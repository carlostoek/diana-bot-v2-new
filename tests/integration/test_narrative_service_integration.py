"""
Integration Tests for Narrative Service

This module provides integration tests for the narrative service and its components,
testing the full workflow from service initialization through story progression.
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Any, Dict, List

# Test imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.narrative.service import NarrativeService
from services.narrative.engines.story_engine import StoryEngine
from services.narrative.engines.character_system import CharacterSystem
from services.narrative.engines.decision_engine import DecisionEngine
from services.narrative.interfaces import (
    ChapterContent,
    DecisionResult,
    Dialogue,
    UnlockedContent,
    ContentType,
    RelationshipType,
    DecisionType,
)
from services.narrative.models import (
    NarrativeDecisionEvent,
    CharacterInteractionEvent,
    StoryUnlockEvent,
    NarrativePointsEvent,
)
from core.interfaces import IEventBus


class TestNarrativeServiceIntegration:
    """Integration test suite for narrative service components working together."""
    
    @pytest.fixture
    async def event_bus_mock(self):
        """Create a mock event bus for integration testing."""
        mock = AsyncMock(spec=IEventBus)
        mock._is_connected = True
        mock.health_check.return_value = {"status": "healthy"}
        return mock
    
    @pytest.fixture
    async def narrative_service(self, event_bus_mock):
        """Create a fully initialized narrative service for integration testing."""
        service = NarrativeService(
            event_bus=event_bus_mock,
            enable_vip_content=True,
            enable_analytics=True
        )
        await service.initialize()
        return service

    # Full User Story Flow Tests
    
    async def test_complete_user_story_flow(self, narrative_service):
        """Test a complete user story flow from chapter access to decision processing."""
        user_id = 1
        
        # Step 1: User gets their current chapter
        with patch.object(narrative_service.story_engine, 'load_story_state') as mock_story_state:
            with patch.object(narrative_service.story_engine, 'generate_chapter_content') as mock_chapter:
                
                # Mock story state
                story_state = Mock()
                story_state.current_chapter = "prologue"
                story_state.vip_content_available = False
                mock_story_state.return_value = story_state
                
                # Mock chapter content
                chapter_content = ChapterContent(
                    chapter_id="prologue",
                    title="The Beginning",
                    content="Your journey begins here...",
                    decisions=[
                        {
                            "id": "prologue_decision_1",
                            "text": "Choose the path of wisdom",
                            "type": "moral_dilemma"
                        },
                        {
                            "id": "prologue_decision_2", 
                            "text": "Choose the path of adventure",
                            "type": "strategic_choice"
                        }
                    ],
                    character_appearances=["diana"],
                    vip_required=False
                )
                mock_chapter.return_value = chapter_content
                
                current_chapter = await narrative_service.get_current_chapter(user_id)
                
                assert current_chapter.chapter_id == "prologue"
                assert current_chapter.title == "The Beginning"
                assert len(current_chapter.decisions) == 2
                assert current_chapter.character_appearances == ["diana"]
        
        # Step 2: User makes a decision
        with patch.object(narrative_service.story_engine, 'load_story_state') as mock_story_state:
            with patch.object(narrative_service.decision_engine, 'process_decision') as mock_process:
                with patch.object(narrative_service.character_system, 'update_relationship') as mock_update:
                    
                    story_state.current_chapter = "prologue"
                    mock_story_state.return_value = story_state
                    
                    # Mock successful decision processing
                    decision_result = DecisionResult(
                        success=True,
                        user_id=user_id,
                        chapter_id="prologue",
                        decision_id="prologue_decision_1",
                        immediate_consequences={"moral_growth": 10},
                        character_impacts={"diana": 5},
                        unlocked_content=["wisdom_bonus"],
                        next_chapter="chapter_01_discovery",
                        achievement_triggers=["first_decision"]
                    )
                    mock_process.return_value = decision_result
                    
                    result = await narrative_service.process_decision(
                        user_id, "prologue_decision_1"
                    )
                    
                    assert result.success is True
                    assert result.character_impacts["diana"] == 5
                    assert result.unlocked_content == ["wisdom_bonus"]
                    assert result.next_chapter == "chapter_01_discovery"
                    
                    # Verify character relationship was updated
                    mock_update.assert_called_once()
        
        # Step 3: User interacts with character
        with patch.object(narrative_service.character_system, 'generate_character_dialogue') as mock_dialogue:
            
            dialogue = Dialogue(
                character_id="diana",
                dialogue_text="I see wisdom in your choice, young one.",
                relationship_context={"level": 30, "type": "mentorship"},
                available_responses=[
                    {"id": "grateful", "text": "Thank you for your guidance", "impact": 3},
                    {"id": "confident", "text": "I trust my instincts", "impact": 1}
                ],
                mood="approving"
            )
            mock_dialogue.return_value = dialogue
            
            character_interaction = await narrative_service.get_character_interaction(
                user_id, "diana"
            )
            
            assert character_interaction.character_id == "diana"
            assert "wisdom" in character_interaction.dialogue_text
            assert character_interaction.mood == "approving"
            assert len(character_interaction.available_responses) == 2
        
        # Step 4: Check for story unlocks
        with patch.object(narrative_service.story_engine, 'load_story_state') as mock_story_state:
            with patch.object(narrative_service.story_engine, 'unlock_next_content') as mock_unlock:
                
                story_state.completed_chapters = ["prologue"]
                story_state.story_flags = {"wisdom_path": True}
                story_state.character_relationships = {"diana": {"level": 30}}
                story_state.moral_alignment = {"compassionate": 60}
                mock_story_state.return_value = story_state
                
                unlocked_content = [
                    UnlockedContent(
                        content_id="diana_mentor_scene",
                        content_type=ContentType.CHARACTER_INTERACTION,
                        title="Mentorship with Diana",
                        description="Deep conversation about wisdom",
                        unlock_reason="relationship_milestone"
                    )
                ]
                mock_unlock.return_value = unlocked_content
                
                unlocks = await narrative_service.check_story_unlocks(user_id)
                
                assert len(unlocks) == 1
                assert unlocks[0].content_id == "diana_mentor_scene"
        
        # Verify events were published throughout the flow
        published_events = [call.args[0] for call in narrative_service.event_bus.publish.call_args_list]
        
        # Should have decision event
        decision_events = [e for e in published_events if isinstance(e, NarrativeDecisionEvent)]
        assert len(decision_events) > 0
        
        # Should have character interaction event
        interaction_events = [e for e in published_events if isinstance(e, CharacterInteractionEvent)]
        assert len(interaction_events) > 0
        
        # Should have story unlock event
        unlock_events = [e for e in published_events if isinstance(e, StoryUnlockEvent)]
        assert len(unlock_events) > 0
        
        # Should have points award events
        points_events = [e for e in published_events if isinstance(e, NarrativePointsEvent)]
        assert len(points_events) > 0

    # Service Component Integration Tests
    
    async def test_story_engine_character_system_integration(self, narrative_service):
        """Test integration between story engine and character system."""
        user_id = 1
        
        # Story engine provides relationship data that character system uses
        with patch.object(narrative_service.story_engine, 'load_story_state') as mock_story_state:
            with patch.object(narrative_service.character_system, 'load_character_relationships') as mock_relationships:
                with patch.object(narrative_service.character_system, 'generate_character_dialogue') as mock_dialogue:
                    
                    # Story engine provides story state with relationship info
                    story_state = Mock()
                    story_state.character_relationships = {
                        "diana": {"level": 75, "type": "mentorship"},
                        "alex": {"level": 45, "type": "friendship"}
                    }
                    mock_story_state.return_value = story_state
                    
                    # Character system loads relationships
                    mock_relationships.return_value = story_state.character_relationships
                    
                    # Character system generates dialogue based on relationship level
                    dialogue = Dialogue(
                        character_id="diana",
                        dialogue_text="Your progress has been remarkable, my student.",
                        relationship_context={"level": 75, "type": "mentorship"},
                        available_responses=[
                            {"id": "humble", "text": "I owe it all to your guidance", "impact": 5}
                        ],
                        mood="proud"
                    )
                    mock_dialogue.return_value = dialogue
                    
                    # Get chapter content (uses story state)
                    await narrative_service.get_current_chapter(user_id)
                    
                    # Generate character dialogue (uses relationships from story state)
                    character_dialogue = await narrative_service.get_character_interaction(user_id, "diana")
                    
                    # Verify high relationship level influenced dialogue
                    assert character_dialogue.relationship_context["level"] == 75
                    assert character_dialogue.mood == "proud"
                    assert "remarkable" in character_dialogue.dialogue_text
    
    async def test_decision_engine_story_engine_integration(self, narrative_service):
        """Test integration between decision engine and story engine."""
        user_id = 1
        
        with patch.object(narrative_service.story_engine, 'load_story_state') as mock_story_state:
            with patch.object(narrative_service.decision_engine, 'process_decision') as mock_process_decision:
                with patch.object(narrative_service.story_engine, 'validate_story_consistency') as mock_validate:
                    
                    # Story engine provides current state
                    story_state = Mock()
                    story_state.current_chapter = "chapter_02"
                    story_state.story_flags = {"moral_path": True}
                    story_state.moral_alignment = {"compassionate": 70}
                    mock_story_state.return_value = story_state
                    
                    # Decision engine processes decision with story context
                    decision_result = DecisionResult(
                        success=True,
                        user_id=user_id,
                        chapter_id="chapter_02",
                        decision_id="moral_choice_advanced",
                        immediate_consequences={"story_flags": {"wisdom_mastery": True}},
                        character_impacts={"diana": 8},
                        unlocked_content=["advanced_moral_content"],
                        next_chapter="chapter_03_enlightenment"
                    )
                    mock_process_decision.return_value = decision_result
                    
                    # Story engine validates consistency of resulting state
                    mock_validate.return_value = (True, None)
                    
                    result = await narrative_service.process_decision(
                        user_id, "moral_choice_advanced"
                    )
                    
                    # Verify decision was processed with story context
                    assert result.success is True
                    assert result.next_chapter == "chapter_03_enlightenment"
                    
                    # Verify story engine was consulted for current state
                    mock_story_state.assert_called_with(user_id)
    
    async def test_character_system_decision_engine_integration(self, narrative_service):
        """Test integration between character system and decision engine."""
        user_id = 1
        
        with patch.object(narrative_service.story_engine, 'load_story_state') as mock_story_state:
            with patch.object(narrative_service.decision_engine, 'process_decision') as mock_process_decision:
                with patch.object(narrative_service.character_system, 'update_relationship') as mock_update_relationship:
                    
                    story_state = Mock()
                    story_state.current_chapter = "chapter_01"
                    mock_story_state.return_value = story_state
                    
                    # Decision engine calculates character impacts
                    decision_result = DecisionResult(
                        success=True,
                        user_id=user_id,
                        chapter_id="chapter_01",
                        decision_id="relationship_decision",
                        immediate_consequences={},
                        character_impacts={"alex": 7, "sam": -3},  # Strong positive/negative impacts
                        unlocked_content=[]
                    )
                    mock_process_decision.return_value = decision_result
                    
                    # Character system receives relationship updates
                    mock_update_relationship.return_value = {"level": 52, "type": "friendship"}
                    
                    result = await narrative_service.process_decision(
                        user_id, "relationship_decision"
                    )
                    
                    # Verify character relationships were updated for each impacted character
                    assert mock_update_relationship.call_count == 2  # Called for alex and sam
                    
                    # Verify the updates included the calculated impacts
                    calls = mock_update_relationship.call_args_list
                    alex_call = next(call for call in calls if call[0][1] == "alex")
                    sam_call = next(call for call in calls if call[0][1] == "sam")
                    
                    assert alex_call[0][2]["level_change"] == 7
                    assert sam_call[0][2]["level_change"] == -3

    # Event Bus Integration Tests
    
    async def test_event_bus_cross_service_communication(self, narrative_service):
        """Test event bus communication across narrative service components."""
        user_id = 1
        
        # Test that events are properly published and would be consumed
        with patch.object(narrative_service.story_engine, 'load_story_state') as mock_story_state:
            with patch.object(narrative_service.decision_engine, 'process_decision') as mock_process:
                
                story_state = Mock()
                story_state.current_chapter = "chapter_01"
                mock_story_state.return_value = story_state
                
                decision_result = DecisionResult(
                    success=True,
                    user_id=user_id,
                    chapter_id="chapter_01",
                    decision_id="event_decision",
                    immediate_consequences={"achievement_earned": True},
                    character_impacts={"diana": 6},
                    unlocked_content=["bonus_content"],
                    achievement_triggers=["storyteller"]
                )
                mock_process.return_value = decision_result
                
                await narrative_service.process_decision(user_id, "event_decision")
                
                # Verify multiple types of events were published
                published_events = [call.args[0] for call in narrative_service.event_bus.publish.call_args_list]
                
                # Should have decision event
                decision_events = [e for e in published_events if isinstance(e, NarrativeDecisionEvent)]
                assert len(decision_events) > 0
                decision_event = decision_events[0]
                assert decision_event.user_id == user_id
                assert decision_event.decision_id == "event_decision"
                
                # Should have points event
                points_events = [e for e in published_events if isinstance(e, NarrativePointsEvent)]
                assert len(points_events) > 0
                
                # Should have unlock event
                unlock_events = [e for e in published_events if isinstance(e, StoryUnlockEvent)]
                assert len(unlock_events) > 0
                unlock_event = unlock_events[0]
                assert unlock_event.user_id == user_id
                assert len(unlock_event.unlocked_content) == 1
    
    async def test_event_handler_integration(self, narrative_service):
        """Test narrative service event handlers integration."""
        # Test user registration handler
        user_event = Mock()
        user_event.data = {"user_id": 1, "username": "test_user"}
        
        with patch.object(narrative_service, '_initialize_user_narrative_data') as mock_init:
            await narrative_service._handle_user_registered(user_event)
            mock_init.assert_called_once_with(1)
        
        # Test VIP purchase handler
        vip_event = Mock()
        vip_event.data = {"user_id": 1, "purchase_type": "vip_monthly"}
        
        with patch.object(narrative_service, '_unlock_vip_narrative_content') as mock_unlock_vip:
            await narrative_service._handle_vip_purchase(vip_event)
            mock_unlock_vip.assert_called_once_with(1)
        
        # Test achievement unlock handler
        achievement_event = Mock()
        achievement_event.data = {
            "user_id": 1,
            "achievement_id": "moral_master",
            "context": {"source": "narrative", "moral_alignment": "compassionate"}
        }
        
        with patch.object(narrative_service, '_award_achievement_story_content') as mock_award:
            await narrative_service._handle_achievement_unlocked(achievement_event)
            mock_award.assert_called_once_with(1, {"source": "narrative", "moral_alignment": "compassionate"})

    # Error Handling and Recovery Tests
    
    async def test_partial_component_failure_recovery(self, narrative_service):
        """Test service behavior when individual components fail."""
        user_id = 1
        
        # Test story engine failure with graceful degradation
        with patch.object(narrative_service.story_engine, 'load_story_state') as mock_story_state:
            mock_story_state.side_effect = Exception("Story engine failure")
            
            with pytest.raises(Exception):
                await narrative_service.get_current_chapter(user_id)
        
        # Test character system failure with fallback
        with patch.object(narrative_service.character_system, 'generate_character_dialogue') as mock_dialogue:
            mock_dialogue.side_effect = Exception("Character system failure")
            
            with pytest.raises(Exception):
                await narrative_service.get_character_interaction(user_id, "diana")
        
        # Test decision engine failure with error result
        with patch.object(narrative_service.story_engine, 'load_story_state') as mock_story_state:
            with patch.object(narrative_service.decision_engine, 'process_decision') as mock_process:
                
                story_state = Mock()
                story_state.current_chapter = "chapter_01"
                mock_story_state.return_value = story_state
                
                mock_process.side_effect = Exception("Decision engine failure")
                
                result = await narrative_service.process_decision(user_id, "test_decision")
                
                # Should return failed result instead of raising exception
                assert result.success is False
                assert "Decision processing failed" in result.error_message
    
    async def test_event_bus_failure_handling(self, narrative_service):
        """Test service behavior when event bus operations fail."""
        user_id = 1
        
        # Make event bus publishing fail
        narrative_service.event_bus.publish.side_effect = Exception("Event bus error")
        
        with patch.object(narrative_service.story_engine, 'load_story_state') as mock_story_state:
            with patch.object(narrative_service.decision_engine, 'process_decision') as mock_process:
                
                story_state = Mock()
                story_state.current_chapter = "chapter_01"
                mock_story_state.return_value = story_state
                
                decision_result = DecisionResult(
                    success=True,
                    user_id=user_id,
                    chapter_id="chapter_01",
                    decision_id="test_decision",
                    immediate_consequences={},
                    character_impacts={},
                    unlocked_content=[]
                )
                mock_process.return_value = decision_result
                
                # Should still return successful result even if event publishing fails
                result = await narrative_service.process_decision(user_id, "test_decision")
                assert result.success is True

    # Performance Integration Tests
    
    async def test_high_load_decision_processing(self, narrative_service):
        """Test narrative service performance under high decision processing load."""
        user_count = 10
        decisions_per_user = 5
        
        with patch.object(narrative_service.story_engine, 'load_story_state') as mock_story_state:
            with patch.object(narrative_service.decision_engine, 'process_decision') as mock_process:
                with patch.object(narrative_service.character_system, 'update_relationship') as mock_update:
                    
                    # Setup mocks
                    story_state = Mock()
                    story_state.current_chapter = "chapter_01"
                    mock_story_state.return_value = story_state
                    
                    decision_result = DecisionResult(
                        success=True,
                        user_id=1,  # Will be overridden
                        chapter_id="chapter_01",
                        decision_id="load_test_decision",
                        immediate_consequences={},
                        character_impacts={"diana": 2},
                        unlocked_content=[]
                    )
                    mock_process.return_value = decision_result
                    mock_update.return_value = {"level": 25}
                    
                    # Create load test tasks
                    tasks = []
                    for user_id in range(1, user_count + 1):
                        for decision_num in range(decisions_per_user):
                            tasks.append(
                                narrative_service.process_decision(
                                    user_id, f"decision_{decision_num}"
                                )
                            )
                    
                    # Process all decisions concurrently
                    start_time = asyncio.get_event_loop().time()
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    end_time = asyncio.get_event_loop().time()
                    
                    # Verify all completed successfully
                    successful_results = [r for r in results if isinstance(r, DecisionResult) and r.success]
                    assert len(successful_results) == user_count * decisions_per_user
                    
                    # Verify reasonable performance
                    total_time = end_time - start_time
                    decisions_per_second = len(tasks) / total_time
                    assert decisions_per_second > 10  # At least 10 decisions per second
    
    async def test_concurrent_user_story_progression(self, narrative_service):
        """Test concurrent story progression for multiple users."""
        user_ids = [1, 2, 3, 4, 5]
        
        with patch.object(narrative_service.story_engine, 'load_story_state') as mock_story_state:
            with patch.object(narrative_service.story_engine, 'generate_chapter_content') as mock_chapter:
                with patch.object(narrative_service.character_system, 'generate_character_dialogue') as mock_dialogue:
                    
                    # Setup mocks
                    def mock_story_state_func(user_id):
                        state = Mock()
                        state.current_chapter = f"chapter_{user_id}"
                        state.vip_content_available = False
                        return state
                    
                    mock_story_state.side_effect = mock_story_state_func
                    
                    def mock_chapter_func(user_id, chapter_id, personalize=True):
                        return ChapterContent(
                            chapter_id=chapter_id,
                            title=f"Chapter for User {user_id}",
                            content=f"Content for user {user_id}",
                            decisions=[],
                            character_appearances=[]
                        )
                    
                    mock_chapter.side_effect = mock_chapter_func
                    
                    dialogue = Dialogue(
                        character_id="diana",
                        dialogue_text="Hello, traveler.",
                        relationship_context={},
                        available_responses=[]
                    )
                    mock_dialogue.return_value = dialogue
                    
                    # Create concurrent tasks
                    chapter_tasks = [narrative_service.get_current_chapter(uid) for uid in user_ids]
                    interaction_tasks = [
                        narrative_service.get_character_interaction(uid, "diana") for uid in user_ids
                    ]
                    
                    # Execute all tasks concurrently
                    chapter_results = await asyncio.gather(*chapter_tasks, return_exceptions=True)
                    interaction_results = await asyncio.gather(*interaction_tasks, return_exceptions=True)
                    
                    # Verify all succeeded
                    assert all(isinstance(r, ChapterContent) for r in chapter_results)
                    assert all(isinstance(r, Dialogue) for r in interaction_results)
                    
                    # Verify each user got their specific content
                    for i, result in enumerate(chapter_results):
                        expected_user_id = user_ids[i]
                        assert f"User {expected_user_id}" in result.title

    # Data Consistency Integration Tests
    
    async def test_story_state_consistency_across_components(self, narrative_service):
        """Test that story state remains consistent across all service components."""
        user_id = 1
        
        # Setup consistent story state
        consistent_story_state = Mock()
        consistent_story_state.current_chapter = "chapter_02"
        consistent_story_state.completed_chapters = ["prologue", "chapter_01"]
        consistent_story_state.story_flags = {"wisdom_path": True, "diana_trust": 75}
        consistent_story_state.character_relationships = {
            "diana": {"level": 75, "type": "mentorship"},
            "alex": {"level": 45, "type": "friendship"}
        }
        consistent_story_state.moral_alignment = {"compassionate": 80}
        consistent_story_state.vip_content_available = True
        
        # All components should receive the same story state
        with patch.object(narrative_service.story_engine, 'load_story_state') as mock_story_state:
            with patch.object(narrative_service.story_engine, 'generate_chapter_content') as mock_chapter:
                with patch.object(narrative_service.character_system, 'load_character_relationships') as mock_relationships:
                    with patch.object(narrative_service.decision_engine, 'validate_decision_consistency') as mock_validate:
                        
                        mock_story_state.return_value = consistent_story_state
                        mock_relationships.return_value = consistent_story_state.character_relationships
                        mock_validate.return_value = (True, None)
                        
                        chapter_content = ChapterContent(
                            chapter_id="chapter_02",
                            title="Advanced Chapter",
                            content="Advanced content",
                            decisions=[],
                            character_appearances=[]
                        )
                        mock_chapter.return_value = chapter_content
                        
                        # Get current chapter (uses story state)
                        chapter = await narrative_service.get_current_chapter(user_id)
                        
                        # Verify consistent data was used
                        mock_story_state.assert_called_with(user_id)
                        assert chapter.chapter_id == "chapter_02"
                        
                        # Load relationships (should use same story state data)
                        relationships = await narrative_service.character_system.load_character_relationships(user_id)
                        
                        # Verify same relationship data
                        assert relationships["diana"]["level"] == 75
                        assert relationships["alex"]["level"] == 45
    
    async def test_transaction_like_behavior_in_decision_processing(self, narrative_service):
        """Test that decision processing maintains transaction-like consistency."""
        user_id = 1
        
        with patch.object(narrative_service.story_engine, 'load_story_state') as mock_story_state:
            with patch.object(narrative_service.decision_engine, 'process_decision') as mock_process:
                with patch.object(narrative_service.character_system, 'update_relationship') as mock_update:
                    
                    story_state = Mock()
                    story_state.current_chapter = "chapter_01"
                    mock_story_state.return_value = story_state
                    
                    # First decision succeeds
                    success_result = DecisionResult(
                        success=True,
                        user_id=user_id,
                        chapter_id="chapter_01",
                        decision_id="success_decision",
                        immediate_consequences={"progress": 1},
                        character_impacts={"diana": 5},
                        unlocked_content=[]
                    )
                    
                    # Second decision fails  
                    failure_result = DecisionResult(
                        success=False,
                        user_id=user_id,
                        chapter_id="chapter_01",
                        decision_id="failure_decision",
                        immediate_consequences={},
                        character_impacts={},
                        unlocked_content=[],
                        error_message="Decision failed"
                    )
                    
                    mock_process.side_effect = [success_result, failure_result]
                    mock_update.return_value = {"level": 30}
                    
                    # Process successful decision
                    result1 = await narrative_service.process_decision(user_id, "success_decision")
                    assert result1.success is True
                    
                    # Process failed decision
                    result2 = await narrative_service.process_decision(user_id, "failure_decision")
                    assert result2.success is False
                    
                    # Verify only successful decision updated relationships
                    assert mock_update.call_count == 1  # Only called for successful decision

    # Service Lifecycle Integration Tests
    
    async def test_service_initialization_component_coordination(self, event_bus_mock):
        """Test that service initialization properly coordinates all components."""
        service = NarrativeService(event_bus=event_bus_mock)
        
        # Before initialization
        assert not service._initialized
        
        # Initialize service
        await service.initialize()
        
        # After initialization
        assert service._initialized
        assert service.story_engine is not None
        assert service.character_system is not None
        assert service.decision_engine is not None
        
        # Verify event subscriptions were set up
        event_bus_mock.subscribe.assert_called()
        
        # Verify service startup event was published
        service_events = [
            call.args[0] for call in event_bus_mock.publish.call_args_list
            if hasattr(call.args[0], 'component') and call.args[0].component == "narrative_service"
        ]
        assert len(service_events) > 0
    
    async def test_service_cleanup_component_coordination(self, narrative_service):
        """Test that service cleanup properly coordinates all components."""
        # Service should be initialized
        assert narrative_service._initialized
        
        # Cleanup service
        await narrative_service.cleanup()
        
        # After cleanup
        assert not narrative_service._initialized
        
        # Verify cleanup events were published
        cleanup_events = [
            call.args[0] for call in narrative_service.event_bus.publish.call_args_list
            if hasattr(call.args[0], 'event_type') and call.args[0].event_type == "service_stopped"
        ]
        assert len(cleanup_events) > 0
    
    async def test_service_health_check_integration(self, narrative_service):
        """Test comprehensive health check across all components."""
        with patch.object(narrative_service.story_engine, 'load_story_state') as mock_story:
            with patch.object(narrative_service.character_system, 'load_character_relationships') as mock_character:
                
                # Mock healthy components
                mock_story.return_value = Mock()
                mock_character.return_value = {}
                
                health_status = await narrative_service.health_check()
                
                assert health_status["status"] == "healthy"
                assert health_status["service_initialized"] is True
                assert health_status["event_bus_connected"] is True
                assert health_status["story_engine_status"] == "healthy"
                assert health_status["character_system_status"] == "healthy"
                assert health_status["decision_engine_status"] == "healthy"
                assert "performance_stats" in health_status
    
    async def test_service_degraded_health_integration(self, narrative_service):
        """Test health check when some components are degraded."""
        with patch.object(narrative_service.story_engine, 'load_story_state') as mock_story:
            with patch.object(narrative_service.character_system, 'load_character_relationships') as mock_character:
                
                # Story engine fails
                mock_story.side_effect = Exception("Story engine error")
                # Character system works
                mock_character.return_value = {}
                
                health_status = await narrative_service.health_check()
                
                assert health_status["status"] == "degraded"
                assert health_status["story_engine_status"] == "unhealthy"
                assert health_status["character_system_status"] == "healthy"

    # Advanced Story Consistency Tests
    
    async def test_cross_component_story_consistency_validation(self, narrative_service):
        """Test story consistency validation across all components."""
        user_id = 1
        
        with patch.object(narrative_service.story_engine, 'validate_story_consistency') as mock_validate:
            with patch.object(narrative_service.character_system, 'validate_character_consistency') as mock_char_validate:
                with patch.object(narrative_service.decision_engine, 'validate_decision_consistency') as mock_decision_validate:
                    
                    # All components report consistency
                    mock_validate.return_value = (True, None)
                    mock_char_validate.return_value = (True, None)
                    mock_decision_validate.return_value = (True, None)
                    
                    # Test story state consistency
                    proposed_state = {
                        "current_chapter": "chapter_02",
                        "moral_alignment": {"compassionate": 75}
                    }
                    
                    is_valid, error = await narrative_service.story_engine.validate_story_consistency(
                        user_id, proposed_state
                    )
                    
                    assert is_valid is True
                    assert error is None
                    
                    # Test character consistency
                    is_char_valid, char_error = await narrative_service.character_system.validate_character_consistency(
                        "diana", "I sense great wisdom in your path, young seeker."
                    )
                    
                    assert is_char_valid is True
                    assert char_error is None
                    
                    # Test decision consistency
                    decision_data = {"decision": Mock()}
                    is_decision_valid, decision_error = await narrative_service.decision_engine.validate_decision_consistency(
                        user_id, decision_data
                    )
                    
                    assert is_decision_valid is True
                    assert decision_error is None


class TestNarrativeServiceStoryConsistency:
    """Specialized integration tests for story consistency validation."""
    
    @pytest.fixture
    async def event_bus_mock(self):
        """Create a mock event bus."""
        mock = AsyncMock(spec=IEventBus)
        mock._is_connected = True
        mock.health_check.return_value = {"status": "healthy"}
        return mock
    
    @pytest.fixture
    async def narrative_service(self, event_bus_mock):
        """Create narrative service for consistency testing."""
        service = NarrativeService(event_bus=event_bus_mock)
        await service.initialize()
        return service
    
    async def test_story_progression_consistency_validation(self, narrative_service):
        """Test story progression maintains consistency."""
        user_id = 1
        
        # Start from a known state
        initial_state = Mock()
        initial_state.current_chapter = "prologue"
        initial_state.completed_chapters = []
        initial_state.story_flags = {}
        initial_state.character_relationships = {}
        initial_state.moral_alignment = {}
        
        with patch.object(narrative_service.story_engine, 'load_story_state') as mock_state:
            with patch.object(narrative_service.decision_engine, 'process_decision') as mock_process:
                with patch.object(narrative_service.story_engine, 'validate_story_consistency') as mock_validate:
                    
                    mock_state.return_value = initial_state
                    
                    # First decision advances story
                    first_result = DecisionResult(
                        success=True,
                        user_id=user_id,
                        chapter_id="prologue",
                        decision_id="first_decision",
                        immediate_consequences={"chapter_complete": True},
                        character_impacts={"diana": 5},
                        unlocked_content=[],
                        next_chapter="chapter_01"
                    )
                    mock_process.return_value = first_result
                    
                    # Consistency validation should pass
                    mock_validate.return_value = (True, None)
                    
                    result = await narrative_service.process_decision(user_id, "first_decision")
                    
                    assert result.success is True
                    assert result.next_chapter == "chapter_01"
                    
                    # Verify consistency was validated
                    mock_validate.assert_called()
    
    async def test_character_relationship_consistency_validation(self, narrative_service):
        """Test character relationship changes maintain consistency."""
        user_id = 1
        
        with patch.object(narrative_service.character_system, 'load_character_relationships') as mock_load:
            with patch.object(narrative_service.character_system, 'update_relationship') as mock_update:
                with patch.object(narrative_service.character_system, 'validate_character_consistency') as mock_validate:
                    
                    # Current relationship state
                    current_relationships = {
                        "diana": {"level": 30, "type": "friendship", "interaction_count": 5}
                    }
                    mock_load.return_value = current_relationships
                    
                    # Valid relationship change
                    relationship_change = {
                        "level_change": 8,
                        "interaction_type": "supportive",
                        "context": {"emotional_significance": "high"}
                    }
                    
                    updated_relationship = {"level": 38, "type": "friendship", "interaction_count": 6}
                    mock_update.return_value = updated_relationship
                    
                    # Character dialogue should be consistent with new relationship
                    mock_validate.return_value = (True, None)
                    
                    result = await narrative_service.character_system.update_relationship(
                        user_id, "diana", relationship_change
                    )
                    
                    assert result["level"] == 38
                    assert result["type"] == "friendship"
    
    async def test_moral_alignment_consistency_validation(self, narrative_service):
        """Test moral alignment changes maintain consistency."""
        user_id = 1
        
        with patch.object(narrative_service.story_engine, 'load_story_state') as mock_state:
            with patch.object(narrative_service.decision_engine, 'process_decision') as mock_process:
                
                # Current moral state
                current_state = Mock()
                current_state.moral_alignment = {"compassionate": 50, "pragmatic": 30}
                current_state.current_chapter = "chapter_01"
                mock_state.return_value = current_state
                
                # Decision that affects moral alignment
                decision_result = DecisionResult(
                    success=True,
                    user_id=user_id,
                    chapter_id="chapter_01",
                    decision_id="moral_decision",
                    immediate_consequences={
                        "moral_impact": {"compassionate": 15}  # Increases compassionate
                    },
                    character_impacts={},
                    unlocked_content=[]
                )
                mock_process.return_value = decision_result
                
                result = await narrative_service.process_decision(user_id, "moral_decision")
                
                # Result should maintain moral consistency
                assert result.success is True
                assert "compassionate" in result.immediate_consequences.get("moral_impact", {})
    
    async def test_story_flag_dependency_consistency(self, narrative_service):
        """Test story flag dependencies maintain consistency."""
        user_id = 1
        
        with patch.object(narrative_service.story_engine, 'load_story_state') as mock_state:
            with patch.object(narrative_service.decision_engine, 'update_narrative_flags') as mock_flags:
                
                # Current story state with dependencies
                current_state = Mock()
                current_state.story_flags = {
                    "diana_met": True,
                    "tutorial_complete": True,
                    "wisdom_path": False
                }
                current_state.character_relationships = {"diana": {"level": 40}}
                mock_state.return_value = current_state
                
                # Flag update that depends on existing flags
                updated_flags = {
                    "diana_met": True,
                    "tutorial_complete": True,
                    "wisdom_path": True,  # Now unlocked due to Diana relationship
                    "diana_mentor": True  # Dependent on wisdom_path and diana relationship
                }
                mock_flags.return_value = updated_flags
                
                decision_data = {
                    "decision": Mock(),
                    "consequences": {"unlock_wisdom_path": True}
                }
                
                result = await narrative_service.decision_engine.update_narrative_flags(
                    user_id, decision_data
                )
                
                # Verify flag dependencies are maintained
                assert result["wisdom_path"] is True
                assert result["diana_mentor"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])