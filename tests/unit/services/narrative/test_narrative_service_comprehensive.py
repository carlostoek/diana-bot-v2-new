"""
Comprehensive Unit Tests for Narrative Service

This module provides extensive unit test coverage for the Diana Bot V2 Narrative Service,
including all core functionality, edge cases, and error conditions with >95% coverage.
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

from services.narrative.service import NarrativeService
from services.narrative.interfaces import (
    ChapterContent,
    DecisionResult,
    Dialogue,
    UnlockedContent,
    ContentType,
    NarrativeServiceError,
    VIPRequiredError,
)
from services.narrative.models import (
    NarrativeDecisionEvent,
    CharacterInteractionEvent,
    StoryUnlockEvent,
    NarrativePointsEvent,
    POINTS_AWARDS,
)
from core.interfaces import IEventBus


class TestNarrativeService:
    """Comprehensive test suite for NarrativeService."""
    
    @pytest.fixture
    async def event_bus_mock(self):
        """Create a mock event bus."""
        mock = AsyncMock(spec=IEventBus)
        mock._is_connected = True
        mock.health_check.return_value = {"status": "healthy"}
        return mock
    
    @pytest.fixture
    async def narrative_service(self, event_bus_mock):
        """Create a narrative service instance for testing."""
        service = NarrativeService(
            event_bus=event_bus_mock,
            enable_vip_content=True,
            enable_analytics=True
        )
        await service.initialize()
        return service
    
    @pytest.fixture
    async def narrative_service_no_vip(self, event_bus_mock):
        """Create a narrative service instance with VIP disabled."""
        service = NarrativeService(
            event_bus=event_bus_mock,
            enable_vip_content=False,
            enable_analytics=False
        )
        await service.initialize()
        return service

    # Initialization Tests
    
    async def test_initialize_success(self, event_bus_mock):
        """Test successful service initialization."""
        service = NarrativeService(event_bus=event_bus_mock)
        
        assert not service._initialized
        await service.initialize()
        
        assert service._initialized
        assert service.event_bus == event_bus_mock
        event_bus_mock.initialize.assert_called_once()
    
    async def test_initialize_event_bus_not_connected(self):
        """Test initialization when event bus is not connected."""
        event_bus_mock = AsyncMock(spec=IEventBus)
        event_bus_mock._is_connected = False
        
        service = NarrativeService(event_bus=event_bus_mock)
        await service.initialize()
        
        event_bus_mock.initialize.assert_called_once()
        assert service._initialized
    
    async def test_initialize_already_initialized(self, narrative_service):
        """Test initialization when service is already initialized."""
        assert narrative_service._initialized
        
        # Should not re-initialize
        await narrative_service.initialize()
        assert narrative_service._initialized
    
    async def test_initialize_failure(self, event_bus_mock):
        """Test initialization failure handling."""
        event_bus_mock.initialize.side_effect = Exception("Connection failed")
        
        service = NarrativeService(event_bus=event_bus_mock)
        
        with pytest.raises(NarrativeServiceError, match="Initialization failed"):
            await service.initialize()
        
        assert not service._initialized
    
    # Cleanup Tests
    
    async def test_cleanup_success(self, narrative_service):
        """Test successful service cleanup."""
        assert narrative_service._initialized
        
        await narrative_service.cleanup()
        
        assert not narrative_service._initialized
    
    async def test_cleanup_not_initialized(self, event_bus_mock):
        """Test cleanup when service is not initialized."""
        service = NarrativeService(event_bus=event_bus_mock)
        
        # Should not fail if not initialized
        await service.cleanup()
        assert not service._initialized
    
    async def test_cleanup_with_error(self, narrative_service):
        """Test cleanup with subscription cleanup error."""
        narrative_service.event_bus.unsubscribe.side_effect = Exception("Unsubscribe failed")
        
        # Should not raise exception
        await narrative_service.cleanup()
        assert not narrative_service._initialized

    # Get Current Chapter Tests
    
    @patch('services.narrative.service.StoryEngine')
    async def test_get_current_chapter_success(self, mock_story_engine, narrative_service):
        """Test successful chapter content retrieval."""
        # Mock story engine
        mock_engine = AsyncMock()
        mock_story_engine.return_value = mock_engine
        narrative_service.story_engine = mock_engine
        
        # Mock story state
        mock_story_state = Mock()
        mock_story_state.current_chapter = "chapter_01"
        mock_story_state.vip_content_available = True
        mock_engine.load_story_state.return_value = mock_story_state
        
        # Mock chapter content
        mock_content = ChapterContent(
            chapter_id="chapter_01",
            title="Test Chapter",
            content="Test content",
            decisions=[],
            character_appearances=["diana"],
            vip_required=False
        )
        mock_engine.generate_chapter_content.return_value = mock_content
        
        result = await narrative_service.get_current_chapter(1)
        
        assert isinstance(result, ChapterContent)
        assert result.chapter_id == "chapter_01"
        assert result.title == "Test Chapter"
        assert narrative_service._stats["chapters_served"] == 1
        
        mock_engine.load_story_state.assert_called_once_with(1)
        mock_engine.generate_chapter_content.assert_called_once()
    
    @patch('services.narrative.service.StoryEngine')
    async def test_get_current_chapter_vip_required_success(self, mock_story_engine, narrative_service):
        """Test VIP chapter access with valid VIP status."""
        mock_engine = AsyncMock()
        mock_story_engine.return_value = mock_engine
        narrative_service.story_engine = mock_engine
        
        mock_story_state = Mock()
        mock_story_state.current_chapter = "vip_chapter"
        mock_story_state.vip_content_available = True
        mock_engine.load_story_state.return_value = mock_story_state
        
        mock_content = ChapterContent(
            chapter_id="vip_chapter",
            title="VIP Chapter",
            content="VIP content",
            decisions=[],
            character_appearances=[],
            vip_required=True
        )
        mock_engine.generate_chapter_content.return_value = mock_content
        
        result = await narrative_service.get_current_chapter(1)
        
        assert result.vip_required
        assert narrative_service._stats["vip_content_served"] == 1
    
    @patch('services.narrative.service.StoryEngine')
    async def test_get_current_chapter_vip_required_denied(self, mock_story_engine, narrative_service):
        """Test VIP chapter access denial without VIP status."""
        mock_engine = AsyncMock()
        mock_story_engine.return_value = mock_engine
        narrative_service.story_engine = mock_engine
        
        mock_story_state = Mock()
        mock_story_state.current_chapter = "vip_chapter"
        mock_story_state.vip_content_available = False
        mock_engine.load_story_state.return_value = mock_story_state
        
        mock_content = ChapterContent(
            chapter_id="vip_chapter",
            title="VIP Chapter",
            content="VIP content",
            decisions=[],
            character_appearances=[],
            vip_required=True
        )
        mock_engine.generate_chapter_content.return_value = mock_content
        
        with pytest.raises(VIPRequiredError, match="requires VIP access"):
            await narrative_service.get_current_chapter(1)
    
    @patch('services.narrative.service.StoryEngine')
    async def test_get_current_chapter_with_analytics(self, mock_story_engine, narrative_service):
        """Test chapter retrieval with analytics enabled."""
        mock_engine = AsyncMock()
        narrative_service.story_engine = mock_engine
        
        mock_story_state = Mock()
        mock_story_state.current_chapter = "chapter_01"
        mock_story_state.vip_content_available = True
        mock_engine.load_story_state.return_value = mock_story_state
        
        mock_content = ChapterContent(
            chapter_id="chapter_01",
            title="Test Chapter",
            content="Test content",
            decisions=[],
            character_appearances=[],
            vip_required=False,
            personalization_data={"style": "action"}
        )
        mock_engine.generate_chapter_content.return_value = mock_content
        
        await narrative_service.get_current_chapter(1)
        
        # Verify analytics event was published
        narrative_service.event_bus.publish.assert_called()
        published_events = [call.args[0] for call in narrative_service.event_bus.publish.call_args_list]
        analytics_events = [event for event in published_events if hasattr(event, 'type') and 
                          event.type == 'narrative.points_award']
        assert len(analytics_events) > 0
    
    @patch('services.narrative.service.StoryEngine')
    async def test_get_current_chapter_analytics_disabled(self, mock_story_engine, narrative_service_no_vip):
        """Test chapter retrieval with analytics disabled."""
        mock_engine = AsyncMock()
        narrative_service_no_vip.story_engine = mock_engine
        
        mock_story_state = Mock()
        mock_story_state.current_chapter = "chapter_01"
        mock_story_state.vip_content_available = True
        mock_engine.load_story_state.return_value = mock_story_state
        
        mock_content = ChapterContent(
            chapter_id="chapter_01",
            title="Test Chapter",
            content="Test content",
            decisions=[],
            character_appearances=[],
            vip_required=False
        )
        mock_engine.generate_chapter_content.return_value = mock_content
        
        await narrative_service_no_vip.get_current_chapter(1)
        
        # Should not publish analytics events
        narrative_service_no_vip.event_bus.publish.assert_not_called()
    
    @patch('services.narrative.service.StoryEngine')
    async def test_get_current_chapter_error(self, mock_story_engine, narrative_service):
        """Test chapter retrieval error handling."""
        mock_engine = AsyncMock()
        narrative_service.story_engine = mock_engine
        mock_engine.load_story_state.side_effect = Exception("Story engine error")
        
        with pytest.raises(NarrativeServiceError, match="Cannot retrieve chapter"):
            await narrative_service.get_current_chapter(1)

    # Process Decision Tests
    
    @patch('services.narrative.service.DecisionEngine')
    @patch('services.narrative.service.CharacterSystem')
    @patch('services.narrative.service.StoryEngine')
    async def test_process_decision_success(self, mock_story_engine, mock_char_system, 
                                          mock_decision_engine, narrative_service):
        """Test successful decision processing."""
        # Setup mocks
        mock_story_eng = AsyncMock()
        mock_char_sys = AsyncMock()
        mock_dec_eng = AsyncMock()
        
        narrative_service.story_engine = mock_story_eng
        narrative_service.character_system = mock_char_sys
        narrative_service.decision_engine = mock_dec_eng
        
        # Mock story state
        mock_story_state = Mock()
        mock_story_state.current_chapter = "chapter_01"
        mock_story_eng.load_story_state.return_value = mock_story_state
        
        # Mock decision result
        mock_result = DecisionResult(
            success=True,
            user_id=1,
            chapter_id="chapter_01",
            decision_id="test_decision",
            immediate_consequences={"moral_growth": 10},
            character_impacts={"diana": 5},
            unlocked_content=["bonus_scene"],
            next_chapter="chapter_02",
            relationship_changes={"diana": {"level_change": 5}},
            achievement_triggers=["decision_maker"]
        )
        mock_dec_eng.process_decision.return_value = mock_result
        
        result = await narrative_service.process_decision(1, "test_decision")
        
        assert result.success
        assert result.user_id == 1
        assert result.character_impacts == {"diana": 5}
        assert narrative_service._stats["decisions_processed"] == 1
        
        # Verify event publishing
        narrative_service.event_bus.publish.assert_called()
        published_events = [call.args[0] for call in narrative_service.event_bus.publish.call_args_list]
        
        # Check for NarrativeDecisionEvent
        decision_events = [e for e in published_events if isinstance(e, NarrativeDecisionEvent)]
        assert len(decision_events) > 0
        
        # Check for character relationship update
        mock_char_sys.update_relationship.assert_called_once()
    
    @patch('services.narrative.service.DecisionEngine')
    @patch('services.narrative.service.CharacterSystem')
    @patch('services.narrative.service.StoryEngine')
    async def test_process_decision_failure(self, mock_story_engine, mock_char_system, 
                                          mock_decision_engine, narrative_service):
        """Test decision processing failure."""
        mock_story_eng = AsyncMock()
        mock_dec_eng = AsyncMock()
        
        narrative_service.story_engine = mock_story_eng
        narrative_service.decision_engine = mock_dec_eng
        
        mock_story_state = Mock()
        mock_story_state.current_chapter = "chapter_01"
        mock_story_eng.load_story_state.return_value = mock_story_state
        
        # Mock failed decision result
        mock_result = DecisionResult(
            success=False,
            user_id=1,
            chapter_id="chapter_01",
            decision_id="test_decision",
            immediate_consequences={},
            character_impacts={},
            unlocked_content=[],
            error_message="Decision failed"
        )
        mock_dec_eng.process_decision.return_value = mock_result
        
        result = await narrative_service.process_decision(1, "test_decision")
        
        assert not result.success
        assert result.error_message == "Decision failed"
    
    @patch('services.narrative.service.StoryEngine')
    async def test_process_decision_with_context(self, mock_story_engine, narrative_service):
        """Test decision processing with context."""
        mock_engine = AsyncMock()
        narrative_service.story_engine = mock_engine
        narrative_service.decision_engine = AsyncMock()
        
        mock_story_state = Mock()
        mock_story_state.current_chapter = "chapter_01"
        mock_engine.load_story_state.return_value = mock_story_state
        
        mock_result = DecisionResult(
            success=True,
            user_id=1,
            chapter_id="chapter_01",
            decision_id="test_decision",
            immediate_consequences={},
            character_impacts={},
            unlocked_content=[]
        )
        narrative_service.decision_engine.process_decision.return_value = mock_result
        
        context = {"emotional_state": "excited", "time_pressure": True}
        result = await narrative_service.process_decision(1, "test_decision", context)
        
        assert result.success
        narrative_service.decision_engine.process_decision.assert_called_once()
        call_args = narrative_service.decision_engine.process_decision.call_args
        assert call_args[1]["decision_context"] == context
    
    @patch('services.narrative.service.StoryEngine')
    async def test_process_decision_unlocked_content_event(self, mock_story_engine, narrative_service):
        """Test decision processing with content unlocks."""
        mock_engine = AsyncMock()
        narrative_service.story_engine = mock_engine
        narrative_service.decision_engine = AsyncMock()
        
        mock_story_state = Mock()
        mock_story_state.current_chapter = "chapter_01"
        mock_engine.load_story_state.return_value = mock_story_state
        
        mock_result = DecisionResult(
            success=True,
            user_id=1,
            chapter_id="chapter_01",
            decision_id="test_decision",
            immediate_consequences={},
            character_impacts={},
            unlocked_content=["bonus_scene", "character_dialogue"]
        )
        narrative_service.decision_engine.process_decision.return_value = mock_result
        
        await narrative_service.process_decision(1, "test_decision")
        
        # Verify unlock event was published
        published_events = [call.args[0] for call in narrative_service.event_bus.publish.call_args_list]
        unlock_events = [e for e in published_events if isinstance(e, StoryUnlockEvent)]
        assert len(unlock_events) > 0
        
        unlock_event = unlock_events[0]
        assert unlock_event.user_id == 1
        assert len(unlock_event.unlocked_content) == 2
    
    @patch('services.narrative.service.StoryEngine')
    async def test_process_decision_achievement_triggers(self, mock_story_engine, narrative_service):
        """Test decision processing with achievement triggers."""
        mock_engine = AsyncMock()
        narrative_service.story_engine = mock_engine
        narrative_service.decision_engine = AsyncMock()
        
        mock_story_state = Mock()
        mock_story_state.current_chapter = "chapter_01"
        mock_engine.load_story_state.return_value = mock_story_state
        
        mock_result = DecisionResult(
            success=True,
            user_id=1,
            chapter_id="chapter_01",
            decision_id="test_decision",
            immediate_consequences={},
            character_impacts={},
            unlocked_content=[],
            achievement_triggers=["moral_master", "decision_maker"]
        )
        narrative_service.decision_engine.process_decision.return_value = mock_result
        
        with patch.object(narrative_service, '_trigger_narrative_achievement') as mock_trigger:
            await narrative_service.process_decision(1, "test_decision")
            
            # Should trigger both achievements
            assert mock_trigger.call_count == 2

    # Get Character Interaction Tests
    
    @patch('services.narrative.service.CharacterSystem')
    async def test_get_character_interaction_success(self, mock_char_system, narrative_service):
        """Test successful character interaction."""
        mock_char_sys = AsyncMock()
        narrative_service.character_system = mock_char_sys
        
        mock_dialogue = Dialogue(
            character_id="diana",
            dialogue_text="Hello, traveler.",
            relationship_context={"level": 25, "type": "friendship"},
            available_responses=[
                {"id": "friendly", "text": "Hello Diana!", "impact": 2}
            ],
            mood="welcoming"
        )
        mock_char_sys.generate_character_dialogue.return_value = mock_dialogue
        
        result = await narrative_service.get_character_interaction(1, "diana")
        
        assert isinstance(result, Dialogue)
        assert result.character_id == "diana"
        assert result.dialogue_text == "Hello, traveler."
        assert result.mood == "welcoming"
        assert narrative_service._stats["character_interactions"] == 1
        
        mock_char_sys.generate_character_dialogue.assert_called_once_with(
            user_id=1,
            character_id="diana",
            context=None
        )
        
        # Verify interaction event was published
        published_events = [call.args[0] for call in narrative_service.event_bus.publish.call_args_list]
        interaction_events = [e for e in published_events if isinstance(e, CharacterInteractionEvent)]
        assert len(interaction_events) > 0
    
    @patch('services.narrative.service.CharacterSystem')
    async def test_get_character_interaction_with_context(self, mock_char_system, narrative_service):
        """Test character interaction with context."""
        mock_char_sys = AsyncMock()
        narrative_service.character_system = mock_char_sys
        
        mock_dialogue = Dialogue(
            character_id="alex",
            dialogue_text="Ready for adventure?",
            relationship_context={"level": 50, "type": "friendship"},
            available_responses=[]
        )
        mock_char_sys.generate_character_dialogue.return_value = mock_dialogue
        
        context = {"scene": "training_grounds", "mood": "excited"}
        result = await narrative_service.get_character_interaction(1, "alex", context)
        
        assert result.character_id == "alex"
        mock_char_sys.generate_character_dialogue.assert_called_once_with(
            user_id=1,
            character_id="alex",
            context=context
        )
    
    @patch('services.narrative.service.CharacterSystem')
    async def test_get_character_interaction_error(self, mock_char_system, narrative_service):
        """Test character interaction error handling."""
        mock_char_sys = AsyncMock()
        narrative_service.character_system = mock_char_sys
        mock_char_sys.generate_character_dialogue.side_effect = Exception("Character error")
        
        with pytest.raises(NarrativeServiceError, match="Cannot generate character interaction"):
            await narrative_service.get_character_interaction(1, "diana")

    # Check Story Unlocks Tests
    
    @patch('services.narrative.service.StoryEngine')
    async def test_check_story_unlocks_success(self, mock_story_engine, narrative_service):
        """Test successful story unlocks check."""
        mock_engine = AsyncMock()
        narrative_service.story_engine = mock_engine
        
        mock_story_state = Mock()
        mock_story_state.completed_chapters = ["prologue", "chapter_01"]
        mock_story_state.story_flags = {"hero_path": True}
        mock_story_state.character_relationships = {"diana": {"level": 75}}
        mock_story_state.moral_alignment = {"compassionate": 80}
        mock_engine.load_story_state.return_value = mock_story_state
        
        unlocked_items = [
            UnlockedContent(
                content_id="hero_chapter_01",
                content_type=ContentType.MAIN_STORY,
                title="Hero's Beginning",
                description="Unlocked by moral alignment",
                unlock_reason="moral_progress"
            )
        ]
        mock_engine.unlock_next_content.return_value = unlocked_items
        
        result = await narrative_service.check_story_unlocks(1)
        
        assert len(result) == 1
        assert result[0].content_id == "hero_chapter_01"
        assert result[0].content_type == ContentType.MAIN_STORY
        
        # Verify unlock event was published
        published_events = [call.args[0] for call in narrative_service.event_bus.publish.call_args_list]
        unlock_events = [e for e in published_events if isinstance(e, StoryUnlockEvent)]
        assert len(unlock_events) > 0
    
    @patch('services.narrative.service.StoryEngine')
    async def test_check_story_unlocks_no_unlocks(self, mock_story_engine, narrative_service):
        """Test story unlocks check with no new unlocks."""
        mock_engine = AsyncMock()
        narrative_service.story_engine = mock_engine
        
        mock_story_state = Mock()
        mock_story_state.completed_chapters = []
        mock_story_state.story_flags = {}
        mock_story_state.character_relationships = {}
        mock_story_state.moral_alignment = {}
        mock_engine.load_story_state.return_value = mock_story_state
        
        mock_engine.unlock_next_content.return_value = []
        
        result = await narrative_service.check_story_unlocks(1)
        
        assert len(result) == 0
        # Should not publish unlock event if no unlocks
        narrative_service.event_bus.publish.assert_not_called()
    
    @patch('services.narrative.service.StoryEngine')
    async def test_check_story_unlocks_error(self, mock_story_engine, narrative_service):
        """Test story unlocks error handling."""
        mock_engine = AsyncMock()
        narrative_service.story_engine = mock_engine
        mock_engine.load_story_state.side_effect = Exception("State load error")
        
        # Should return empty list on error, not raise exception
        result = await narrative_service.check_story_unlocks(1)
        assert result == []

    # Get Story Summary Tests
    
    @patch('services.narrative.service.StoryEngine')
    @patch('services.narrative.service.CharacterSystem')
    async def test_get_story_summary_success(self, mock_char_system, mock_story_engine, narrative_service):
        """Test successful story summary retrieval."""
        mock_story_eng = AsyncMock()
        mock_char_sys = AsyncMock()
        narrative_service.story_engine = mock_story_eng
        narrative_service.character_system = mock_char_sys
        
        # Mock story state
        mock_story_state = Mock()
        mock_story_state.current_chapter = "chapter_02"
        mock_story_state.completed_chapters = ["prologue", "chapter_01"]
        mock_story_state.moral_alignment = {"compassionate": 60, "pragmatic": 30}
        mock_story_state.unlocked_branches = ["main_story", "hero_path"]
        mock_story_state.vip_content_available = True
        mock_story_state.story_flags = {"diana_trust": 75, "_internal_flag": "hidden"}
        mock_story_state.last_updated = datetime.now(timezone.utc)
        mock_story_eng.load_story_state.return_value = mock_story_state
        
        # Mock character relationships
        relationships = {
            "diana": {"level": 75, "type": "mentorship"},
            "alex": {"level": 45, "type": "friendship"}
        }
        mock_char_sys.load_character_relationships.return_value = relationships
        
        # Mock total chapter count
        with patch.object(narrative_service, '_get_total_chapter_count', return_value=20):
            result = await narrative_service.get_story_summary(1)
        
        assert result["user_id"] == 1
        assert result["story_progress"]["current_chapter"] == "chapter_02"
        assert result["story_progress"]["completed_chapters"] == 2
        assert result["story_progress"]["total_chapters"] == 20
        assert result["story_progress"]["progress_percentage"] == 10.0  # 2/20 * 100
        
        assert "diana" in result["character_relationships"]
        assert result["character_relationships"]["diana"]["level"] == 75
        assert result["character_relationships"]["diana"]["type"] == "mentorship"
        
        assert result["moral_alignment"] == {"compassionate": 60, "pragmatic": 30}
        assert result["unlocked_branches"] == ["main_story", "hero_path"]
        assert result["vip_content_available"] is True
        
        # Should exclude internal flags (starting with _)
        assert "diana_trust" in result["story_flags"]
        assert "_internal_flag" not in result["story_flags"]
    
    @patch('services.narrative.service.StoryEngine')
    async def test_get_story_summary_error(self, mock_story_engine, narrative_service):
        """Test story summary error handling."""
        mock_engine = AsyncMock()
        narrative_service.story_engine = mock_engine
        mock_engine.load_story_state.side_effect = Exception("Story state error")
        
        with pytest.raises(NarrativeServiceError, match="Cannot retrieve story summary"):
            await narrative_service.get_story_summary(1)

    # Admin Functions Tests
    
    async def test_admin_unlock_content_success(self, narrative_service):
        """Test successful admin content unlock."""
        with patch.object(narrative_service, '_record_admin_unlock') as mock_record:
            result = await narrative_service.admin_unlock_content(
                admin_id=100,
                user_id=1,
                content_id="special_chapter",
                reason="Beta testing access"
            )
        
        assert result is True
        mock_record.assert_called_once()
        
        # Verify admin event was published
        published_events = [call.args[0] for call in narrative_service.event_bus.publish.call_args_list]
        admin_events = [e for e in published_events if hasattr(e, 'action_type') and 
                       e.action_type == "content_unlocked"]
        assert len(admin_events) > 0
        
        # Verify unlock event was published
        unlock_events = [e for e in published_events if isinstance(e, StoryUnlockEvent)]
        assert len(unlock_events) > 0
    
    async def test_admin_unlock_content_invalid_admin(self, narrative_service):
        """Test admin content unlock with invalid admin ID."""
        result = await narrative_service.admin_unlock_content(
            admin_id=0,  # Invalid admin ID
            user_id=1,
            content_id="special_chapter",
            reason="Invalid access"
        )
        
        assert result is False
        # Should not publish any events
        narrative_service.event_bus.publish.assert_not_called()
    
    async def test_admin_unlock_content_error(self, narrative_service):
        """Test admin content unlock error handling."""
        narrative_service.event_bus.publish.side_effect = Exception("Event bus error")
        
        result = await narrative_service.admin_unlock_content(
            admin_id=100,
            user_id=1,
            content_id="special_chapter",
            reason="Test access"
        )
        
        assert result is False

    # Health Check Tests
    
    async def test_health_check_healthy(self, narrative_service):
        """Test health check when all systems are healthy."""
        with patch.object(narrative_service.story_engine, 'load_story_state') as mock_story:
            with patch.object(narrative_service.character_system, 'load_character_relationships') as mock_char:
                mock_story.return_value = Mock()
                mock_char.return_value = {}
                
                result = await narrative_service.health_check()
        
        assert result["status"] == "healthy"
        assert result["service_initialized"] is True
        assert result["event_bus_connected"] is True
        assert result["story_engine_status"] == "healthy"
        assert result["character_system_status"] == "healthy"
        assert result["decision_engine_status"] == "healthy"
        assert "performance_stats" in result
        assert "last_health_check" in result
    
    async def test_health_check_degraded(self, narrative_service):
        """Test health check when some systems are failing."""
        # Make story engine fail
        with patch.object(narrative_service.story_engine, 'load_story_state') as mock_story:
            with patch.object(narrative_service.character_system, 'load_character_relationships') as mock_char:
                mock_story.side_effect = Exception("Story engine error")
                mock_char.return_value = {}
                
                result = await narrative_service.health_check()
        
        assert result["status"] == "degraded"
        assert result["story_engine_status"] == "unhealthy"
        assert result["character_system_status"] == "healthy"
    
    async def test_health_check_unhealthy(self, narrative_service):
        """Test health check when service is not initialized."""
        narrative_service._initialized = False
        
        result = await narrative_service.health_check()
        
        assert result["status"] == "unhealthy"
        assert result["service_initialized"] is False
    
    async def test_health_check_event_bus_unhealthy(self, narrative_service):
        """Test health check when event bus is unhealthy."""
        narrative_service.event_bus.health_check.return_value = {"status": "unhealthy"}
        
        with patch.object(narrative_service.story_engine, 'load_story_state') as mock_story:
            with patch.object(narrative_service.character_system, 'load_character_relationships') as mock_char:
                mock_story.return_value = Mock()
                mock_char.return_value = {}
                
                result = await narrative_service.health_check()
        
        assert result["status"] == "degraded"
        assert result["event_bus_connected"] is False
    
    async def test_health_check_exception(self, narrative_service):
        """Test health check error handling."""
        narrative_service.event_bus.health_check.side_effect = Exception("Health check error")
        
        result = await narrative_service.health_check()
        
        assert result["status"] == "unhealthy"
        assert "error" in result

    # Event Handler Tests
    
    async def test_handle_user_registered(self, narrative_service):
        """Test user registration event handling."""
        mock_event = Mock()
        mock_event.data = {"user_id": 1, "username": "test_user"}
        
        with patch.object(narrative_service, '_initialize_user_narrative_data') as mock_init:
            await narrative_service._handle_user_registered(mock_event)
            
            mock_init.assert_called_once_with(1)
            assert narrative_service._stats["events_received"] == 1
    
    async def test_handle_user_profile_updated(self, narrative_service):
        """Test user profile update event handling."""
        mock_event = Mock()
        mock_event.data = {
            "user_id": 1,
            "user_data": {
                "narrative_preferences": {
                    "pacing": "fast",
                    "style": "action"
                }
            }
        }
        
        with patch.object(narrative_service, '_update_user_personalization') as mock_update:
            await narrative_service._handle_user_profile_updated(mock_event)
            
            mock_update.assert_called_once()
            assert narrative_service._stats["events_received"] == 1
    
    async def test_handle_achievement_unlocked_narrative(self, narrative_service):
        """Test achievement unlock event handling for narrative achievements."""
        mock_event = Mock()
        mock_event.data = {
            "user_id": 1,
            "achievement_id": "moral_master",
            "context": {"source": "narrative", "decision_id": "moral_choice_1"}
        }
        
        with patch.object(narrative_service, '_award_achievement_story_content') as mock_award:
            await narrative_service._handle_achievement_unlocked(mock_event)
            
            mock_award.assert_called_once()
            assert narrative_service._stats["events_received"] == 1
    
    async def test_handle_achievement_unlocked_non_narrative(self, narrative_service):
        """Test achievement unlock event handling for non-narrative achievements."""
        mock_event = Mock()
        mock_event.data = {
            "user_id": 1,
            "achievement_id": "game_master",
            "context": {"source": "gamification"}
        }
        
        with patch.object(narrative_service, '_award_achievement_story_content') as mock_award:
            await narrative_service._handle_achievement_unlocked(mock_event)
            
            # Should not award story content for non-narrative achievements
            mock_award.assert_not_called()
            assert narrative_service._stats["events_received"] == 1
    
    async def test_handle_vip_purchase(self, narrative_service):
        """Test VIP purchase event handling."""
        mock_event = Mock()
        mock_event.data = {"user_id": 1, "purchase_type": "vip_monthly"}
        
        with patch.object(narrative_service, '_unlock_vip_narrative_content') as mock_unlock:
            await narrative_service._handle_vip_purchase(mock_event)
            
            mock_unlock.assert_called_once_with(1)
            assert narrative_service._stats["events_received"] == 1
    
    async def test_handle_admin_content_deleted(self, narrative_service):
        """Test admin content deletion event handling."""
        mock_event = Mock()
        mock_event.data = {
            "admin_id": 100,
            "details": {
                "content_type": "narrative",
                "content_id": "deleted_chapter",
                "reason": "content_violation"
            }
        }
        
        with patch.object(narrative_service, '_handle_narrative_content_deletion') as mock_handle:
            await narrative_service._handle_admin_content_deleted(mock_event)
            
            mock_handle.assert_called_once()
            assert narrative_service._stats["events_received"] == 1

    # Helper Methods Tests
    
    async def test_award_narrative_points(self, narrative_service):
        """Test narrative points awarding."""
        context = {
            "character_impacts": {"diana": 10, "alex": 8},
            "decision_id": "moral_choice",
            "chapter_id": "chapter_01"
        }
        
        await narrative_service._award_narrative_points(1, "decision_made", context)
        
        # Verify points event was published
        published_events = [call.args[0] for call in narrative_service.event_bus.publish.call_args_list]
        points_events = [e for e in published_events if isinstance(e, NarrativePointsEvent)]
        assert len(points_events) > 0
        
        points_event = points_events[0]
        assert points_event.user_id == 1
        assert points_event.action_type == "decision_made"
        # Should get bonus for high character impact
        assert points_event.points_base > POINTS_AWARDS["decision_made"]
    
    async def test_trigger_narrative_achievement(self, narrative_service):
        """Test narrative achievement triggering."""
        mock_result = DecisionResult(
            success=True,
            user_id=1,
            chapter_id="chapter_01",
            decision_id="moral_choice",
            immediate_consequences={},
            character_impacts={},
            unlocked_content=[]
        )
        
        await narrative_service._trigger_narrative_achievement(1, "moral_master", mock_result)
        
        # Verify game event was published
        published_events = [call.args[0] for call in narrative_service.event_bus.publish.call_args_list]
        game_events = [e for e in published_events if hasattr(e, 'action') and 
                      e.action == "achievement_unlocked"]
        assert len(game_events) > 0
        
        game_event = game_events[0]
        assert game_event.user_id == 1
        assert game_event.context["achievement_id"] == "moral_master"
        assert game_event.context["source"] == "narrative"
    
    def test_get_relationship_status_text(self, narrative_service):
        """Test relationship status text generation."""
        # Test friendship levels
        assert narrative_service._get_relationship_status_text(
            {"level": 80, "type": "friendship"}
        ) == "Best Friend"
        
        assert narrative_service._get_relationship_status_text(
            {"level": 60, "type": "friendship"}
        ) == "Close Friend"
        
        assert narrative_service._get_relationship_status_text(
            {"level": 30, "type": "friendship"}
        ) == "Good Friend"
        
        assert narrative_service._get_relationship_status_text(
            {"level": 10, "type": "friendship"}
        ) == "Acquaintance"
        
        # Test romance levels
        assert narrative_service._get_relationship_status_text(
            {"level": 85, "type": "romance"}
        ) == "In Love"
        
        assert narrative_service._get_relationship_status_text(
            {"level": 65, "type": "romance"}
        ) == "Romantic Interest"
        
        assert narrative_service._get_relationship_status_text(
            {"level": 45, "type": "romance"}
        ) == "Attracted"
        
        assert narrative_service._get_relationship_status_text(
            {"level": 25, "type": "romance"}
        ) == "Interested"
        
        # Test rivalry levels
        assert narrative_service._get_relationship_status_text(
            {"level": -85, "type": "rivalry"}
        ) == "Bitter Enemy"
        
        assert narrative_service._get_relationship_status_text(
            {"level": -65, "type": "rivalry"}
        ) == "Strong Rival"
        
        assert narrative_service._get_relationship_status_text(
            {"level": -45, "type": "rivalry"}
        ) == "Competitor"
        
        assert narrative_service._get_relationship_status_text(
            {"level": -25, "type": "rivalry"}
        ) == "Tension"
        
        # Test mentorship levels
        assert narrative_service._get_relationship_status_text(
            {"level": 80, "type": "mentorship"}
        ) == "Trusted Successor"
        
        assert narrative_service._get_relationship_status_text(
            {"level": 60, "type": "mentorship"}
        ) == "Valued Student"
        
        assert narrative_service._get_relationship_status_text(
            {"level": 35, "type": "mentorship"}
        ) == "Learning"
        
        assert narrative_service._get_relationship_status_text(
            {"level": 15, "type": "mentorship"}
        ) == "New Student"
        
        # Test default/neutral
        assert narrative_service._get_relationship_status_text(
            {"level": 0, "type": "unknown"}
        ) == "Neutral"

    # Performance and Statistics Tests
    
    async def test_performance_statistics_tracking(self, narrative_service):
        """Test that performance statistics are properly tracked."""
        initial_stats = narrative_service._stats.copy()
        
        # Simulate various operations
        with patch.object(narrative_service.story_engine, 'load_story_state'):
            with patch.object(narrative_service.story_engine, 'generate_chapter_content'):
                narrative_service.story_engine.load_story_state.return_value = Mock()
                narrative_service.story_engine.generate_chapter_content.return_value = ChapterContent(
                    chapter_id="test", title="Test", content="Test", decisions=[],
                    character_appearances=[]
                )
                
                await narrative_service.get_current_chapter(1)
        
        # Check that statistics were updated
        assert narrative_service._stats["chapters_served"] > initial_stats["chapters_served"]
    
    async def test_concurrent_operations(self, narrative_service):
        """Test service behavior under concurrent operations."""
        # Mock the engines
        with patch.object(narrative_service.story_engine, 'load_story_state'):
            with patch.object(narrative_service.story_engine, 'generate_chapter_content'):
                with patch.object(narrative_service.character_system, 'generate_character_dialogue'):
                    
                    # Setup mocks
                    narrative_service.story_engine.load_story_state.return_value = Mock()
                    narrative_service.story_engine.generate_chapter_content.return_value = ChapterContent(
                        chapter_id="test", title="Test", content="Test", decisions=[],
                        character_appearances=[]
                    )
                    narrative_service.character_system.generate_character_dialogue.return_value = Dialogue(
                        character_id="diana", dialogue_text="Hello", relationship_context={},
                        available_responses=[]
                    )
                    
                    # Run concurrent operations
                    tasks = [
                        narrative_service.get_current_chapter(i)
                        for i in range(1, 6)
                    ] + [
                        narrative_service.get_character_interaction(i, "diana")
                        for i in range(1, 6)
                    ]
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # All operations should succeed
                    assert all(not isinstance(result, Exception) for result in results)
                    assert len(results) == 10

    # Edge Cases and Error Conditions
    
    async def test_service_not_initialized_operations(self, event_bus_mock):
        """Test operations on non-initialized service."""
        service = NarrativeService(event_bus=event_bus_mock)
        
        # Operations should work even if service is not explicitly initialized
        # because they will initialize components as needed
        with patch.object(service.story_engine, 'load_story_state'):
            with patch.object(service.story_engine, 'generate_chapter_content'):
                service.story_engine.load_story_state.return_value = Mock()
                service.story_engine.generate_chapter_content.return_value = ChapterContent(
                    chapter_id="test", title="Test", content="Test", decisions=[],
                    character_appearances=[]
                )
                
                # This should not raise an exception
                result = await service.get_current_chapter(1)
                assert isinstance(result, ChapterContent)
    
    async def test_empty_decision_context(self, narrative_service):
        """Test decision processing with empty context."""
        with patch.object(narrative_service.story_engine, 'load_story_state'):
            with patch.object(narrative_service.decision_engine, 'process_decision'):
                
                narrative_service.story_engine.load_story_state.return_value = Mock()
                narrative_service.decision_engine.process_decision.return_value = DecisionResult(
                    success=True, user_id=1, chapter_id="test", decision_id="test",
                    immediate_consequences={}, character_impacts={}, unlocked_content=[]
                )
                
                # Empty context should be handled gracefully
                result = await narrative_service.process_decision(1, "test_decision", {})
                assert result.success
    
    async def test_large_character_impact_values(self, narrative_service):
        """Test handling of large character impact values."""
        context = {
            "character_impacts": {f"character_{i}": 15 for i in range(20)},  # Many characters
            "decision_id": "major_choice"
        }
        
        # Should handle large number of character impacts
        await narrative_service._award_narrative_points(1, "decision_made", context)
        
        # Verify event was published without errors
        published_events = [call.args[0] for call in narrative_service.event_bus.publish.call_args_list]
        points_events = [e for e in published_events if isinstance(e, NarrativePointsEvent)]
        assert len(points_events) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])