"""
Comprehensive Unit Tests for Decision Engine

This module provides extensive unit test coverage for the Decision Engine component,
including decision processing, consequence calculation, and story consistency validation.
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Any, Dict, List

# Test imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from services.narrative.engines.decision_engine import DecisionEngine
from services.narrative.interfaces import (
    DecisionResult,
    DecisionType,
    RelationshipType,
    DecisionEngineError,
    InvalidDecisionError,
)
from services.narrative.models import (
    StoryDecision,
    NarrativeFlag,
    InteractionHistory,
    MORAL_ALIGNMENTS,
    POINTS_AWARDS,
)
from core.interfaces import IEventBus


class TestDecisionEngine:
    """Comprehensive test suite for DecisionEngine."""
    
    @pytest.fixture
    async def event_bus_mock(self):
        """Create a mock event bus."""
        mock = AsyncMock(spec=IEventBus)
        return mock
    
    @pytest.fixture
    async def decision_engine(self, event_bus_mock):
        """Create a decision engine instance for testing."""
        return DecisionEngine(
            event_bus=event_bus_mock,
            enable_long_term_tracking=True,
            max_consequences_per_decision=5
        )
    
    @pytest.fixture
    async def decision_engine_no_long_term(self, event_bus_mock):
        """Create a decision engine instance with long-term tracking disabled."""
        return DecisionEngine(
            event_bus=event_bus_mock,
            enable_long_term_tracking=False,
            max_consequences_per_decision=3
        )

    # Initialization Tests
    
    def test_initialization_default(self, event_bus_mock):
        """Test default initialization of decision engine."""
        engine = DecisionEngine(event_bus_mock)
        
        assert engine.event_bus == event_bus_mock
        assert engine.enable_long_term_tracking is True
        assert engine.max_consequences_per_decision == 5
        assert len(engine._decision_cache) == 0
        assert engine._stats["decisions_processed"] == 0
    
    def test_initialization_custom_settings(self, event_bus_mock):
        """Test initialization with custom settings."""
        engine = DecisionEngine(
            event_bus=event_bus_mock,
            enable_long_term_tracking=False,
            max_consequences_per_decision=10
        )
        
        assert engine.enable_long_term_tracking is False
        assert engine.max_consequences_per_decision == 10

    # Process Decision Tests
    
    async def test_process_decision_success(self, decision_engine):
        """Test successful decision processing."""
        user_id = 1
        chapter_id = "chapter_01"
        decision_id = "chapter_01_decision_1"
        
        with patch.object(decision_engine, '_load_decision_data') as mock_load:
            with patch.object(decision_engine, '_validate_decision_eligibility') as mock_validate:
                with patch.object(decision_engine, 'calculate_immediate_consequences') as mock_immediate:
                    with patch.object(decision_engine, '_calculate_character_impacts') as mock_character:
                        with patch.object(decision_engine, 'update_narrative_flags') as mock_flags:
                            with patch.object(decision_engine, '_determine_unlocked_content') as mock_unlock:
                                with patch.object(decision_engine, '_calculate_next_chapter') as mock_next:
                                    with patch.object(decision_engine, '_check_achievement_triggers') as mock_achievements:
                                        with patch.object(decision_engine, 'calculate_long_term_impact') as mock_long_term:
                                            with patch.object(decision_engine, '_record_decision_history') as mock_record:
                                                with patch.object(decision_engine, '_format_relationship_changes') as mock_format:
                                                    
                                                    # Setup mocks
                                                    decision = StoryDecision(
                                                        id=decision_id,
                                                        chapter_id=chapter_id,
                                                        decision_text="Choose wisdom",
                                                        decision_type=DecisionType.MORAL_DILEMMA,
                                                        character_impact={"diana": 5}
                                                    )
                                                    mock_load.return_value = decision
                                                    
                                                    mock_immediate.return_value = {"moral_growth": 10}
                                                    mock_character.return_value = {"diana": 5}
                                                    mock_flags.return_value = {"wisdom_path": True}
                                                    mock_unlock.return_value = ["wisdom_content"]
                                                    mock_next.return_value = "chapter_02"
                                                    mock_achievements.return_value = ["wise_choice"]
                                                    mock_long_term.return_value = {"future_wisdom": True}
                                                    mock_format.return_value = {"diana": {"level_change": 5}}
                                                    
                                                    result = await decision_engine.process_decision(
                                                        user_id, chapter_id, decision_id
                                                    )
                                                    
                                                    assert result.success is True
                                                    assert result.user_id == user_id
                                                    assert result.chapter_id == chapter_id
                                                    assert result.decision_id == decision_id
                                                    assert result.immediate_consequences == {"moral_growth": 10}
                                                    assert result.character_impacts == {"diana": 5}
                                                    assert result.unlocked_content == ["wisdom_content"]
                                                    assert result.next_chapter == "chapter_02"
                                                    assert result.achievement_triggers == ["wise_choice"]
                                                    assert decision_engine._stats["decisions_processed"] == 1
    
    async def test_process_decision_with_context(self, decision_engine):
        """Test decision processing with decision context."""
        user_id = 1
        chapter_id = "chapter_02"
        decision_id = "test_decision"
        decision_context = {
            "emotional_state": "stressed",
            "time_pressure": True,
            "characters_present": ["diana", "alex"]
        }
        
        with patch.object(decision_engine, '_load_decision_data') as mock_load:
            with patch.object(decision_engine, '_validate_decision_eligibility') as mock_validate:
                with patch.object(decision_engine, 'calculate_immediate_consequences') as mock_consequences:
                    with patch.object(decision_engine, '_calculate_character_impacts') as mock_impacts:
                        with patch.object(decision_engine, 'update_narrative_flags') as mock_flags:
                            with patch.object(decision_engine, '_determine_unlocked_content') as mock_unlock:
                                with patch.object(decision_engine, '_calculate_next_chapter') as mock_next:
                                    with patch.object(decision_engine, '_check_achievement_triggers') as mock_achievements:
                                        with patch.object(decision_engine, 'calculate_long_term_impact') as mock_long_term:
                                            with patch.object(decision_engine, '_record_decision_history') as mock_record:
                                                with patch.object(decision_engine, '_format_relationship_changes') as mock_format:
                                                    
                                                    decision = StoryDecision(
                                                        id=decision_id, chapter_id=chapter_id,
                                                        decision_text="Test", decision_type=DecisionType.STRATEGIC_CHOICE
                                                    )
                                                    mock_load.return_value = decision
                                                    mock_consequences.return_value = {}
                                                    mock_impacts.return_value = {}
                                                    mock_flags.return_value = {}
                                                    mock_unlock.return_value = []
                                                    mock_next.return_value = None
                                                    mock_achievements.return_value = []
                                                    mock_long_term.return_value = {}
                                                    mock_format.return_value = {}
                                                    
                                                    await decision_engine.process_decision(
                                                        user_id, chapter_id, decision_id, decision_context
                                                    )
                                                    
                                                    # Verify context was passed to consequence calculation
                                                    mock_consequences.assert_called_once()
                                                    call_args = mock_consequences.call_args[0][0]
                                                    assert call_args["context"] == decision_context
    
    async def test_process_decision_no_long_term_tracking(self, decision_engine_no_long_term):
        """Test decision processing with long-term tracking disabled."""
        user_id = 1
        chapter_id = "chapter_01"
        decision_id = "test_decision"
        
        with patch.object(decision_engine_no_long_term, '_load_decision_data') as mock_load:
            with patch.object(decision_engine_no_long_term, '_validate_decision_eligibility'):
                with patch.object(decision_engine_no_long_term, 'calculate_immediate_consequences') as mock_immediate:
                    with patch.object(decision_engine_no_long_term, '_calculate_character_impacts') as mock_character:
                        with patch.object(decision_engine_no_long_term, 'update_narrative_flags') as mock_flags:
                            with patch.object(decision_engine_no_long_term, '_determine_unlocked_content') as mock_unlock:
                                with patch.object(decision_engine_no_long_term, '_calculate_next_chapter') as mock_next:
                                    with patch.object(decision_engine_no_long_term, '_check_achievement_triggers') as mock_achievements:
                                        with patch.object(decision_engine_no_long_term, '_record_decision_history'):
                                            with patch.object(decision_engine_no_long_term, '_format_relationship_changes') as mock_format:
                                                
                                                decision = StoryDecision(
                                                    id=decision_id, chapter_id=chapter_id,
                                                    decision_text="Test", decision_type=DecisionType.MORAL_DILEMMA
                                                )
                                                mock_load.return_value = decision
                                                mock_immediate.return_value = {}
                                                mock_character.return_value = {}
                                                mock_flags.return_value = {}
                                                mock_unlock.return_value = []
                                                mock_next.return_value = None
                                                mock_achievements.return_value = []
                                                mock_format.return_value = {}
                                                
                                                result = await decision_engine_no_long_term.process_decision(
                                                    user_id, chapter_id, decision_id
                                                )
                                                
                                                assert result.success is True
                                                # Long-term tracking should not be called
                                                assert not hasattr(decision_engine_no_long_term, '_long_term_called')
    
    async def test_process_decision_validation_failure(self, decision_engine):
        """Test decision processing with validation failure."""
        user_id = 1
        chapter_id = "chapter_01"
        decision_id = "invalid_decision"
        
        with patch.object(decision_engine, '_load_decision_data') as mock_load:
            with patch.object(decision_engine, '_validate_decision_eligibility') as mock_validate:
                
                decision = StoryDecision(
                    id=decision_id, chapter_id=chapter_id,
                    decision_text="Invalid", decision_type=DecisionType.MORAL_DILEMMA
                )
                mock_load.return_value = decision
                mock_validate.side_effect = InvalidDecisionError("Decision not eligible")
                
                with pytest.raises(InvalidDecisionError, match="Decision not eligible"):
                    await decision_engine.process_decision(user_id, chapter_id, decision_id)
    
    async def test_process_decision_general_error(self, decision_engine):
        """Test decision processing with general error."""
        user_id = 1
        chapter_id = "chapter_01"
        decision_id = "error_decision"
        
        with patch.object(decision_engine, '_load_decision_data') as mock_load:
            mock_load.side_effect = Exception("Database error")
            
            result = await decision_engine.process_decision(user_id, chapter_id, decision_id)
            
            assert result.success is False
            assert "Decision processing failed" in result.error_message

    # Calculate Immediate Consequences Tests
    
    async def test_calculate_immediate_consequences_basic(self, decision_engine):
        """Test basic immediate consequences calculation."""
        decision_obj = StoryDecision(
            id="test_decision",
            chapter_id="chapter_01",
            decision_text="Help the stranger",
            decision_type=DecisionType.MORAL_DILEMMA,
            immediate_consequences={"moral_impact": {"compassionate": 10}},
            character_impact={"diana": 5}
        )
        
        decision_data = {
            "decision": decision_obj,
            "user_id": 1,
            "context": {}
        }
        
        with patch.object(decision_engine, '_calculate_context_consequences') as mock_context:
            with patch.object(decision_engine, '_calculate_dynamic_consequences') as mock_dynamic:
                with patch.object(decision_engine, '_limit_consequence_scope') as mock_limit:
                    
                    mock_context.return_value = {"context_bonus": 5}
                    mock_dynamic.return_value = {"wisdom_growth": 3}
                    mock_limit.side_effect = lambda x: x  # No limiting
                    
                    result = await decision_engine.calculate_immediate_consequences(decision_data)
                    
                    assert "moral_impact" in result
                    assert result["moral_impact"]["compassionate"] == 10
                    assert result["context_bonus"] == 5
                    assert result["wisdom_growth"] == 3
                    assert decision_engine._stats["consequences_calculated"] == 1
    
    async def test_calculate_immediate_consequences_strategic_with_randomization(self, decision_engine):
        """Test consequences calculation for strategic decision with randomization."""
        decision_obj = StoryDecision(
            id="strategic_decision",
            chapter_id="chapter_02",
            decision_text="Plan the assault",
            decision_type=DecisionType.STRATEGIC_CHOICE,
            immediate_consequences={"tactical_advantage": True}
        )
        
        decision_data = {
            "decision": decision_obj,
            "user_id": 1
        }
        
        with patch.object(decision_engine, '_calculate_context_consequences', return_value={}):
            with patch.object(decision_engine, '_calculate_dynamic_consequences', return_value={}):
                with patch.object(decision_engine, '_apply_strategic_randomization') as mock_random:
                    with patch.object(decision_engine, '_limit_consequence_scope') as mock_limit:
                        
                        mock_random.return_value = {"unexpected_success": True}
                        mock_limit.side_effect = lambda x: x
                        
                        result = await decision_engine.calculate_immediate_consequences(decision_data)
                        
                        assert result["tactical_advantage"] is True
                        assert result["unexpected_success"] is True
                        
                        # Strategic decisions should trigger randomization
                        mock_random.assert_called_once_with(decision_obj)
    
    async def test_calculate_immediate_consequences_with_context(self, decision_engine):
        """Test consequences calculation with rich context."""
        decision_obj = StoryDecision(
            id="context_decision",
            chapter_id="chapter_01",
            decision_text="React quickly",
            decision_type=DecisionType.STRATEGIC_CHOICE
        )
        
        context = {
            "decision_time": 3,  # Quick decision
            "emotional_state": "excited",
            "characters_present": ["diana", "alex"],
            "previous_decisions": ["moral_choice_1", "strategic_choice_1"]
        }
        
        decision_data = {
            "decision": decision_obj,
            "user_id": 1,
            "context": context
        }
        
        with patch.object(decision_engine, '_calculate_dynamic_consequences', return_value={}):
            with patch.object(decision_engine, '_apply_strategic_randomization', return_value={}):
                with patch.object(decision_engine, '_limit_consequence_scope') as mock_limit:
                    
                    mock_limit.side_effect = lambda x: x
                    
                    result = await decision_engine.calculate_immediate_consequences(decision_data)
                    
                    # Should have context-based consequences
                    assert "impulsiveness_points" in result  # Quick decision
    
    async def test_calculate_immediate_consequences_error_handling(self, decision_engine):
        """Test consequences calculation error handling."""
        decision_data = {"decision": None, "user_id": 1}  # Invalid data
        
        # Should return empty dict on error
        result = await decision_engine.calculate_immediate_consequences(decision_data)
        assert result == {}

    # Calculate Character Impacts Tests
    
    async def test_calculate_character_impacts_basic(self, decision_engine):
        """Test basic character impact calculation."""
        decision = StoryDecision(
            id="test_decision",
            chapter_id="chapter_01",
            decision_text="Help Diana",
            decision_type=DecisionType.RELATIONSHIP_ACTION,
            character_impact={"diana": 8, "alex": -2}
        )
        
        with patch.object(decision_engine, '_load_user_relationships') as mock_relationships:
            mock_relationships.return_value = {
                "diana": {"level": 40},
                "alex": {"level": 20}
            }
            
            result = await decision_engine._calculate_character_impacts(
                1, decision, None
            )
            
            # Should return modified impacts within bounds
            assert result["diana"] <= 10
            assert result["diana"] >= -10
            assert result["alex"] <= 10
            assert result["alex"] >= -10
    
    async def test_calculate_character_impacts_with_context_modifiers(self, decision_engine):
        """Test character impact calculation with context modifiers."""
        decision = StoryDecision(
            id="pressure_decision",
            chapter_id="chapter_01",
            decision_text="Quick choice",
            decision_type=DecisionType.STRATEGIC_CHOICE,
            character_impact={"alex": 4}
        )
        
        context = {
            "time_pressure": True,
            "emotional_state": "excited"
        }
        
        with patch.object(decision_engine, '_load_user_relationships') as mock_relationships:
            mock_relationships.return_value = {"alex": {"level": 30}}
            
            result = await decision_engine._calculate_character_impacts(
                1, decision, context
            )
            
            # Should apply both time pressure (1.5x) and excitement (1.2x) modifiers
            # 4 * 1.5 * 1.2 = 7.2, rounded to 7
            expected_impact = int(4 * 1.5 * 1.2)
            assert result["alex"] == expected_impact
    
    async def test_calculate_character_impacts_relationship_modifiers(self, decision_engine):
        """Test character impact with relationship-based modifiers."""
        decision = StoryDecision(
            id="relationship_decision",
            chapter_id="chapter_01",
            decision_text="Support friend",
            decision_type=DecisionType.RELATIONSHIP_ACTION,
            character_impact={"diana": 5, "morgan": -3}
        )
        
        with patch.object(decision_engine, '_load_user_relationships') as mock_relationships:
            mock_relationships.return_value = {
                "diana": {"level": 75},  # High relationship - positive impact strengthened
                "morgan": {"level": -30}  # Poor relationship - negative impact worsened
            }
            
            result = await decision_engine._calculate_character_impacts(
                1, decision, None
            )
            
            # Diana impact should be strengthened (5 * 1.3 = 6.5 -> 6)
            assert result["diana"] > 5
            
            # Morgan impact should be worsened (-3 * 1.4 = -4.2 -> -4)
            assert result["morgan"] < -3
    
    async def test_calculate_character_impacts_bounds_enforcement(self, decision_engine):
        """Test character impact bounds enforcement."""
        decision = StoryDecision(
            id="extreme_decision",
            chapter_id="chapter_01",
            decision_text="Extreme choice",
            decision_type=DecisionType.MORAL_DILEMMA,
            character_impact={"diana": 15, "alex": -20}  # Extreme values
        )
        
        with patch.object(decision_engine, '_load_user_relationships') as mock_relationships:
            mock_relationships.return_value = {
                "diana": {"level": 80},  # Would amplify to 15 * 1.3 = 19.5
                "alex": {"level": -40}   # Would amplify to -20 * 1.4 = -28
            }
            
            result = await decision_engine._calculate_character_impacts(
                1, decision, None
            )
            
            # Should be bounded to [-10, 10]
            assert result["diana"] == 10
            assert result["alex"] == -10

    # Long-term Impact Tests
    
    async def test_calculate_long_term_impact_full(self, decision_engine):
        """Test comprehensive long-term impact calculation."""
        decision_obj = StoryDecision(
            id="major_decision",
            chapter_id="chapter_02",
            decision_text="Make alliance",
            decision_type=DecisionType.STORY_BRANCH,
            long_term_impact={"alliance_formed": True}
        )
        
        decision_data = {
            "decision": decision_obj,
            "consequences": {"moral_consistency_bonus": True}
        }
        
        with patch.object(decision_engine, '_calculate_branch_cascade_effects') as mock_branch:
            with patch.object(decision_engine, '_calculate_relationship_evolution') as mock_relationship:
                with patch.object(decision_engine, '_calculate_moral_trajectory') as mock_moral:
                    with patch.object(decision_engine, '_predict_future_content_unlocks') as mock_predict:
                        
                        mock_branch.return_value = {"ending_bias": "diplomatic"}
                        mock_relationship.return_value = {"diana_evolving_to": "mentorship"}
                        mock_moral.return_value = {"compassionate_mastery_approaching": True}
                        mock_predict.return_value = {"diplomatic_ending": "high_probability"}
                        
                        result = await decision_engine.calculate_long_term_impact(1, decision_data)
                        
                        assert result["alliance_formed"] is True
                        assert result["branch_effects"]["ending_bias"] == "diplomatic"
                        assert result["relationship_evolution"]["diana_evolving_to"] == "mentorship"
                        assert result["moral_trajectory"]["compassionate_mastery_approaching"] is True
                        assert result["predicted_unlocks"]["diplomatic_ending"] == "high_probability"
    
    async def test_calculate_long_term_impact_error_handling(self, decision_engine):
        """Test long-term impact calculation error handling."""
        decision_data = {"invalid": "data"}
        
        # Should return empty dict on error
        result = await decision_engine.calculate_long_term_impact(1, decision_data)
        assert result == {}

    # Update Narrative Flags Tests
    
    async def test_update_narrative_flags_success(self, decision_engine):
        """Test successful narrative flags update."""
        decision_obj = StoryDecision(
            id="flag_decision",
            chapter_id="chapter_01",
            decision_text="Set flag",
            decision_type=DecisionType.MORAL_DILEMMA,
            immediate_consequences={"flag_updates": {"hero_path": True}}
        )
        
        decision_data = {
            "decision": decision_obj,
            "consequences": {"moral_consistency_bonus": True}
        }
        
        with patch.object(decision_engine, '_load_user_flags') as mock_load:
            with patch.object(decision_engine, '_apply_flag_updates') as mock_apply:
                with patch.object(decision_engine, '_save_user_flags') as mock_save:
                    
                    mock_load.return_value = {"existing_flag": "value"}
                    mock_apply.return_value = {
                        "existing_flag": "value",
                        "hero_path": True,
                        "moral_consistency_streak": 1
                    }
                    
                    result = await decision_engine.update_narrative_flags(1, decision_data)
                    
                    assert result["hero_path"] is True
                    assert result["moral_consistency_streak"] == 1
                    assert decision_engine._stats["flags_updated"] == 1
                    
                    mock_save.assert_called_once()
    
    async def test_update_narrative_flags_error(self, decision_engine):
        """Test narrative flags update error handling."""
        decision_data = {"decision": Mock()}
        
        with patch.object(decision_engine, '_load_user_flags') as mock_load:
            mock_load.side_effect = Exception("Flag load error")
            
            # Should return empty dict on error
            result = await decision_engine.update_narrative_flags(1, decision_data)
            assert result == {}

    # Validate Decision Consistency Tests
    
    async def test_validate_decision_consistency_success(self, decision_engine):
        """Test successful decision consistency validation."""
        decision_obj = StoryDecision(
            id="valid_decision",
            chapter_id="chapter_01",
            decision_text="Valid choice",
            decision_type=DecisionType.MORAL_DILEMMA,
            required_flags={"tutorial_complete": True},
            vip_required=False
        )
        
        decision_data = {"decision": decision_obj}
        
        with patch.object(decision_engine, '_load_user_flags') as mock_flags:
            with patch.object(decision_engine, '_check_vip_status') as mock_vip:
                
                mock_flags.return_value = {"tutorial_complete": True}
                mock_vip.return_value = True
                
                is_valid, error = await decision_engine.validate_decision_consistency(
                    1, decision_data
                )
                
                assert is_valid is True
                assert error is None
    
    async def test_validate_decision_consistency_required_flags_not_met(self, decision_engine):
        """Test decision consistency validation with unmet required flags."""
        decision_obj = StoryDecision(
            id="flag_dependent_decision",
            chapter_id="chapter_02",
            decision_text="Advanced choice",
            decision_type=DecisionType.STORY_BRANCH,
            required_flags={"hero_path": True, "chapter_01_complete": True}
        )
        
        decision_data = {"decision": decision_obj}
        
        with patch.object(decision_engine, '_load_user_flags') as mock_flags:
            mock_flags.return_value = {"hero_path": False, "chapter_01_complete": True}
            
            is_valid, error = await decision_engine.validate_decision_consistency(
                1, decision_data
            )
            
            assert is_valid is False
            assert "Required flag hero_path=True not met" in error
    
    async def test_validate_decision_consistency_vip_required_denied(self, decision_engine):
        """Test decision consistency validation with VIP requirement not met."""
        decision_obj = StoryDecision(
            id="vip_decision",
            chapter_id="vip_chapter",
            decision_text="VIP choice",
            decision_type=DecisionType.STORY_BRANCH,
            vip_required=True
        )
        
        decision_data = {"decision": decision_obj}
        
        with patch.object(decision_engine, '_check_vip_status') as mock_vip:
            mock_vip.return_value = False
            
            is_valid, error = await decision_engine.validate_decision_consistency(
                1, decision_data
            )
            
            assert is_valid is False
            assert "requires VIP access" in error
    
    async def test_validate_decision_consistency_character_requirements(self, decision_engine):
        """Test decision consistency validation with character relationship requirements."""
        decision_obj = StoryDecision(
            id="relationship_decision",
            chapter_id="chapter_03",
            decision_text="Intimate conversation",
            decision_type=DecisionType.CHARACTER_RESPONSE
        )
        # Add character requirements dynamically
        decision_obj.character_requirements = {"diana": 50, "alex": 25}
        
        decision_data = {"decision": decision_obj}
        
        with patch.object(decision_engine, '_load_user_relationships') as mock_relationships:
            mock_relationships.return_value = {
                "diana": {"level": 60},  # Meets requirement
                "alex": {"level": 20}    # Below requirement
            }
            
            is_valid, error = await decision_engine.validate_decision_consistency(
                1, decision_data
            )
            
            assert is_valid is False
            assert "Insufficient relationship with alex" in error
            assert "need 25, have 20" in error
    
    async def test_validate_decision_consistency_no_decision_object(self, decision_engine):
        """Test decision consistency validation with missing decision object."""
        decision_data = {"invalid": "data"}
        
        is_valid, error = await decision_engine.validate_decision_consistency(
            1, decision_data
        )
        
        assert is_valid is False
        assert "No decision object provided" in error
    
    async def test_validate_decision_consistency_exception(self, decision_engine):
        """Test decision consistency validation error handling."""
        decision_obj = Mock()
        decision_data = {"decision": decision_obj}
        
        with patch.object(decision_engine, '_load_user_flags') as mock_flags:
            mock_flags.side_effect = Exception("Validation error")
            
            is_valid, error = await decision_engine.validate_decision_consistency(
                1, decision_data
            )
            
            assert is_valid is False
            assert "Validation error" in error

    # Decision Loading and Caching Tests
    
    async def test_load_decision_data_success(self, decision_engine):
        """Test successful decision data loading."""
        decision_id = "prologue_decision_1"
        
        result = await decision_engine._load_decision_data(decision_id)
        
        assert isinstance(result, StoryDecision)
        assert result.id == decision_id
        assert result.chapter_id == "prologue"
        assert decision_engine._stats["cache_misses"] == 1
    
    async def test_load_decision_data_caching(self, decision_engine):
        """Test decision data caching."""
        decision_id = "chapter_01_discovery_decision_1"
        
        # First call - should miss cache
        result1 = await decision_engine._load_decision_data(decision_id)
        assert decision_engine._stats["cache_misses"] == 1
        
        # Second call - should hit cache
        result2 = await decision_engine._load_decision_data(decision_id)
        assert decision_engine._stats["cache_hits"] == 1
        
        # Results should be the same
        assert result1.id == result2.id
    
    async def test_validate_decision_eligibility_success(self, decision_engine):
        """Test successful decision eligibility validation."""
        user_id = 1
        chapter_id = "chapter_01"
        decision = StoryDecision(
            id="chapter_01_decision_1",
            chapter_id=chapter_id,
            decision_text="Valid choice",
            decision_type=DecisionType.MORAL_DILEMMA
        )
        
        with patch.object(decision_engine, 'validate_decision_consistency') as mock_consistency:
            mock_consistency.return_value = (True, None)
            
            # Should not raise exception
            await decision_engine._validate_decision_eligibility(user_id, chapter_id, decision)
            
            mock_consistency.assert_called_once()
    
    async def test_validate_decision_eligibility_wrong_chapter(self, decision_engine):
        """Test decision eligibility validation with wrong chapter."""
        user_id = 1
        chapter_id = "chapter_02"
        decision = StoryDecision(
            id="chapter_01_decision_1",
            chapter_id="chapter_01",  # Different chapter
            decision_text="Wrong chapter choice",
            decision_type=DecisionType.MORAL_DILEMMA
        )
        
        with pytest.raises(InvalidDecisionError, match="not available in chapter"):
            await decision_engine._validate_decision_eligibility(user_id, chapter_id, decision)
    
    async def test_validate_decision_eligibility_consistency_failure(self, decision_engine):
        """Test decision eligibility validation with consistency failure."""
        user_id = 1
        chapter_id = "chapter_01"
        decision = StoryDecision(
            id="chapter_01_decision_1",
            chapter_id=chapter_id,
            decision_text="Inconsistent choice",
            decision_type=DecisionType.MORAL_DILEMMA
        )
        
        with patch.object(decision_engine, 'validate_decision_consistency') as mock_consistency:
            mock_consistency.return_value = (False, "Consistency error")
            
            with pytest.raises(InvalidDecisionError, match="Decision not eligible"):
                await decision_engine._validate_decision_eligibility(user_id, chapter_id, decision)

    # Context and Dynamic Consequences Tests
    
    async def test_calculate_context_consequences_decision_time(self, decision_engine):
        """Test context consequences for decision timing."""
        decision = StoryDecision(
            id="timed_decision", chapter_id="chapter_01",
            decision_text="Quick choice", decision_type=DecisionType.STRATEGIC_CHOICE
        )
        
        # Test quick decision
        context_quick = {"decision_time": 3}
        result_quick = await decision_engine._calculate_context_consequences(decision, context_quick)
        assert result_quick.get("impulsiveness_points") == 1
        
        # Test slow decision
        context_slow = {"decision_time": 90}
        result_slow = await decision_engine._calculate_context_consequences(decision, context_slow)
        assert result_slow.get("thoughtfulness_points") == 1
        
        # Test normal decision time
        context_normal = {"decision_time": 30}
        result_normal = await decision_engine._calculate_context_consequences(decision, context_normal)
        assert "impulsiveness_points" not in result_normal
        assert "thoughtfulness_points" not in result_normal
    
    async def test_calculate_context_consequences_decision_chain(self, decision_engine):
        """Test context consequences for decision chains."""
        decision = StoryDecision(
            id="chain_decision", chapter_id="chapter_01",
            decision_text="Chain choice", decision_type=DecisionType.MORAL_DILEMMA
        )
        
        context = {
            "previous_decisions": ["moral_choice_1", "moral_choice_2", "moral_choice_3"]
        }
        
        with patch.object(decision_engine, '_calculate_decision_chain_bonus') as mock_chain:
            mock_chain.return_value = {"decision_consistency_bonus": 3}
            
            result = await decision_engine._calculate_context_consequences(decision, context)
            
            assert result["decision_consistency_bonus"] == 3
            mock_chain.assert_called_once_with(context["previous_decisions"], decision)
    
    async def test_calculate_context_consequences_character_witnesses(self, decision_engine):
        """Test context consequences for character witnesses."""
        decision = StoryDecision(
            id="witnessed_decision", chapter_id="chapter_01",
            decision_text="Public choice", decision_type=DecisionType.RELATIONSHIP_ACTION,
            character_impact={"diana": 5, "alex": 3}
        )
        
        context = {
            "characters_present": ["diana", "morgan"]  # Diana present, Alex not
        }
        
        result = await decision_engine._calculate_context_consequences(decision, context)
        
        # Only Diana should have witnessed consequence (she's affected AND present)
        assert result.get("diana_witnessed_decision") is True
        assert "alex_witnessed_decision" not in result
        assert "morgan_witnessed_decision" not in result  # Present but not affected
    
    async def test_calculate_dynamic_consequences_moral_consistency(self, decision_engine):
        """Test dynamic consequences for moral consistency."""
        decision_obj = StoryDecision(
            id="moral_decision",
            chapter_id="chapter_01",
            decision_text="Compassionate choice",
            decision_type=DecisionType.MORAL_DILEMMA,
            immediate_consequences={"moral_impact": {"compassionate": 10}}
        )
        
        with patch.object(decision_engine, '_load_user_moral_alignment') as mock_moral:
            with patch.object(decision_engine, '_load_user_completed_chapters') as mock_chapters:
                
                # User already has high compassionate alignment
                mock_moral.return_value = {"compassionate": 70}
                mock_chapters.return_value = ["prologue", "chapter_01"]
                
                result = await decision_engine._calculate_dynamic_consequences(1, decision_obj)
                
                # Should get moral consistency bonus
                assert result.get("moral_consistency_bonus") is True
    
    async def test_calculate_dynamic_consequences_moral_growth(self, decision_engine):
        """Test dynamic consequences for moral growth opportunity."""
        decision_obj = StoryDecision(
            id="growth_decision",
            chapter_id="chapter_01",
            decision_text="New moral path",
            decision_type=DecisionType.MORAL_DILEMMA,
            immediate_consequences={"moral_impact": {"rebellious": 15}}
        )
        
        with patch.object(decision_engine, '_load_user_moral_alignment') as mock_moral:
            with patch.object(decision_engine, '_load_user_completed_chapters') as mock_chapters:
                
                # User has low rebellious but high traditional (opposite)
                mock_moral.return_value = {"rebellious": -20, "traditional": 60}
                mock_chapters.return_value = ["prologue"]
                
                result = await decision_engine._calculate_dynamic_consequences(1, decision_obj)
                
                # Should get growth opportunity for exploring new morality
                assert result.get("moral_growth_opportunity") is True
    
    async def test_calculate_dynamic_consequences_veteran_player(self, decision_engine):
        """Test dynamic consequences for veteran players."""
        decision_obj = StoryDecision(
            id="veteran_decision", chapter_id="chapter_10",
            decision_text="Advanced choice", decision_type=DecisionType.STRATEGIC_CHOICE
        )
        
        with patch.object(decision_engine, '_load_user_moral_alignment', return_value={}):
            with patch.object(decision_engine, '_load_user_completed_chapters') as mock_chapters:
                
                # Veteran player with many completed chapters
                mock_chapters.return_value = [f"chapter_{i:02d}" for i in range(1, 15)]
                
                result = await decision_engine._calculate_dynamic_consequences(1, decision_obj)
                
                assert result.get("veteran_player_insight") is True
    
    async def test_calculate_dynamic_consequences_beginner_guidance(self, decision_engine):
        """Test dynamic consequences for new players."""
        decision_obj = StoryDecision(
            id="beginner_decision", chapter_id="chapter_01",
            decision_text="First real choice", decision_type=DecisionType.MORAL_DILEMMA
        )
        
        with patch.object(decision_engine, '_load_user_moral_alignment', return_value={}):
            with patch.object(decision_engine, '_load_user_completed_chapters') as mock_chapters:
                
                # New player with few completed chapters
                mock_chapters.return_value = ["prologue"]
                
                result = await decision_engine._calculate_dynamic_consequences(1, decision_obj)
                
                assert result.get("beginner_guidance_active") is True

    # Strategic Randomization Tests
    
    async def test_apply_strategic_randomization_success(self, decision_engine):
        """Test strategic randomization with positive outcome."""
        decision = StoryDecision(
            id="strategic_decision", chapter_id="chapter_01",
            decision_text="Risky strategy", decision_type=DecisionType.STRATEGIC_CHOICE
        )
        
        # Mock random for successful outcome
        with patch('random.random', return_value=0.1):  # 20% chance for success
            result = await decision_engine._apply_strategic_randomization(decision)
            
            assert result.get("unexpected_success") is True
            assert "bonus_points" in result
            assert isinstance(result["bonus_points"], int)
            assert 10 <= result["bonus_points"] <= 50
    
    async def test_apply_strategic_randomization_complication(self, decision_engine):
        """Test strategic randomization with complication."""
        decision = StoryDecision(
            id="strategic_decision", chapter_id="chapter_01",
            decision_text="Bold strategy", decision_type=DecisionType.STRATEGIC_CHOICE
        )
        
        # Mock random for complication (after missing success)
        with patch('random.random', side_effect=[0.5, 0.05]):  # Miss success, hit complication
            result = await decision_engine._apply_strategic_randomization(decision)
            
            assert result.get("unexpected_complication") is True
            assert "future_challenge" in result
            assert isinstance(result["future_challenge"], dict)
    
    async def test_apply_strategic_randomization_non_strategic(self, decision_engine):
        """Test strategic randomization for non-strategic decision."""
        decision = StoryDecision(
            id="moral_decision", chapter_id="chapter_01",
            decision_text="Moral choice", decision_type=DecisionType.MORAL_DILEMMA
        )
        
        result = await decision_engine._apply_strategic_randomization(decision)
        
        # Should return empty for non-strategic decisions
        assert result == {}
    
    def test_generate_future_challenge(self, decision_engine):
        """Test future challenge generation."""
        # Mock random to ensure consistent result
        with patch('random.choice') as mock_choice:
            expected_challenge = {
                "type": "moral_dilemma",
                "description": "Your values will be challenged"
            }
            mock_choice.return_value = expected_challenge
            
            result = decision_engine._generate_future_challenge()
            
            assert result == expected_challenge
            assert "type" in result
            assert "description" in result

    # Flag Management Tests
    
    def test_calculate_flag_updates_basic(self, decision_engine):
        """Test basic flag updates calculation."""
        decision = StoryDecision(
            id="flag_decision", chapter_id="chapter_01",
            decision_text="Flag setting choice", decision_type=DecisionType.STORY_BRANCH,
            immediate_consequences={
                "flag_updates": {"story_branch": "wisdom_path", "diana_trust": True}
            },
            character_impact={"diana": 7}  # Significant impact
        )
        
        consequences = {
            "moral_consistency_bonus": True,
            "unexpected_success": True,
            "veteran_player_insight": True
        }
        
        result = decision_engine._calculate_flag_updates(decision, consequences)
        
        assert result["story_branch"] == "wisdom_path"
        assert result["diana_trust"] is True
        assert result["moral_consistency_streak"] == 1
        assert result["lucky_outcomes"] == 1
        assert result["veteran_insights"] == 1
        assert result["diana_significant_interaction"] is True
    
    async def test_apply_flag_updates_counters(self, decision_engine):
        """Test flag updates application for counter flags."""
        current_flags = {
            "wisdom_streak": 2,
            "decisions_count": 5,
            "existing_flag": "value"
        }
        
        updates = {
            "wisdom_streak": 1,
            "decisions_count": 1,
            "new_boolean_flag": True,
            "new_value_flag": "new_value"
        }
        
        with patch.object(decision_engine, '_apply_flag_dependencies') as mock_dependencies:
            mock_dependencies.side_effect = lambda uid, flags: flags
            
            result = await decision_engine._apply_flag_updates(current_flags, updates, 1)
            
            assert result["wisdom_streak"] == 3  # 2 + 1
            assert result["decisions_count"] == 6  # 5 + 1
            assert result["new_boolean_flag"] is True
            assert result["new_value_flag"] == "new_value"
            assert result["existing_flag"] == "value"  # Unchanged
    
    async def test_determine_unlocked_content_decision_based(self, decision_engine):
        """Test content unlocking based on specific decisions."""
        decision = StoryDecision(
            id="chapter_02_choice_decision_1",  # Specific decision that unlocks content
            chapter_id="chapter_02_choice",
            decision_text="Choose wisdom",
            decision_type=DecisionType.MORAL_DILEMMA,
            character_impact={"diana": 6}  # High impact
        )
        
        consequences = {"moral_consistency_bonus": True}
        
        result = await decision_engine._determine_unlocked_content(1, decision, consequences)
        
        # Should unlock wisdom path content
        assert "side_quest_wisdom_path" in result
        # Should unlock character depth content from moral bonus
        assert "character_depth_content" in result
        # Should unlock relationship scene from high character impact
        assert "diana_relationship_scene" in result
    
    async def test_calculate_next_chapter_linear_progression(self, decision_engine):
        """Test next chapter calculation with linear progression."""
        decision = StoryDecision(
            id="normal_decision", chapter_id="prologue",
            decision_text="Normal choice", decision_type=DecisionType.MORAL_DILEMMA
        )
        
        flags = {}
        
        result = await decision_engine._calculate_next_chapter(1, "prologue", decision, flags)
        
        assert result == "chapter_01_discovery"  # Linear progression
    
    async def test_calculate_next_chapter_branching(self, decision_engine):
        """Test next chapter calculation with branching based on flags."""
        decision = StoryDecision(
            id="branch_decision", chapter_id="chapter_02_choice",
            decision_text="Moral choice", decision_type=DecisionType.MORAL_DILEMMA
        )
        
        flags = {"moral_consistency_streak": 3}  # High moral streak
        
        result = await decision_engine._calculate_next_chapter(1, "chapter_02_choice", decision, flags)
        
        assert result == "chapter_03_moral_mastery"  # Branched path
    
    async def test_calculate_next_chapter_strategic_branch(self, decision_engine):
        """Test next chapter calculation for strategic decision branch."""
        decision = StoryDecision(
            id="strategic_decision", chapter_id="chapter_02_choice",
            decision_text="Strategic choice", decision_type=DecisionType.STRATEGIC_CHOICE
        )
        
        flags = {"moral_consistency_streak": 0}  # Low moral streak
        
        result = await decision_engine._calculate_next_chapter(1, "chapter_02_choice", decision, flags)
        
        assert result == "chapter_03_strategic_outcomes"

    # Achievement Triggers Tests
    
    async def test_check_achievement_triggers_moral_dilemma(self, decision_engine):
        """Test achievement triggers for moral dilemma decisions."""
        decision = StoryDecision(
            id="moral_decision", chapter_id="chapter_01",
            decision_text="Moral choice", decision_type=DecisionType.MORAL_DILEMMA,
            character_impact={"diana": 5, "alex": 4, "morgan": 7}  # Total 16, high impact
        )
        
        consequences = {"moral_consistency_bonus": True}
        
        result = await decision_engine._check_achievement_triggers(1, decision, consequences)
        
        expected_achievements = {
            "moral_decision_maker",  # From decision type
            "moral_consistency",     # From consequence
            "character_influencer"   # From high total impact (16 >= 15)
        }
        
        assert set(result) == expected_achievements
        assert decision_engine._stats["achievements_triggered"] == len(expected_achievements)
    
    async def test_check_achievement_triggers_fortune_favored(self, decision_engine):
        """Test achievement trigger for unexpected success."""
        decision = StoryDecision(
            id="lucky_decision", chapter_id="chapter_01",
            decision_text="Lucky choice", decision_type=DecisionType.STRATEGIC_CHOICE
        )
        
        consequences = {"unexpected_success": True}
        
        result = await decision_engine._check_achievement_triggers(1, decision, consequences)
        
        assert "fortune_favored" in result
    
    async def test_check_achievement_triggers_no_achievements(self, decision_engine):
        """Test achievement check with no triggered achievements."""
        decision = StoryDecision(
            id="normal_decision", chapter_id="chapter_01",
            decision_text="Normal choice", decision_type=DecisionType.CHARACTER_RESPONSE,
            character_impact={"sam": 2}  # Low impact
        )
        
        consequences = {}  # No special consequences
        
        result = await decision_engine._check_achievement_triggers(1, decision, consequences)
        
        assert result == []

    # Decision Chain and Pattern Tests
    
    async def test_calculate_decision_chain_bonus_consistency(self, decision_engine):
        """Test decision chain bonus for consistent decisions."""
        previous_decisions = ["moral_choice_1", "moral_choice_2", "moral_choice_3"]
        current_decision = StoryDecision(
            id="moral_choice_4", chapter_id="chapter_04",
            decision_text="Another moral choice", decision_type=DecisionType.MORAL_DILEMMA
        )
        
        with patch.object(decision_engine, '_get_decision_type') as mock_type:
            mock_type.return_value = "moral_dilemma"  # All same type
            
            result = await decision_engine._calculate_decision_chain_bonus(
                previous_decisions, current_decision
            )
            
            assert result["decision_consistency_bonus"] == 3
    
    async def test_calculate_decision_chain_bonus_diversity(self, decision_engine):
        """Test decision chain bonus for diverse decisions."""
        previous_decisions = ["moral_choice", "strategic_choice", "relationship_choice"]
        current_decision = StoryDecision(
            id="character_choice", chapter_id="chapter_04",
            decision_text="Character choice", decision_type=DecisionType.CHARACTER_RESPONSE
        )
        
        with patch.object(decision_engine, '_get_decision_type') as mock_type:
            # All different types
            mock_type.side_effect = ["moral_dilemma", "strategic_choice", "relationship_action"]
            
            result = await decision_engine._calculate_decision_chain_bonus(
                previous_decisions, current_decision
            )
            
            assert result["decision_diversity_bonus"] == 3
    
    async def test_calculate_decision_chain_bonus_insufficient_history(self, decision_engine):
        """Test decision chain bonus with insufficient history."""
        previous_decisions = ["single_decision"]  # Not enough history
        current_decision = Mock()
        
        result = await decision_engine._calculate_decision_chain_bonus(
            previous_decisions, current_decision
        )
        
        assert result == {}
    
    def test_get_decision_type_extraction(self, decision_engine):
        """Test decision type extraction from decision ID."""
        assert decision_engine._get_decision_type("moral_choice_1") == "moral_dilemma"
        assert decision_engine._get_decision_type("strategic_plan_2") == "strategic_choice"
        assert decision_engine._get_decision_type("random_decision") == "general"

    # Consequence Limitation Tests
    
    def test_limit_consequence_scope_max_consequences(self, decision_engine):
        """Test consequence scope limitation by maximum count."""
        # Create more consequences than the limit
        consequences = {f"consequence_{i}": f"value_{i}" for i in range(10)}
        
        with patch.object(decision_engine, '_calculate_consequence_priority') as mock_priority:
            # Set up priorities so we can predict which ones survive
            mock_priority.side_effect = lambda name, value: int(name.split("_")[1])
            
            result = decision_engine._limit_consequence_scope(consequences)
            
            # Should be limited to max_consequences_per_decision (5)
            assert len(result) == decision_engine.max_consequences_per_decision
    
    def test_limit_consequence_scope_moral_impact_bounds(self, decision_engine):
        """Test consequence scope limitation for moral impact bounds."""
        consequences = {
            "moral_impact": {
                "compassionate": 50,    # Too high
                "pragmatic": -30,       # Too low
                "curious": 15           # Within bounds
            },
            "other_consequence": "value"
        }
        
        result = decision_engine._limit_consequence_scope(consequences)
        
        # Moral impacts should be bounded to [-20, 20]
        assert result["moral_impact"]["compassionate"] == 20
        assert result["moral_impact"]["pragmatic"] == -20
        assert result["moral_impact"]["curious"] == 15
        assert result["other_consequence"] == "value"  # Unchanged
    
    def test_calculate_consequence_priority(self, decision_engine):
        """Test consequence priority calculation."""
        # Test different consequence types
        assert decision_engine._calculate_consequence_priority("moral_impact", {}) == 10
        assert decision_engine._calculate_consequence_priority("character_impact", {}) == 9
        assert decision_engine._calculate_consequence_priority("story_branch", {}) == 8
        assert decision_engine._calculate_consequence_priority("unknown_type", {}) == 1
        
        # Test priority boost for significant values
        large_dict = {f"key_{i}": f"value_{i}" for i in range(5)}
        priority_large = decision_engine._calculate_consequence_priority("test", large_dict)
        priority_small = decision_engine._calculate_consequence_priority("test", {})
        assert priority_large > priority_small
        
        # Test priority boost for large numeric values
        priority_big_num = decision_engine._calculate_consequence_priority("test", 15)
        priority_small_num = decision_engine._calculate_consequence_priority("test", 5)
        assert priority_big_num > priority_small_num

    # Long-term Impact Calculation Tests
    
    async def test_calculate_branch_cascade_effects_moral_dilemma(self, decision_engine):
        """Test branch cascade effects for moral dilemma."""
        decision = StoryDecision(
            id="moral_decision", chapter_id="chapter_01",
            decision_text="Moral choice", decision_type=DecisionType.MORAL_DILEMMA,
            immediate_consequences={"moral_impact": {"compassionate": 18}}
        )
        
        consequences = {}
        
        result = await decision_engine._calculate_branch_cascade_effects(1, decision, consequences)
        
        assert result["ending_bias"] == "compassionate"
        assert result["ending_weight"] == 18
    
    async def test_calculate_branch_cascade_effects_strategic_choice(self, decision_engine):
        """Test branch cascade effects for strategic choice."""
        decision = StoryDecision(
            id="strategic_aggressive_choice", chapter_id="chapter_02",
            decision_text="Aggressive strategy", decision_type=DecisionType.STRATEGIC_CHOICE
        )
        
        consequences = {}
        
        result = await decision_engine._calculate_branch_cascade_effects(1, decision, consequences)
        
        assert result["strategic_preference"] == "choice"  # Last part of decision ID
    
    async def test_calculate_branch_cascade_effects_relationship_action(self, decision_engine):
        """Test branch cascade effects for relationship action."""
        decision = StoryDecision(
            id="relationship_decision", chapter_id="chapter_01",
            decision_text="Help friend", decision_type=DecisionType.RELATIONSHIP_ACTION,
            character_impact={"diana": 8, "alex": -6}  # Significant impacts
        )
        
        consequences = {}
        
        result = await decision_engine._calculate_branch_cascade_effects(1, decision, consequences)
        
        assert result["diana_arc_influence"] == "positive"
        assert result["alex_arc_influence"] == "negative"
    
    async def test_calculate_relationship_evolution_predictions(self, decision_engine):
        """Test relationship evolution predictions."""
        decision = StoryDecision(
            id="evolution_decision", chapter_id="chapter_01",
            decision_text="Relationship choice", decision_type=DecisionType.RELATIONSHIP_ACTION,
            character_impact={"diana": 6, "alex": 8}
        )
        
        with patch.object(decision_engine, '_load_user_relationships') as mock_relationships:
            mock_relationships.return_value = {
                "diana": {"level": 20, "type": "neutral"},     # Should evolve to friendship
                "alex": {"level": 55, "type": "friendship"}    # Should approach romance threshold
            }
            
            result = await decision_engine._calculate_relationship_evolution(1, decision)
            
            assert result["diana_evolving_to"] == "friendship"  # 20 + 6 = 26 >= 25
            assert result["alex_deep_content_upcoming"] is True  # 55 + 8 = 63 >= 75 (almost)
    
    async def test_calculate_moral_trajectory_mastery_approaching(self, decision_engine):
        """Test moral trajectory calculation for approaching mastery."""
        decision = StoryDecision(
            id="moral_decision", chapter_id="chapter_01",
            decision_text="Compassionate choice", decision_type=DecisionType.MORAL_DILEMMA,
            immediate_consequences={"moral_impact": {"compassionate": 15}}
        )
        
        with patch.object(decision_engine, '_load_user_moral_alignment') as mock_alignment:
            with patch.object(decision_engine, '_get_opposing_traits') as mock_opposing:
                
                mock_alignment.return_value = {"compassionate": 40, "pragmatic": 30}
                mock_opposing.return_value = ["pragmatic"]
                
                result = await decision_engine._calculate_moral_trajectory(1, decision)
                
                # 40 + 15 = 55, which crosses 50 threshold
                assert result["compassionate_mastery_approaching"] is True
    
    async def test_calculate_moral_trajectory_conflict_developing(self, decision_engine):
        """Test moral trajectory calculation for developing conflicts."""
        decision = StoryDecision(
            id="complex_moral_decision", chapter_id="chapter_01",
            decision_text="Complex choice", decision_type=DecisionType.MORAL_DILEMMA,
            immediate_consequences={"moral_impact": {"compassionate": 20}}
        )
        
        with patch.object(decision_engine, '_load_user_moral_alignment') as mock_alignment:
            with patch.object(decision_engine, '_get_opposing_traits') as mock_opposing:
                
                # High values in opposing traits
                mock_alignment.return_value = {"compassionate": 45, "pragmatic": 50}
                mock_opposing.return_value = ["pragmatic"]
                
                result = await decision_engine._calculate_moral_trajectory(1, decision)
                
                # 45 + 20 = 65 > 60, and pragmatic = 50 > 40, so conflict develops
                conflict_data = result.get("moral_conflict_developing")
                assert conflict_data is not None
                assert "compassionate" in conflict_data["traits"]
                assert "pragmatic" in conflict_data["traits"]
    
    def test_get_opposing_traits(self, decision_engine):
        """Test opposing traits identification."""
        assert "pragmatic" in decision_engine._get_opposing_traits("compassionate")
        assert "traditional" in decision_engine._get_opposing_traits("rebellious")
        assert "cautious" in decision_engine._get_opposing_traits("curious")
        
        # Test reverse mappings
        assert "compassionate" in decision_engine._get_opposing_traits("pragmatic")
        assert "rebellious" in decision_engine._get_opposing_traits("traditional")
        assert "curious" in decision_engine._get_opposing_traits("cautious")
        
        # Test unknown trait
        assert decision_engine._get_opposing_traits("unknown_trait") == []

    # Content Prediction Tests
    
    async def test_predict_future_content_unlocks_character_based(self, decision_engine):
        """Test future content prediction based on character impacts."""
        decision = StoryDecision(
            id="character_focused_decision", chapter_id="chapter_01",
            decision_text="Character choice", decision_type=DecisionType.RELATIONSHIP_ACTION,
            character_impact={"diana": 9, "alex": 6, "sam": 3}  # Various impact levels
        )
        
        consequences = {}
        
        result = await decision_engine._predict_future_content_unlocks(1, decision, consequences)
        
        assert result["diana_exclusive_content"] == "high_probability"  # Impact 9 >= 8
        assert result["alex_bonus_scenes"] == "medium_probability"     # Impact 6 >= 5
        assert "sam_exclusive_content" not in result                   # Impact 3 < 5
    
    async def test_predict_future_content_unlocks_moral_paths(self, decision_engine):
        """Test future content prediction based on moral alignment."""
        decision = StoryDecision(
            id="high_moral_decision", chapter_id="chapter_01",
            decision_text="Strong moral choice", decision_type=DecisionType.MORAL_DILEMMA,
            immediate_consequences={"moral_impact": {"rebellious": 16, "compassionate": 8}}
        )
        
        consequences = {}
        
        result = await decision_engine._predict_future_content_unlocks(1, decision, consequences)
        
        assert result["rebellious_path_content"] == "unlocking_soon"  # 16 >= 15
        assert "compassionate_path_content" not in result             # 8 < 15
    
    async def test_predict_future_content_unlocks_secret_content(self, decision_engine):
        """Test future content prediction for secret content."""
        decision = StoryDecision(
            id="secret_decision", chapter_id="chapter_01",
            decision_text="Secret choice", decision_type=DecisionType.STRATEGIC_CHOICE
        )
        
        consequences = {"unexpected_success": True}
        
        result = await decision_engine._predict_future_content_unlocks(1, decision, consequences)
        
        assert result["secret_content"] == "possible_unlock"

    # Relationship Impact Description Tests
    
    def test_describe_relationship_impact_levels(self, decision_engine):
        """Test relationship impact description for various levels."""
        assert decision_engine._describe_relationship_impact(9) == "Your bond grows significantly stronger"
        assert decision_engine._describe_relationship_impact(6) == "They appreciate your choice"
        assert decision_engine._describe_relationship_impact(3) == "A small positive step forward"
        assert decision_engine._describe_relationship_impact(0) == "No significant change"
        assert decision_engine._describe_relationship_impact(-3) == "A slight strain on your connection"
        assert decision_engine._describe_relationship_impact(-6) == "They're disappointed in your choice"
        assert decision_engine._describe_relationship_impact(-9) == "Serious damage to your relationship"
    
    async def test_format_relationship_changes(self, decision_engine):
        """Test relationship changes formatting."""
        character_impacts = {"diana": 7, "alex": -5, "sam": 2}
        
        result = await decision_engine._format_relationship_changes(character_impacts)
        
        # Check all characters are included
        assert "diana" in result
        assert "alex" in result
        assert "sam" in result
        
        # Check format structure
        diana_change = result["diana"]
        assert diana_change["level_change"] == 7
        assert "impact_description" in diana_change
        assert diana_change["new_interaction_available"] is True  # |7| >= 5
        
        alex_change = result["alex"]
        assert alex_change["level_change"] == -5
        assert alex_change["new_interaction_available"] is True  # |-5| >= 5
        
        sam_change = result["sam"]
        assert sam_change["level_change"] == 2
        assert sam_change["new_interaction_available"] is False  # |2| < 5

    # Performance and Concurrency Tests
    
    async def test_concurrent_decision_processing(self, decision_engine):
        """Test concurrent decision processing."""
        decisions = [
            ("user_1", "chapter_01", "decision_1"),
            ("user_2", "chapter_01", "decision_2"),
            ("user_3", "chapter_02", "decision_3")
        ]
        
        with patch.object(decision_engine, '_load_decision_data') as mock_load:
            with patch.object(decision_engine, '_validate_decision_eligibility'):
                with patch.object(decision_engine, 'calculate_immediate_consequences', return_value={}):
                    with patch.object(decision_engine, '_calculate_character_impacts', return_value={}):
                        with patch.object(decision_engine, 'update_narrative_flags', return_value={}):
                            with patch.object(decision_engine, '_determine_unlocked_content', return_value=[]):
                                with patch.object(decision_engine, '_calculate_next_chapter', return_value=None):
                                    with patch.object(decision_engine, '_check_achievement_triggers', return_value=[]):
                                        with patch.object(decision_engine, 'calculate_long_term_impact', return_value={}):
                                            with patch.object(decision_engine, '_record_decision_history'):
                                                with patch.object(decision_engine, '_format_relationship_changes', return_value={}):
                                                    
                                                    # Mock decision loading
                                                    def mock_decision_load(decision_id):
                                                        return StoryDecision(
                                                            id=decision_id,
                                                            chapter_id=decision_id.split("_")[0] + "_01",
                                                            decision_text="Test choice",
                                                            decision_type=DecisionType.MORAL_DILEMMA
                                                        )
                                                    
                                                    mock_load.side_effect = mock_decision_load
                                                    
                                                    # Process decisions concurrently
                                                    tasks = [
                                                        decision_engine.process_decision(uid, cid, did)
                                                        for uid, cid, did in decisions
                                                    ]
                                                    
                                                    results = await asyncio.gather(*tasks, return_exceptions=True)
                                                    
                                                    # All should succeed
                                                    assert all(isinstance(r, DecisionResult) and r.success for r in results)
                                                    assert decision_engine._stats["decisions_processed"] == 3
    
    async def test_decision_caching_performance(self, decision_engine):
        """Test decision caching improves performance."""
        decision_id = "cached_decision"
        
        # First load - cache miss
        result1 = await decision_engine._load_decision_data(decision_id)
        assert decision_engine._stats["cache_misses"] == 1
        assert decision_engine._stats["cache_hits"] == 0
        
        # Second load - cache hit
        result2 = await decision_engine._load_decision_data(decision_id)
        assert decision_engine._stats["cache_hits"] == 1
        
        # Results should be identical
        assert result1.id == result2.id
        assert result1.decision_text == result2.decision_text
    
    async def test_decision_history_recording(self, decision_engine):
        """Test decision history recording."""
        user_id = 1
        chapter_id = "chapter_01"
        decision = StoryDecision(
            id="recorded_decision", chapter_id=chapter_id,
            decision_text="Test choice", decision_type=DecisionType.MORAL_DILEMMA,
            character_impact={"diana": 5}
        )
        consequences = {"moral_growth": 10}
        
        # Should not raise exception
        await decision_engine._record_decision_history(user_id, chapter_id, decision, consequences)

    # Edge Cases and Error Conditions
    
    async def test_empty_character_impacts(self, decision_engine):
        """Test decision processing with no character impacts."""
        decision = StoryDecision(
            id="no_impact_decision", chapter_id="chapter_01",
            decision_text="Solo choice", decision_type=DecisionType.STRATEGIC_CHOICE,
            character_impact={}  # No character impacts
        )
        
        with patch.object(decision_engine, '_load_user_relationships', return_value={}):
            
            result = await decision_engine._calculate_character_impacts(1, decision, None)
            
            assert result == {}
    
    async def test_extreme_moral_alignment_values(self, decision_engine):
        """Test handling of extreme moral alignment values."""
        decision_obj = StoryDecision(
            id="extreme_moral_decision", chapter_id="chapter_01",
            decision_text="Extreme choice", decision_type=DecisionType.MORAL_DILEMMA,
            immediate_consequences={"moral_impact": {"compassionate": 1000}}  # Extreme value
        )
        
        with patch.object(decision_engine, '_load_user_moral_alignment') as mock_alignment:
            with patch.object(decision_engine, '_load_user_completed_chapters', return_value=[]):
                
                mock_alignment.return_value = {"compassionate": 0}
                
                # Should handle extreme values gracefully
                result = await decision_engine._calculate_dynamic_consequences(1, decision_obj)
                
                # Should still detect moral growth opportunity
                assert result.get("moral_growth_opportunity") is True
    
    async def test_massive_decision_chain(self, decision_engine):
        """Test decision processing with massive decision history."""
        previous_decisions = [f"decision_{i}" for i in range(100)]  # Large history
        current_decision = StoryDecision(
            id="chain_decision", chapter_id="chapter_50",
            decision_text="Chain choice", decision_type=DecisionType.MORAL_DILEMMA
        )
        
        with patch.object(decision_engine, '_get_decision_type', return_value="moral_dilemma"):
            
            result = await decision_engine._calculate_decision_chain_bonus(
                previous_decisions, current_decision
            )
            
            # Should handle large chain without issues
            assert result["decision_consistency_bonus"] == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])