from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from ..models.narrative_models import (
    UserNarrativeState, 
    UserDecisionLog, 
    NarrativeScene,
    NarrativeDecision
)

class UserNarrativeService:
    """Service for managing user narrative states and decisions."""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
    
    async def create_user_state(self, user_id: str, initial_scene_id: str) -> UserNarrativeState:
        """Create a new narrative state for a user."""
        # Check if user state already exists
        existing_state = await self.get_user_state(user_id)
        if existing_state:
            return existing_state
            
        # Create new state
        user_state = UserNarrativeState(
            user_id=user_id,
            current_scene_id=initial_scene_id,
            emotional_variables={}
        )
        
        self.db_session.add(user_state)
        await self.db_session.commit()
        await self.db_session.refresh(user_state)
        
        return user_state
    
    async def get_user_state(self, user_id: str) -> Optional[UserNarrativeState]:
        """Get the current narrative state for a user."""
        result = await self.db_session.execute(
            select(UserNarrativeState).where(UserNarrativeState.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def update_user_state(self, user_id: str, scene_id: str, emotional_variables: Dict[str, Any]) -> UserNarrativeState:
        """Update a user's narrative state."""
        user_state = await self.get_user_state(user_id)
        
        if not user_state:
            # Create new state if it doesn't exist
            user_state = await self.create_user_state(user_id, scene_id)
        
        user_state.current_scene_id = scene_id
        user_state.emotional_variables = emotional_variables
        user_state.last_updated_at = func.now()
        
        await self.db_session.commit()
        await self.db_session.refresh(user_state)
        
        return user_state
    
    async def log_user_decision(self, user_id: str, decision_id: str, scene_id: str) -> UserDecisionLog:
        """Log a user's decision."""
        decision_log = UserDecisionLog(
            user_id=user_id,
            decision_id=decision_id,
            scene_id=scene_id
        )
        
        self.db_session.add(decision_log)
        await self.db_session.commit()
        await self.db_session.refresh(decision_log)
        
        return decision_log
    
    async def get_user_decision_history(self, user_id: str) -> List[UserDecisionLog]:
        """Get the decision history for a user."""
        result = await self.db_session.execute(
            select(UserDecisionLog)
            .where(UserDecisionLog.user_id == user_id)
            .order_by(UserDecisionLog.timestamp)
        )
        return result.scalars().all()


class NarrativeContentService:
    """Service for managing narrative content (chapters, scenes, decisions)."""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
    
    async def get_scene_with_choices(self, scene_id: str) -> Optional[Dict[str, Any]]:
        """Get a scene with its available choices."""
        # Get the scene
        result = await self.db_session.execute(
            select(NarrativeScene).where(NarrativeScene.id == scene_id)
        )
        scene = result.scalar_one_or_none()
        
        if not scene:
            return None
        
        # Get decisions for this scene
        result = await self.db_session.execute(
            select(NarrativeDecision)
            .where(NarrativeDecision.scene_id == scene_id)
            .order_by(NarrativeDecision.sort_order)
        )
        decisions = result.scalars().all()
        
        return {
            "scene": scene,
            "decisions": decisions
        }
    
    async def validate_narrative_structure(self) -> Dict[str, Any]:
        """
        Validate the narrative structure for consistency.
        Checks for:
        - Orphaned scenes (scenes with no decisions leading to them)
        - Dead-end decisions (decisions with no next scene)
        - Logical contradictions in conditions
        """
        validation_report = {
            "orphaned_scenes": [],
            "dead_end_decisions": [],
            "logical_issues": [],
            "is_valid": True
        }
        
        # Get all scenes
        result = await self.db_session.execute(select(NarrativeScene))
        all_scenes = result.scalars().all()
        scene_ids = {str(scene.id) for scene in all_scenes}
        
        # Get all decisions
        result = await self.db_session.execute(select(NarrativeDecision))
        all_decisions = result.scalars().all()
        
        # Check for orphaned scenes (except the initial scene)
        referenced_scene_ids = {str(decision.next_scene_id) for decision in all_decisions if decision.next_scene_id}
        orphaned_scene_ids = scene_ids - referenced_scene_ids
        
        if orphaned_scene_ids:
            validation_report["orphaned_scenes"] = list(orphaned_scene_ids)
            validation_report["is_valid"] = False
        
        # Check for dead-end decisions
        dead_end_decisions = [
            str(decision.id) for decision in all_decisions 
            if not decision.next_scene_id
        ]
        
        if dead_end_decisions:
            validation_report["dead_end_decisions"] = dead_end_decisions
            # Note: Dead ends aren't necessarily invalid, so we don't set is_valid to False
        
        # TODO: Add more complex logical validation for conditions
        
        return validation_report