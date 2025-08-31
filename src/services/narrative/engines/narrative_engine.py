import json
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, func
from datetime import datetime, timedelta

from ..models.narrative_models import (
    NarrativeScene, 
    NarrativeDecision, 
    UserNarrativeState, 
    UserDecisionLog,
    CharacterEnum
)

class NarrativeEngine:
    """
    Core logic for processing user decisions, evaluating conditions,
    and determining the next scene in the narrative.
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
    
    async def get_user_state(self, user_id: str) -> Optional[UserNarrativeState]:
        """Get the current narrative state for a user."""
        result = await self.db_session.execute(
            select(UserNarrativeState).where(UserNarrativeState.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_scene(self, scene_id: str) -> Optional[NarrativeScene]:
        """Get a scene by its ID."""
        result = await self.db_session.execute(
            select(NarrativeScene).where(NarrativeScene.id == scene_id)
        )
        return result.scalar_one_or_none()
    
    async def get_decisions_for_scene(self, scene_id: str) -> List[NarrativeDecision]:
        """Get all decisions available for a scene."""
        result = await self.db_session.execute(
            select(NarrativeDecision)
            .where(NarrativeDecision.scene_id == scene_id)
            .order_by(NarrativeDecision.sort_order)
        )
        return result.scalars().all()
    
    async def get_user_decision_history(self, user_id: str) -> List[UserDecisionLog]:
        """Get the decision history for a user."""
        result = await self.db_session.execute(
            select(UserDecisionLog)
            .where(UserDecisionLog.user_id == user_id)
            .order_by(UserDecisionLog.timestamp)
        )
        return result.scalars().all()
    
    async def evaluate_conditions(
        self, 
        conditions: Dict[str, Any], 
        user_state: UserNarrativeState, 
        user_history: List[UserDecisionLog]
    ) -> bool:
        """
        Evaluate complex conditions for showing a decision.
        Supports:
        - Simple comparisons (affinity_diana_gt, affinity_diana_lt)
        - Decision history checks (has_user_chosen_X)
        - Time-based conditions (recent_decisions)
        """
        if not conditions:
            return True
            
        # Check each condition
        for condition_key, condition_value in conditions.items():
            # Handle emotional variable comparisons
            if condition_key.endswith('_gt'):
                var_name = condition_key[:-3]  # Remove '_gt'
                if var_name in user_state.emotional_variables:
                    if user_state.emotional_variables[var_name] <= condition_value:
                        return False
                        
            elif condition_key.endswith('_lt'):
                var_name = condition_key[:-3]  # Remove '_lt'
                if var_name in user_state.emotional_variables:
                    if user_state.emotional_variables[var_name] >= condition_value:
                        return False
            
            # Handle decision history checks
            elif condition_key.startswith('has_user_chosen_'):
                decision_id = condition_key[16:]  # Remove 'has_user_chosen_'
                decision_found = any(
                    log.decision_id == decision_id for log in user_history
                )
                if not decision_found:
                    return False
                    
            # Handle recent decisions check
            elif condition_key == 'recent_decisions':
                # Check if user has made specific decisions recently
                if isinstance(condition_value, dict):
                    required_decisions = condition_value.get('decisions', [])
                    time_window_minutes = condition_value.get('minutes', 60)
                    
                    # Calculate time threshold
                    time_threshold = datetime.utcnow() - timedelta(minutes=time_window_minutes)
                    
                    # Check if all required decisions were made recently
                    for decision_id in required_decisions:
                        recent_decision_found = any(
                            log.decision_id == decision_id and log.timestamp >= time_threshold
                            for log in user_history
                        )
                        if not recent_decision_found:
                            return False
        
        # All conditions passed
        return True
    
    async def apply_emotional_impact(
        self, 
        current_emotions: Dict[str, Any], 
        impact: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply emotional variable impacts from a decision.
        """
        new_emotions = current_emotions.copy()
        
        if not impact:
            return new_emotions
            
        for var_name, change in impact.items():
            if var_name in new_emotions:
                new_emotions[var_name] += change
            else:
                new_emotions[var_name] = change
                
        return new_emotions
    
    async def process_decision(
        self, 
        user_id: str, 
        decision_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Process a user's decision and determine the next narrative state.
        """
        # Get user's current state
        user_state = await self.get_user_state(user_id)
        if not user_state:
            return None
            
        # Get the decision
        result = await self.db_session.execute(
            select(NarrativeDecision).where(NarrativeDecision.id == decision_id)
        )
        decision = result.scalar_one_or_none()
        if not decision:
            return None
            
        # Get user's decision history
        user_history = await self.get_user_decision_history(user_id)
        
        # Log this decision
        new_log = UserDecisionLog(
            user_id=user_id,
            decision_id=decision_id,
            scene_id=user_state.current_scene_id
        )
        self.db_session.add(new_log)
        
        # Apply emotional impact
        new_emotions = await self.apply_emotional_impact(
            user_state.emotional_variables,
            decision.emotional_variables_impact or {}
        )
        
        # Update user state
        user_state.emotional_variables = new_emotions
        user_state.current_scene_id = decision.next_scene_id
        user_state.last_updated_at = func.now()
        
        # Commit changes
        await self.db_session.commit()
        
        # Get the next scene
        next_scene = await self.get_scene(decision.next_scene_id)
        if not next_scene:
            return None
            
        # Get available decisions for next scene
        next_decisions = await self.get_decisions_for_scene(decision.next_scene_id)
        
        # Filter decisions based on conditions
        available_decisions = []
        for d in next_decisions:
            conditions_met = await self.evaluate_conditions(
                d.required_conditions or {},
                user_state,
                user_history + [new_log]  # Include the new decision in history
            )
            if conditions_met:
                available_decisions.append(d)
        
        # Prepare response
        response = {
            "node_id": str(next_scene.id),
            "character": next_scene.character_speaker or "System",
            "text": next_scene.dialogue,
            "choices": [
                {
                    "choice_id": str(d.id),
                    "text": d.choice_text
                }
                for d in available_decisions
            ]
        }
        
        return response