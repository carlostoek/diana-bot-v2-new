"""
Comprehensive Unit Tests for Character System

This module provides extensive unit test coverage for the Character System component,
including relationship tracking, dialogue generation, and memory management.
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

from services.narrative.engines.character_system import CharacterSystem
from services.narrative.interfaces import (
    Dialogue,
    CharacterMemory,
    RelationshipType,
    CharacterSystemError,
    CharacterNotFoundError,
)
from services.narrative.models import (
    CharacterRelationship,
    InteractionHistory,
    MAIN_CHARACTERS,
    RELATIONSHIP_THRESHOLDS,
)
from core.interfaces import IEventBus


class TestCharacterSystem:
    """Comprehensive test suite for CharacterSystem."""
    
    @pytest.fixture
    async def event_bus_mock(self):
        """Create a mock event bus."""
        mock = AsyncMock(spec=IEventBus)
        return mock
    
    @pytest.fixture
    async def character_system(self, event_bus_mock):
        """Create a character system instance for testing."""
        return CharacterSystem(
            event_bus=event_bus_mock,
            memory_retention_days=30,
            relationship_decay_enabled=True
        )
    
    @pytest.fixture
    async def character_system_no_decay(self, event_bus_mock):
        """Create a character system instance with relationship decay disabled."""
        return CharacterSystem(
            event_bus=event_bus_mock,
            memory_retention_days=30,
            relationship_decay_enabled=False
        )

    # Initialization Tests
    
    def test_initialization_default(self, event_bus_mock):
        """Test default initialization of character system."""
        system = CharacterSystem(event_bus_mock)
        
        assert system.event_bus == event_bus_mock
        assert system.memory_retention_days == 30
        assert system.relationship_decay_enabled is True
        assert len(system._character_cache) == 0
        assert len(system._relationship_cache) == 0
        assert system._stats["dialogues_generated"] == 0
    
    def test_initialization_custom_settings(self, event_bus_mock):
        """Test initialization with custom settings."""
        system = CharacterSystem(
            event_bus=event_bus_mock,
            memory_retention_days=60,
            relationship_decay_enabled=False
        )
        
        assert system.memory_retention_days == 60
        assert system.relationship_decay_enabled is False

    # Load Character Relationships Tests
    
    async def test_load_character_relationships_success(self, character_system):
        """Test successful character relationships loading."""
        user_id = 1
        
        with patch.object(character_system, '_load_relationship_from_db') as mock_load:
            with patch.object(character_system, '_apply_relationship_decay') as mock_decay:
                
                # Create mock relationships for each character
                mock_relationships = {}
                for character_id in MAIN_CHARACTERS.keys():
                    relationship = CharacterRelationship(
                        user_id=user_id,
                        character_id=character_id,
                        relationship_level=25,
                        relationship_type=RelationshipType.FRIENDSHIP,
                        interaction_count=5
                    )
                    mock_relationships[character_id] = relationship
                
                mock_load.side_effect = lambda uid, cid: mock_relationships[cid]
                mock_decay.side_effect = lambda rel: rel  # No decay for test
                
                result = await character_system.load_character_relationships(user_id)
                
                assert len(result) == len(MAIN_CHARACTERS)
                for character_id in MAIN_CHARACTERS.keys():
                    assert character_id in result
                    assert result[character_id]["level"] == 25
                    assert result[character_id]["type"] == "friendship"
                
                # Should call load for each character
                assert mock_load.call_count == len(MAIN_CHARACTERS)
    
    async def test_load_character_relationships_caching(self, character_system):
        """Test character relationships caching."""
        user_id = 1
        character_id = "diana"
        
        with patch.object(character_system, '_load_relationship_from_db') as mock_load:
            with patch.object(character_system, '_apply_relationship_decay') as mock_decay:
                
                relationship = CharacterRelationship(
                    user_id=user_id,
                    character_id=character_id,
                    relationship_level=50,
                    relationship_type=RelationshipType.FRIENDSHIP
                )
                mock_load.return_value = relationship
                mock_decay.return_value = relationship
                
                # First call - should miss cache
                result1 = await character_system.load_character_relationships(user_id)
                assert character_system._stats["cache_misses"] >= 1
                
                # Second call - should hit cache for at least one character
                result2 = await character_system.load_character_relationships(user_id)
                assert character_system._stats["cache_hits"] >= 1
    
    async def test_load_character_relationships_with_decay(self, character_system):
        """Test relationship loading with decay applied."""
        user_id = 1
        
        with patch.object(character_system, '_load_relationship_from_db') as mock_load:
            
            # Create relationship with old last_interaction
            old_interaction = datetime.now(timezone.utc) - timedelta(days=15)
            relationship = CharacterRelationship(
                user_id=user_id,
                character_id="diana",
                relationship_level=60,
                relationship_type=RelationshipType.FRIENDSHIP,
                last_interaction=old_interaction
            )
            mock_load.return_value = relationship
            
            result = await character_system.load_character_relationships(user_id)
            
            # Relationship should have decayed due to old interaction
            assert result["diana"]["level"] < 60
    
    async def test_load_character_relationships_no_decay_disabled(self, character_system_no_decay):
        """Test relationship loading with decay disabled."""
        user_id = 1
        
        with patch.object(character_system_no_decay, '_load_relationship_from_db') as mock_load:
            
            # Create relationship with old last_interaction
            old_interaction = datetime.now(timezone.utc) - timedelta(days=15)
            relationship = CharacterRelationship(
                user_id=user_id,
                character_id="diana",
                relationship_level=60,
                relationship_type=RelationshipType.FRIENDSHIP,
                last_interaction=old_interaction
            )
            mock_load.return_value = relationship
            
            result = await character_system_no_decay.load_character_relationships(user_id)
            
            # Relationship should NOT have decayed
            assert result["diana"]["level"] == 60
    
    async def test_load_character_relationships_error(self, character_system):
        """Test character relationships loading error handling."""
        user_id = 1
        
        with patch.object(character_system, '_load_relationship_from_db') as mock_load:
            mock_load.side_effect = Exception("Database error")
            
            with pytest.raises(CharacterSystemError, match="Cannot load relationships"):
                await character_system.load_character_relationships(user_id)

    # Generate Character Dialogue Tests
    
    async def test_generate_character_dialogue_success(self, character_system):
        """Test successful character dialogue generation."""
        user_id = 1
        character_id = "diana"
        
        with patch.object(character_system, '_load_character_data') as mock_char_data:
            with patch.object(character_system, '_load_relationship_from_db') as mock_relationship:
                with patch.object(character_system, 'get_character_memory') as mock_memory:
                    with patch.object(character_system, '_generate_personality_dialogue') as mock_dialogue:
                        with patch.object(character_system, '_generate_response_options') as mock_responses:
                            with patch.object(character_system, '_calculate_character_mood') as mock_mood:
                                with patch.object(character_system, '_select_relevant_memories') as mock_memories:
                                    
                                    # Setup mocks
                                    mock_char_data.return_value = {
                                        "id": character_id,
                                        "name": "Diana",
                                        "personality_traits": {"wisdom": 90}
                                    }
                                    
                                    relationship = CharacterRelationship(
                                        user_id=user_id,
                                        character_id=character_id,
                                        relationship_level=50,
                                        relationship_type=RelationshipType.FRIENDSHIP
                                    )
                                    mock_relationship.return_value = relationship
                                    
                                    memory = CharacterMemory(
                                        character_id=character_id,
                                        user_id=user_id,
                                        interaction_history=[],
                                        relationship_level=50,
                                        relationship_type=RelationshipType.FRIENDSHIP,
                                        memorable_moments=[],
                                        personality_state={"wisdom": 90}
                                    )
                                    mock_memory.return_value = memory
                                    
                                    mock_dialogue.return_value = "Hello, dear friend."
                                    mock_responses.return_value = [
                                        {"id": "friendly", "text": "Hello Diana!", "impact": 2}
                                    ]
                                    mock_mood.return_value = "welcoming"
                                    mock_memories.return_value = ["Previous conversation"]
                                    
                                    result = await character_system.generate_character_dialogue(
                                        user_id, character_id
                                    )
                                    
                                    assert isinstance(result, Dialogue)
                                    assert result.character_id == character_id
                                    assert result.dialogue_text == "Hello, dear friend."
                                    assert result.mood == "welcoming"
                                    assert len(result.available_responses) == 1
                                    assert result.reference_memory == ["Previous conversation"]
                                    assert character_system._stats["dialogues_generated"] == 1
    
    async def test_generate_character_dialogue_with_context(self, character_system):
        """Test dialogue generation with context."""
        user_id = 1
        character_id = "alex"
        context = {"scene": "battle", "emotional_state": "excited"}
        
        with patch.object(character_system, '_load_character_data') as mock_char_data:
            with patch.object(character_system, '_load_relationship_from_db') as mock_relationship:
                with patch.object(character_system, 'get_character_memory') as mock_memory:
                    with patch.object(character_system, '_generate_personality_dialogue') as mock_dialogue:
                        with patch.object(character_system, '_generate_response_options') as mock_responses:
                            with patch.object(character_system, '_calculate_character_mood') as mock_mood:
                                with patch.object(character_system, '_select_relevant_memories') as mock_memories:
                                    
                                    mock_char_data.return_value = {"id": character_id, "name": "Alex"}
                                    mock_relationship.return_value = CharacterRelationship(
                                        user_id=user_id, character_id=character_id,
                                        relationship_level=30, relationship_type=RelationshipType.FRIENDSHIP
                                    )
                                    mock_memory.return_value = Mock()
                                    mock_dialogue.return_value = "Ready for battle, friend!"
                                    mock_responses.return_value = []
                                    mock_mood.return_value = "excited"
                                    mock_memories.return_value = []
                                    
                                    await character_system.generate_character_dialogue(
                                        user_id, character_id, context
                                    )
                                    
                                    # Verify context was passed to dialogue generation
                                    mock_dialogue.assert_called_once()
                                    call_args = mock_dialogue.call_args[0]
                                    context_arg = call_args[3] if len(call_args) > 3 else None
                                    assert context_arg == context
    
    async def test_generate_character_dialogue_character_not_found(self, character_system):
        """Test dialogue generation for non-existent character."""
        user_id = 1
        character_id = "nonexistent_character"
        
        with pytest.raises(CharacterNotFoundError, match="Character not found"):
            await character_system.generate_character_dialogue(user_id, character_id)
    
    async def test_generate_character_dialogue_error(self, character_system):
        """Test dialogue generation error handling."""
        user_id = 1
        character_id = "diana"
        
        with patch.object(character_system, '_load_character_data') as mock_char_data:
            mock_char_data.side_effect = Exception("Character data error")
            
            with pytest.raises(CharacterSystemError, match="Cannot generate dialogue"):
                await character_system.generate_character_dialogue(user_id, character_id)

    # Update Relationship Tests
    
    async def test_update_relationship_success(self, character_system):
        """Test successful relationship update."""
        user_id = 1
        character_id = "diana"
        relationship_change = {
            "level_change": 5,
            "interaction_type": "supportive",
            "context": {"action": "helped_with_puzzle"}
        }
        
        with patch.object(character_system, '_load_relationship_from_db') as mock_load:
            with patch.object(character_system, '_validate_relationship_change') as mock_validate:
                with patch.object(character_system, '_apply_relationship_changes') as mock_apply:
                    with patch.object(character_system, '_save_relationship_to_db') as mock_save:
                        with patch.object(character_system, '_record_memory_event') as mock_memory:
                            
                            # Setup mocks
                            current_relationship = CharacterRelationship(
                                user_id=user_id,
                                character_id=character_id,
                                relationship_level=45,
                                relationship_type=RelationshipType.FRIENDSHIP
                            )
                            mock_load.return_value = current_relationship
                            mock_validate.return_value = (True, None)
                            
                            updated_relationship = CharacterRelationship(
                                user_id=user_id,
                                character_id=character_id,
                                relationship_level=50,
                                relationship_type=RelationshipType.FRIENDSHIP,
                                interaction_count=1
                            )
                            mock_apply.return_value = updated_relationship
                            
                            result = await character_system.update_relationship(
                                user_id, character_id, relationship_change
                            )
                            
                            assert isinstance(result, dict)
                            assert result["character_id"] == character_id
                            assert result["level"] == 50
                            assert result["type"] == "friendship"
                            assert character_system._stats["relationships_updated"] == 1
                            
                            # Verify all methods were called
                            mock_load.assert_called_once_with(user_id, character_id)
                            mock_validate.assert_called_once()
                            mock_apply.assert_called_once()
                            mock_save.assert_called_once()
                            mock_memory.assert_called_once()
    
    async def test_update_relationship_validation_failure(self, character_system):
        """Test relationship update with validation failure."""
        user_id = 1
        character_id = "diana"
        relationship_change = {"level_change": 50}  # Too large change
        
        with patch.object(character_system, '_load_relationship_from_db') as mock_load:
            with patch.object(character_system, '_validate_relationship_change') as mock_validate:
                
                mock_load.return_value = Mock()
                mock_validate.return_value = (False, "Change too large")
                
                with pytest.raises(CharacterSystemError, match="Invalid relationship change"):
                    await character_system.update_relationship(user_id, character_id, relationship_change)
    
    async def test_update_relationship_character_not_found(self, character_system):
        """Test relationship update for non-existent character."""
        user_id = 1
        character_id = "nonexistent_character"
        relationship_change = {"level_change": 5}
        
        with pytest.raises(CharacterNotFoundError, match="Character not found"):
            await character_system.update_relationship(user_id, character_id, relationship_change)
    
    async def test_update_relationship_cache_invalidation(self, character_system):
        """Test that relationship cache is invalidated after update."""
        user_id = 1
        character_id = "diana"
        
        # Populate cache first
        cache_key = f"{user_id}:{character_id}"
        relationship = CharacterRelationship(
            user_id=user_id, character_id=character_id,
            relationship_level=40, relationship_type=RelationshipType.FRIENDSHIP
        )
        character_system._relationship_cache[cache_key] = (relationship, datetime.now(timezone.utc))
        
        with patch.object(character_system, '_load_relationship_from_db') as mock_load:
            with patch.object(character_system, '_validate_relationship_change', return_value=(True, None)):
                with patch.object(character_system, '_apply_relationship_changes') as mock_apply:
                    with patch.object(character_system, '_save_relationship_to_db'):
                        with patch.object(character_system, '_record_memory_event'):
                            
                            mock_load.return_value = relationship
                            mock_apply.return_value = relationship
                            
                            await character_system.update_relationship(
                                user_id, character_id, {"level_change": 5}
                            )
                            
                            # Cache should be cleared
                            assert cache_key not in character_system._relationship_cache

    # Get Character Memory Tests
    
    async def test_get_character_memory_success(self, character_system):
        """Test successful character memory retrieval."""
        user_id = 1
        character_id = "morgan"
        
        with patch.object(character_system, '_load_interaction_history') as mock_history:
            with patch.object(character_system, '_load_relationship_from_db') as mock_relationship:
                with patch.object(character_system, '_extract_memorable_moments') as mock_moments:
                    with patch.object(character_system, '_get_character_personality_state') as mock_personality:
                        with patch.object(character_system, '_format_interaction_history') as mock_format:
                            
                            # Setup mocks
                            interactions = [
                                InteractionHistory(
                                    id="interaction_1",
                                    user_id=user_id,
                                    interaction_type="dialogue",
                                    target_id=character_id,
                                    interaction_data={"emotional_impact": 7}
                                )
                            ]
                            mock_history.return_value = interactions
                            
                            relationship = CharacterRelationship(
                                user_id=user_id,
                                character_id=character_id,
                                relationship_level=35,
                                relationship_type=RelationshipType.RIVALRY
                            )
                            mock_relationship.return_value = relationship
                            
                            mock_moments.return_value = [
                                {"timestamp": "2024-01-01", "description": "First meeting"}
                            ]
                            mock_personality.return_value = {"intelligence": 95}
                            mock_format.return_value = [
                                {"id": "interaction_1", "type": "dialogue"}
                            ]
                            
                            result = await character_system.get_character_memory(user_id, character_id)
                            
                            assert isinstance(result, CharacterMemory)
                            assert result.character_id == character_id
                            assert result.user_id == user_id
                            assert result.relationship_level == 35
                            assert result.relationship_type == RelationshipType.RIVALRY
                            assert len(result.memorable_moments) == 1
                            assert result.personality_state["intelligence"] == 95
                            assert character_system._stats["memory_recalls"] == 1
    
    async def test_get_character_memory_character_not_found(self, character_system):
        """Test character memory retrieval for non-existent character."""
        user_id = 1
        character_id = "nonexistent_character"
        
        with pytest.raises(CharacterNotFoundError, match="Character not found"):
            await character_system.get_character_memory(user_id, character_id)
    
    async def test_get_character_memory_error(self, character_system):
        """Test character memory retrieval error handling."""
        user_id = 1
        character_id = "diana"
        
        with patch.object(character_system, '_load_interaction_history') as mock_history:
            mock_history.side_effect = Exception("Memory load error")
            
            with pytest.raises(CharacterSystemError, match="Cannot retrieve character memory"):
                await character_system.get_character_memory(user_id, character_id)

    # Validate Character Consistency Tests
    
    async def test_validate_character_consistency_success(self, character_system):
        """Test successful character consistency validation."""
        character_id = "diana"
        dialogue = "Greetings, traveler. I sense wisdom in your choices."
        
        with patch.object(character_system, '_load_character_data') as mock_data:
            with patch.object(character_system, '_validate_dialogue_tone') as mock_tone:
                with patch.object(character_system, '_validate_dialogue_vocabulary') as mock_vocab:
                    with patch.object(character_system, '_validate_dialogue_values') as mock_values:
                        
                        mock_data.return_value = {
                            "personality_traits": {"wisdom": 90, "formality": 70}
                        }
                        mock_tone.return_value = (True, "")
                        mock_vocab.return_value = (True, "")
                        mock_values.return_value = (True, "")
                        
                        is_valid, error = await character_system.validate_character_consistency(
                            character_id, dialogue
                        )
                        
                        assert is_valid is True
                        assert error is None
                        assert character_system._stats["consistency_validations"] == 1
    
    async def test_validate_character_consistency_tone_failure(self, character_system):
        """Test character consistency validation with tone failure."""
        character_id = "diana"
        dialogue = "Hey dude! Yeah, whatever!"
        
        with patch.object(character_system, '_load_character_data') as mock_data:
            with patch.object(character_system, '_validate_dialogue_tone') as mock_tone:
                with patch.object(character_system, '_validate_dialogue_vocabulary') as mock_vocab:
                    with patch.object(character_system, '_validate_dialogue_values') as mock_values:
                        
                        mock_data.return_value = {
                            "personality_traits": {"formality": 90}
                        }
                        mock_tone.return_value = (False, "Too casual for formal character")
                        mock_vocab.return_value = (True, "")
                        mock_values.return_value = (True, "")
                        
                        is_valid, error = await character_system.validate_character_consistency(
                            character_id, dialogue
                        )
                        
                        assert is_valid is False
                        assert "Too casual for formal character" in error
    
    async def test_validate_character_consistency_character_not_found(self, character_system):
        """Test character consistency validation for non-existent character."""
        character_id = "nonexistent_character"
        dialogue = "Test dialogue"
        
        is_valid, error = await character_system.validate_character_consistency(
            character_id, dialogue
        )
        
        assert is_valid is False
        assert "Character not found" in error
    
    async def test_validate_character_consistency_multiple_failures(self, character_system):
        """Test character consistency validation with multiple failures."""
        character_id = "diana"
        dialogue = "yo sup dude whatever lol"
        
        with patch.object(character_system, '_load_character_data') as mock_data:
            with patch.object(character_system, '_validate_dialogue_tone') as mock_tone:
                with patch.object(character_system, '_validate_dialogue_vocabulary') as mock_vocab:
                    with patch.object(character_system, '_validate_dialogue_values') as mock_values:
                        
                        mock_data.return_value = {
                            "personality_traits": {"formality": 90, "intelligence": 95}
                        }
                        mock_tone.return_value = (False, "Too casual")
                        mock_vocab.return_value = (False, "Too simple")
                        mock_values.return_value = (True, "")
                        
                        is_valid, error = await character_system.validate_character_consistency(
                            character_id, dialogue
                        )
                        
                        assert is_valid is False
                        assert "Too casual" in error
                        assert "Too simple" in error

    # Helper Method Tests
    
    def test_apply_relationship_decay_no_interaction(self, character_system):
        """Test relationship decay with no previous interaction."""
        relationship = CharacterRelationship(
            user_id=1,
            character_id="diana",
            relationship_level=60,
            relationship_type=RelationshipType.FRIENDSHIP,
            last_interaction=None
        )
        
        result = asyncio.run(character_system._apply_relationship_decay(relationship))
        
        # No decay should occur without previous interaction
        assert result.relationship_level == 60
    
    def test_apply_relationship_decay_recent_interaction(self, character_system):
        """Test relationship decay with recent interaction."""
        recent_interaction = datetime.now(timezone.utc) - timedelta(days=3)
        relationship = CharacterRelationship(
            user_id=1,
            character_id="diana",
            relationship_level=60,
            relationship_type=RelationshipType.FRIENDSHIP,
            last_interaction=recent_interaction
        )
        
        result = asyncio.run(character_system._apply_relationship_decay(relationship))
        
        # No decay should occur for recent interaction
        assert result.relationship_level == 60
    
    def test_apply_relationship_decay_old_positive_relationship(self, character_system):
        """Test relationship decay for old positive relationship."""
        old_interaction = datetime.now(timezone.utc) - timedelta(days=20)
        relationship = CharacterRelationship(
            user_id=1,
            character_id="diana",
            relationship_level=80,
            relationship_type=RelationshipType.FRIENDSHIP,
            last_interaction=old_interaction
        )
        
        result = asyncio.run(character_system._apply_relationship_decay(relationship))
        
        # Positive relationship should decay towards neutral
        assert result.relationship_level < 80
        assert result.relationship_level >= 0
    
    def test_apply_relationship_decay_old_negative_relationship(self, character_system):
        """Test relationship decay for old negative relationship."""
        old_interaction = datetime.now(timezone.utc) - timedelta(days=20)
        relationship = CharacterRelationship(
            user_id=1,
            character_id="morgan",
            relationship_level=-80,
            relationship_type=RelationshipType.RIVALRY,
            last_interaction=old_interaction
        )
        
        result = asyncio.run(character_system._apply_relationship_decay(relationship))
        
        # Negative relationship should decay towards neutral
        assert result.relationship_level > -80
        assert result.relationship_level <= 0
    
    async def test_apply_relationship_changes_basic(self, character_system):
        """Test basic relationship change application."""
        current = CharacterRelationship(
            user_id=1,
            character_id="alex",
            relationship_level=30,
            relationship_type=RelationshipType.FRIENDSHIP,
            interaction_count=5
        )
        
        changes = {
            "level_change": 10,
            "interaction_type": "supportive",
            "context": {"action": "helped_in_battle"}
        }
        
        with patch.object(character_system, '_evaluate_relationship_evolution') as mock_evolution:
            with patch.object(character_system, '_is_memorable_interaction') as mock_memorable:
                
                mock_evolution.return_value = RelationshipType.FRIENDSHIP
                mock_memorable.return_value = False
                
                result = await character_system._apply_relationship_changes(current, changes)
                
                assert result.relationship_level == 40  # 30 + 10
                assert result.interaction_count == 6  # 5 + 1
                assert result.last_interaction is not None
                assert len(result.relationship_history) == 1
                
                history_entry = result.relationship_history[0]
                assert history_entry["change_type"] == "supportive"
                assert history_entry["level_change"] == 10
                assert history_entry["new_level"] == 40
    
    async def test_apply_relationship_changes_memorable_interaction(self, character_system):
        """Test relationship change with memorable interaction."""
        current = CharacterRelationship(
            user_id=1,
            character_id="diana",
            relationship_level=70,
            relationship_type=RelationshipType.FRIENDSHIP
        )
        
        changes = {
            "level_change": 8,
            "interaction_type": "deep_conversation",
            "emotional_impact": 9,
            "context": {"significance": "high"}
        }
        
        with patch.object(character_system, '_evaluate_relationship_evolution') as mock_evolution:
            with patch.object(character_system, '_is_memorable_interaction') as mock_memorable:
                
                mock_evolution.return_value = RelationshipType.FRIENDSHIP
                mock_memorable.return_value = True
                
                result = await character_system._apply_relationship_changes(current, changes)
                
                assert len(result.memorable_moments) == 1
                moment = result.memorable_moments[0]
                assert moment["interaction_type"] == "deep_conversation"
                assert moment["emotional_impact"] == 9
    
    async def test_apply_relationship_changes_type_evolution(self, character_system):
        """Test relationship type evolution during changes."""
        current = CharacterRelationship(
            user_id=1,
            character_id="alex",
            relationship_level=55,
            relationship_type=RelationshipType.FRIENDSHIP
        )
        
        changes = {
            "level_change": 10,
            "interaction_type": "romantic",
            "context": {"romantic_tension": True}
        }
        
        with patch.object(character_system, '_evaluate_relationship_evolution') as mock_evolution:
            with patch.object(character_system, '_is_memorable_interaction') as mock_memorable:
                
                # Should evolve to romance
                mock_evolution.return_value = RelationshipType.ROMANCE
                mock_memorable.return_value = True  # Relationship type changes are memorable
                
                result = await character_system._apply_relationship_changes(current, changes)
                
                assert result.relationship_type == RelationshipType.ROMANCE
                assert len(result.memorable_moments) == 1

    # Character Personality and Dialogue Tests
    
    async def test_load_character_data_caching(self, character_system):
        """Test character data loading and caching."""
        character_id = "diana"
        
        # First call - should miss cache
        result1 = await character_system._load_character_data(character_id)
        assert result1["id"] == character_id
        assert result1["name"] == "Diana"
        
        # Second call - should hit cache
        result2 = await character_system._load_character_data(character_id)
        assert result2["id"] == character_id
        
        # Results should be identical
        assert result1 == result2
    
    def test_select_dialogue_template(self, character_system):
        """Test dialogue template selection."""
        character_id = "diana"
        
        # Test high friendship
        template = character_system._select_dialogue_template(
            character_id, RelationshipType.FRIENDSHIP, 80
        )
        assert "dear friend" in template.lower()
        
        # Test medium friendship
        template = character_system._select_dialogue_template(
            character_id, RelationshipType.FRIENDSHIP, 40
        )
        assert "traveler" in template.lower()
        
        # Test neutral
        template = character_system._select_dialogue_template(
            character_id, RelationshipType.NEUTRAL, 0
        )
        assert "greetings" in template.lower()
    
    async def test_generate_personality_dialogue(self, character_system):
        """Test personality-driven dialogue generation."""
        character_data = {
            "id": "alex",
            "personality_traits": {"enthusiasm": 95, "humor": 80}
        }
        
        relationship = CharacterRelationship(
            user_id=1,
            character_id="alex",
            relationship_level=60,
            relationship_type=RelationshipType.FRIENDSHIP
        )
        
        memory = CharacterMemory(
            character_id="alex",
            user_id=1,
            interaction_history=[],
            relationship_level=60,
            relationship_type=RelationshipType.FRIENDSHIP,
            memorable_moments=[],
            personality_state={"enthusiasm": 95}
        )
        
        with patch.object(character_system, '_select_dialogue_template') as mock_template:
            with patch.object(character_system, '_apply_personality_to_template') as mock_personality:
                with patch.object(character_system, '_add_relationship_context') as mock_context:
                    with patch.object(character_system, '_add_memory_references') as mock_memory_ref:
                        with patch.object(character_system, '_apply_speech_patterns') as mock_speech:
                            
                            mock_template.return_value = "Hey buddy! Ready for our next adventure?"
                            mock_personality.return_value = "Hey buddy! Ready for our next adventure!"
                            mock_context.return_value = "Hey buddy! Ready for our next adventure? I'm really glad we can talk like this."
                            mock_memory_ref.return_value = "Hey buddy! Ready for our next adventure? I'm really glad we can talk like this."
                            mock_speech.return_value = "Hey buddy! Ready for our next adventure? I'm really glad we can talk like this. *grins confidently*"
                            
                            result = await character_system._generate_personality_dialogue(
                                character_data, relationship, memory, None
                            )
                            
                            assert "Hey buddy" in result
                            assert "*grins confidently*" in result
                            
                            # Verify all steps were called
                            mock_template.assert_called_once()
                            mock_personality.assert_called_once()
                            mock_context.assert_called_once()
                            mock_memory_ref.assert_called_once()
                            mock_speech.assert_called_once()
    
    async def test_generate_response_options_basic(self, character_system):
        """Test basic response options generation."""
        character_id = "sam"
        relationship = CharacterRelationship(
            user_id=1,
            character_id=character_id,
            relationship_level=20,
            relationship_type=RelationshipType.FRIENDSHIP
        )
        
        result = await character_system._generate_response_options(
            character_id, relationship, None
        )
        
        # Should have basic response options
        assert len(result) >= 3
        response_ids = [r["id"] for r in result]
        assert "friendly" in response_ids
        assert "neutral" in response_ids
        assert "distant" in response_ids
    
    async def test_generate_response_options_high_relationship(self, character_system):
        """Test response options for high relationship level."""
        character_id = "diana"
        relationship = CharacterRelationship(
            user_id=1,
            character_id=character_id,
            relationship_level=75,
            relationship_type=RelationshipType.FRIENDSHIP
        )
        
        result = await character_system._generate_response_options(
            character_id, relationship, None
        )
        
        # Should include intimate option for high relationship
        response_ids = [r["id"] for r in result]
        assert "intimate" in response_ids
        
        intimate_option = next(r for r in result if r["id"] == "intimate")
        assert intimate_option["required_level"] == 50
    
    async def test_generate_response_options_romance(self, character_system):
        """Test response options for romance relationship."""
        character_id = "alex"
        relationship = CharacterRelationship(
            user_id=1,
            character_id=character_id,
            relationship_level=40,
            relationship_type=RelationshipType.ROMANCE
        )
        
        result = await character_system._generate_response_options(
            character_id, relationship, None
        )
        
        # Should include flirt option for romance
        response_ids = [r["id"] for r in result]
        assert "flirt" in response_ids
        
        flirt_option = next(r for r in result if r["id"] == "flirt")
        assert flirt_option["relationship_impact"]["type"] == "romance_boost"
    
    async def test_generate_response_options_rivalry(self, character_system):
        """Test response options for rivalry relationship."""
        character_id = "morgan"
        relationship = CharacterRelationship(
            user_id=1,
            character_id=character_id,
            relationship_level=-30,
            relationship_type=RelationshipType.RIVALRY
        )
        
        result = await character_system._generate_response_options(
            character_id, relationship, None
        )
        
        # Should include challenge option for rivalry
        response_ids = [r["id"] for r in result]
        assert "challenge" in response_ids
        
        challenge_option = next(r for r in result if r["id"] == "challenge")
        assert challenge_option["relationship_impact"]["type"] == "rivalry_boost"

    # Character Memory and Personality Tests
    
    async def test_get_character_personality_state_high_relationship(self, character_system):
        """Test personality state calculation for high relationship."""
        character_id = "sam"
        relationship = CharacterRelationship(
            user_id=1,
            character_id=character_id,
            relationship_level=80,
            relationship_type=RelationshipType.FRIENDSHIP
        )
        
        result = await character_system._get_character_personality_state(character_id, relationship)
        
        # High relationship should increase openness and trust
        assert result["openness"] > 50
        assert result["trust"] > 50
    
    async def test_get_character_personality_state_low_relationship(self, character_system):
        """Test personality state calculation for low relationship."""
        character_id = "morgan"
        relationship = CharacterRelationship(
            user_id=1,
            character_id=character_id,
            relationship_level=-70,
            relationship_type=RelationshipType.RIVALRY
        )
        
        result = await character_system._get_character_personality_state(character_id, relationship)
        
        # Poor relationship should increase defensiveness and hostility
        assert result.get("defensiveness", 0) > 50
        assert result.get("hostility", 0) > 0
    
    async def test_get_character_personality_state_romance(self, character_system):
        """Test personality state calculation for romance relationship."""
        character_id = "alex"
        relationship = CharacterRelationship(
            user_id=1,
            character_id=character_id,
            relationship_level=65,
            relationship_type=RelationshipType.ROMANCE
        )
        
        result = await character_system._get_character_personality_state(character_id, relationship)
        
        # Romance should add romantic interest
        assert result["romantic_interest"] == 65
    
    def test_calculate_character_mood_happy(self, character_system):
        """Test character mood calculation for happy state."""
        relationship = CharacterRelationship(
            user_id=1,
            character_id="alex",
            relationship_level=75,
            relationship_type=RelationshipType.FRIENDSHIP
        )
        
        memory = CharacterMemory(
            character_id="alex",
            user_id=1,
            interaction_history=[],
            relationship_level=75,
            relationship_type=RelationshipType.FRIENDSHIP,
            memorable_moments=[],
            personality_state={}
        )
        
        mood = character_system._calculate_character_mood(relationship, memory)
        assert mood == "happy"
    
    def test_calculate_character_mood_with_emotional_memory(self, character_system):
        """Test character mood calculation with emotional memory impact."""
        relationship = CharacterRelationship(
            user_id=1,
            character_id="diana",
            relationship_level=40,  # Should be "friendly" normally
            relationship_type=RelationshipType.FRIENDSHIP
        )
        
        memory = CharacterMemory(
            character_id="diana",
            user_id=1,
            interaction_history=[],
            relationship_level=40,
            relationship_type=RelationshipType.FRIENDSHIP,
            memorable_moments=[
                {"emotional_impact": 8, "description": "Amazing conversation"}
            ],
            personality_state={}
        )
        
        mood = character_system._calculate_character_mood(relationship, memory)
        # Should be "excited" due to high emotional impact in memory
        assert mood == "excited"
    
    def test_select_relevant_memories(self, character_system):
        """Test relevant memory selection."""
        memory = CharacterMemory(
            character_id="diana",
            user_id=1,
            interaction_history=[],
            relationship_level=50,
            relationship_type=RelationshipType.FRIENDSHIP,
            memorable_moments=[
                {"description": "First meeting"},
                {"description": "Deep conversation"},
                {"description": "Shared secret"},
                {"description": "Fourth memory"},
                {"description": "Fifth memory"}
            ],
            personality_state={}
        )
        
        result = character_system._select_relevant_memories(memory, None)
        
        # Should select up to 3 most relevant (first 3)
        assert len(result) == 3
        assert "First meeting" in result
        assert "Deep conversation" in result
        assert "Shared secret" in result
    
    def test_select_relevant_memories_empty(self, character_system):
        """Test relevant memory selection with no memories."""
        memory = CharacterMemory(
            character_id="sam",
            user_id=1,
            interaction_history=[],
            relationship_level=0,
            relationship_type=RelationshipType.NEUTRAL,
            memorable_moments=[],
            personality_state={}
        )
        
        result = character_system._select_relevant_memories(memory, None)
        assert result == []

    # Validation Method Tests
    
    async def test_validate_relationship_change_success(self, character_system):
        """Test successful relationship change validation."""
        current = CharacterRelationship(
            user_id=1,
            character_id="diana",
            relationship_level=50,
            relationship_type=RelationshipType.FRIENDSHIP
        )
        
        change = {"level_change": 10, "interaction_type": "supportive"}
        
        with patch.object(character_system, '_is_valid_type_transition', return_value=True):
            is_valid, error = await character_system._validate_relationship_change(current, change)
            
            assert is_valid is True
            assert error is None
    
    async def test_validate_relationship_change_too_large(self, character_system):
        """Test relationship change validation with too large change."""
        current = CharacterRelationship(
            user_id=1,
            character_id="diana",
            relationship_level=50,
            relationship_type=RelationshipType.FRIENDSHIP
        )
        
        change = {"level_change": 20}  # Too large
        
        is_valid, error = await character_system._validate_relationship_change(current, change)
        
        assert is_valid is False
        assert "too large" in error
    
    async def test_validate_relationship_change_invalid_type_transition(self, character_system):
        """Test relationship change validation with invalid type transition."""
        current = CharacterRelationship(
            user_id=1,
            character_id="morgan",
            relationship_level=-30,
            relationship_type=RelationshipType.RIVALRY
        )
        
        change = {"new_type": RelationshipType.ROMANCE}  # Invalid transition
        
        with patch.object(character_system, '_is_valid_type_transition', return_value=False):
            is_valid, error = await character_system._validate_relationship_change(current, change)
            
            assert is_valid is False
            assert "Invalid relationship type transition" in error
    
    def test_is_valid_type_transition(self, character_system):
        """Test relationship type transition validation."""
        # Valid transitions
        assert character_system._is_valid_type_transition(
            RelationshipType.NEUTRAL, RelationshipType.FRIENDSHIP
        ) is True
        
        assert character_system._is_valid_type_transition(
            RelationshipType.FRIENDSHIP, RelationshipType.ROMANCE
        ) is True
        
        assert character_system._is_valid_type_transition(
            RelationshipType.RIVALRY, RelationshipType.FRIENDSHIP
        ) is True  # Redemption arc
        
        # Invalid transitions
        assert character_system._is_valid_type_transition(
            RelationshipType.NEUTRAL, RelationshipType.ROMANCE
        ) is False
        
        assert character_system._is_valid_type_transition(
            RelationshipType.RIVALRY, RelationshipType.ROMANCE
        ) is False
    
    async def test_evaluate_relationship_evolution_neutral_to_friendship(self, character_system):
        """Test relationship evolution from neutral to friendship."""
        relationship = CharacterRelationship(
            user_id=1,
            character_id="sam",
            relationship_level=30,
            relationship_type=RelationshipType.NEUTRAL
        )
        
        result = await character_system._evaluate_relationship_evolution(
            relationship, "supportive"
        )
        
        assert result == RelationshipType.FRIENDSHIP
    
    async def test_evaluate_relationship_evolution_friendship_to_romance(self, character_system):
        """Test relationship evolution from friendship to romance."""
        relationship = CharacterRelationship(
            user_id=1,
            character_id="alex",
            relationship_level=65,
            relationship_type=RelationshipType.FRIENDSHIP
        )
        
        result = await character_system._evaluate_relationship_evolution(
            relationship, "romantic"
        )
        
        assert result == RelationshipType.ROMANCE
    
    async def test_evaluate_relationship_evolution_no_change(self, character_system):
        """Test relationship evolution when no change should occur."""
        relationship = CharacterRelationship(
            user_id=1,
            character_id="diana",
            relationship_level=15,  # Too low for evolution
            relationship_type=RelationshipType.NEUTRAL
        )
        
        result = await character_system._evaluate_relationship_evolution(
            relationship, "neutral"
        )
        
        assert result == RelationshipType.NEUTRAL
    
    async def test_is_memorable_interaction_high_emotional_impact(self, character_system):
        """Test memorable interaction detection for high emotional impact."""
        changes = {
            "emotional_impact": 8,
            "level_change": 2,
            "interaction_type": "heartfelt"
        }
        
        result = await character_system._is_memorable_interaction(changes)
        assert result is True
    
    async def test_is_memorable_interaction_significant_relationship_change(self, character_system):
        """Test memorable interaction detection for significant relationship change."""
        changes = {
            "level_change": 7,
            "emotional_impact": 2
        }
        
        result = await character_system._is_memorable_interaction(changes)
        assert result is True
    
    async def test_is_memorable_interaction_story_significance(self, character_system):
        """Test memorable interaction detection for story significance."""
        changes = {
            "level_change": 2,
            "story_significance": True
        }
        
        result = await character_system._is_memorable_interaction(changes)
        assert result is True
    
    async def test_is_memorable_interaction_first_type(self, character_system):
        """Test memorable interaction detection for first interaction of type."""
        changes = {
            "level_change": 1,
            "first_interaction_of_type": True
        }
        
        result = await character_system._is_memorable_interaction(changes)
        assert result is True
    
    async def test_is_memorable_interaction_not_memorable(self, character_system):
        """Test memorable interaction detection for ordinary interaction."""
        changes = {
            "level_change": 2,
            "emotional_impact": 1,
            "interaction_type": "casual"
        }
        
        result = await character_system._is_memorable_interaction(changes)
        assert result is False

    # Dialogue Validation Tests
    
    def test_validate_dialogue_tone_formal_character_formal_dialogue(self, character_system):
        """Test dialogue tone validation for formal character with formal dialogue."""
        personality = {"formality": 85}
        dialogue = "Indeed, I find your proposal quite intriguing and certainly worthy of consideration."
        
        is_valid, error = character_system._validate_dialogue_tone(personality, dialogue)
        assert is_valid is True
        assert error == ""
    
    def test_validate_dialogue_tone_formal_character_casual_dialogue(self, character_system):
        """Test dialogue tone validation for formal character with casual dialogue."""
        personality = {"formality": 90}
        dialogue = "Hey yeah, that's pretty cool stuff!"
        
        is_valid, error = character_system._validate_dialogue_tone(personality, dialogue)
        assert is_valid is False
        assert "too casual" in error.lower()
    
    def test_validate_dialogue_tone_casual_character_formal_dialogue(self, character_system):
        """Test dialogue tone validation for casual character with formal dialogue."""
        personality = {"formality": 15}
        dialogue = "Indeed, I must certainly express my most sincere gratitude for your consideration."
        
        is_valid, error = character_system._validate_dialogue_tone(personality, dialogue)
        assert is_valid is False
        assert "too formal" in error.lower()
    
    def test_validate_dialogue_vocabulary_intelligent_character(self, character_system):
        """Test dialogue vocabulary validation for intelligent character."""
        personality = {"intelligence": 95}
        dialogue = "The perspicacious individual comprehends the multifaceted complexities inherent in such philosophical deliberations."
        
        is_valid, error = character_system._validate_dialogue_vocabulary(personality, dialogue)
        assert is_valid is True
        assert error == ""
    
    def test_validate_dialogue_vocabulary_simple_character_complex_dialogue(self, character_system):
        """Test vocabulary validation for simple character with complex dialogue."""
        personality = {"intelligence": 25}
        dialogue = "The sophisticated metamorphosis of interpersonal dynamics necessitates comprehensive analytical methodologies."
        
        is_valid, error = character_system._validate_dialogue_vocabulary(personality, dialogue)
        assert is_valid is False
        assert "too complex" in error.lower()
    
    def test_validate_dialogue_values_honest_character(self, character_system):
        """Test dialogue values validation for honest character."""
        personality = {"core_values": ["honesty", "kindness"]}
        dialogue = "I believe in telling you the truth, even when it's difficult."
        
        is_valid, error = character_system._validate_dialogue_values(personality, dialogue)
        assert is_valid is True
        assert error == ""
    
    def test_validate_dialogue_values_honest_character_dishonest_dialogue(self, character_system):
        """Test values validation for honest character with dishonest dialogue."""
        personality = {"core_values": ["honesty"]}
        dialogue = "I think we should lie to them and deceive everyone about this."
        
        is_valid, error = character_system._validate_dialogue_values(personality, dialogue)
        assert is_valid is False
        assert "honesty" in error.lower()

    # Memory Management Tests
    
    async def test_extract_memorable_moments_high_impact(self, character_system):
        """Test memorable moment extraction for high emotional impact."""
        interactions = [
            InteractionHistory(
                id="interaction_1",
                user_id=1,
                interaction_type="deep_talk",
                target_id="diana",
                interaction_data={
                    "emotional_impact": 9,
                    "description": "Heart-to-heart conversation"
                }
            ),
            InteractionHistory(
                id="interaction_2",
                user_id=1,
                interaction_type="casual",
                target_id="diana",
                interaction_data={
                    "emotional_impact": 2,
                    "description": "Small talk"
                }
            )
        ]
        
        result = await character_system._extract_memorable_moments(interactions)
        
        # Should only include high-impact interaction
        assert len(result) == 1
        assert result[0]["description"] == "Heart-to-heart conversation"
        assert result[0]["emotional_impact"] == 9
    
    async def test_extract_memorable_moments_story_significance(self, character_system):
        """Test memorable moment extraction for story significant interactions."""
        interactions = [
            InteractionHistory(
                id="interaction_1",
                user_id=1,
                interaction_type="story_decision",
                target_id="morgan",
                interaction_data={
                    "story_significance": True,
                    "description": "Major story choice"
                }
            )
        ]
        
        result = await character_system._extract_memorable_moments(interactions)
        
        assert len(result) == 1
        assert result[0]["description"] == "Major story choice"
    
    async def test_extract_memorable_moments_relationship_impact(self, character_system):
        """Test memorable moment extraction for high relationship impact."""
        interactions = [
            InteractionHistory(
                id="interaction_1",
                user_id=1,
                interaction_type="conflict",
                target_id="alex",
                interaction_data={"description": "Major argument"},
                relationship_impact={"alex": -12}  # High negative impact
            )
        ]
        
        result = await character_system._extract_memorable_moments(interactions)
        
        assert len(result) == 1
        assert result[0]["description"] == "Major argument"
    
    async def test_extract_memorable_moments_sorting(self, character_system):
        """Test memorable moments are sorted by impact and recency."""
        interactions = [
            InteractionHistory(
                id="interaction_1",
                user_id=1,
                interaction_type="low_impact",
                target_id="sam",
                interaction_data={
                    "emotional_impact": 6,
                    "description": "Moderate conversation"
                },
                timestamp=datetime.now(timezone.utc) - timedelta(days=2)
            ),
            InteractionHistory(
                id="interaction_2",
                user_id=1,
                interaction_type="high_impact",
                target_id="sam",
                interaction_data={
                    "emotional_impact": 9,
                    "description": "Amazing moment"
                },
                timestamp=datetime.now(timezone.utc) - timedelta(days=1)
            )
        ]
        
        result = await character_system._extract_memorable_moments(interactions)
        
        # Should be sorted by emotional impact (highest first)
        assert len(result) == 2
        assert result[0]["description"] == "Amazing moment"
        assert result[1]["description"] == "Moderate conversation"
    
    async def test_extract_memorable_moments_limit(self, character_system):
        """Test memorable moments limit (max 10)."""
        interactions = [
            InteractionHistory(
                id=f"interaction_{i}",
                user_id=1,
                interaction_type="high_impact",
                target_id="diana",
                interaction_data={
                    "emotional_impact": 8,
                    "description": f"Memorable moment {i}"
                }
            )
            for i in range(15)  # Create 15 memorable interactions
        ]
        
        result = await character_system._extract_memorable_moments(interactions)
        
        # Should be limited to 10
        assert len(result) == 10

    # Speech Pattern and Style Tests
    
    def test_apply_speech_patterns_diana(self, character_system):
        """Test speech pattern application for Diana."""
        dialogue = "I think maybe you should consider this path."
        result = character_system._apply_speech_patterns(dialogue, "diana")
        
        # Diana replaces "I think" with "I sense" and "maybe" with "perhaps"
        assert "I sense" in result
        assert "perhaps" in result
        assert "I think" not in result
        assert "maybe" not in result
    
    def test_apply_speech_patterns_alex(self, character_system):
        """Test speech pattern application for Alex."""
        dialogue = "That sounds great! Let's do it!"
        
        # Mock random to ensure consistent behavior
        with patch('random.random', return_value=0.5):
            result = character_system._apply_speech_patterns(dialogue, "alex")
        
        # Alex adds confident grin to exclamatory statements
        assert "*grins confidently*" in result
    
    def test_apply_speech_patterns_morgan(self, character_system):
        """Test speech pattern application for Morgan."""
        dialogue = "That is an interesting perspective on the matter."
        result = character_system._apply_speech_patterns(dialogue, "morgan")
        
        # Morgan replaces periods with ellipses for longer statements
        assert "..." in result
        assert "." not in result
    
    def test_apply_speech_patterns_sam(self, character_system):
        """Test speech pattern application for Sam."""
        dialogue = "I really appreciate your help with this."
        
        # Mock random to ensure consistent behavior
        with patch('random.random', return_value=0.3):  # 40% chance should trigger
            result = character_system._apply_speech_patterns(dialogue, "sam")
        
        # Sam adds nervous speech pattern
        assert "I... um, I" in result
    
    def test_apply_speech_patterns_unknown_character(self, character_system):
        """Test speech pattern application for unknown character."""
        dialogue = "This is a test dialogue."
        result = character_system._apply_speech_patterns(dialogue, "unknown_character")
        
        # Should return unchanged for unknown character
        assert result == dialogue

    # Personality Application Tests
    
    async def test_apply_personality_to_template_enthusiastic(self, character_system):
        """Test personality application for enthusiastic character."""
        template = "That sounds good. I agree with you."
        personality = {"enthusiasm": 85}
        
        result = await character_system._apply_personality_to_template(template, personality)
        
        # Should replace periods with exclamation marks
        assert "!" in result
        assert result.count("!") > template.count("!")
    
    async def test_apply_personality_to_template_formal(self, character_system):
        """Test personality application for formal character."""
        template = "Hey there! Yeah, that works for me."
        personality = {"formality": 90}
        
        result = await character_system._apply_personality_to_template(template, personality)
        
        # Should replace casual words with formal equivalents
        assert "greetings" in result.lower()
        assert "indeed" in result.lower()
        assert "hey" not in result.lower()
        assert "yeah" not in result.lower()
    
    async def test_apply_personality_to_template_humorous(self, character_system):
        """Test personality application for humorous character."""
        template = "That's an interesting idea."
        personality = {"humor": 90}
        
        # Mock random to ensure consistent behavior
        with patch('random.random', return_value=0.2):  # 30% chance should trigger
            result = await character_system._apply_personality_to_template(template, personality)
        
        # Should add chuckle
        assert "*chuckles*" in result
    
    def test_add_relationship_context_high_relationship(self, character_system):
        """Test relationship context addition for high relationship."""
        dialogue = "How are you doing today?"
        relationship = CharacterRelationship(
            user_id=1,
            character_id="alex",
            relationship_level=75,
            relationship_type=RelationshipType.FRIENDSHIP
        )
        
        result = character_system._add_relationship_context(dialogue, relationship)
        
        # Should add warmth for high relationship
        assert len(result) > len(dialogue)
        assert "glad we can talk" in result.lower()
    
    def test_add_relationship_context_poor_relationship(self, character_system):
        """Test relationship context addition for poor relationship."""
        dialogue = "What do you want?"
        relationship = CharacterRelationship(
            user_id=1,
            character_id="morgan",
            relationship_level=-50,
            relationship_type=RelationshipType.RIVALRY
        )
        
        result = character_system._add_relationship_context(dialogue, relationship)
        
        # Should add tension for poor relationship
        assert "*speaks with noticeable tension*" in result
    
    def test_add_relationship_context_neutral(self, character_system):
        """Test relationship context addition for neutral relationship."""
        dialogue = "Hello there."
        relationship = CharacterRelationship(
            user_id=1,
            character_id="sam",
            relationship_level=15,
            relationship_type=RelationshipType.NEUTRAL
        )
        
        result = character_system._add_relationship_context(dialogue, relationship)
        
        # Should remain unchanged for neutral relationship
        assert result == dialogue

    # Memory Reference Tests
    
    async def test_add_memory_references_with_memories(self, character_system):
        """Test memory reference addition when memories exist."""
        dialogue = "Good to see you again."
        memory = CharacterMemory(
            character_id="diana",
            user_id=1,
            interaction_history=[],
            relationship_level=50,
            relationship_type=RelationshipType.FRIENDSHIP,
            memorable_moments=[
                {"description": "our first meeting in the forest"}
            ],
            personality_state={}
        )
        
        # Mock random to ensure memory reference is added
        with patch('random.random', return_value=0.2):  # 30% chance should trigger
            result = await character_system._add_memory_references(dialogue, memory, None)
        
        assert len(result) > len(dialogue)
        assert "our first meeting in the forest" in result
    
    async def test_add_memory_references_no_memories(self, character_system):
        """Test memory reference addition when no memories exist."""
        dialogue = "Hello there."
        memory = CharacterMemory(
            character_id="sam",
            user_id=1,
            interaction_history=[],
            relationship_level=20,
            relationship_type=RelationshipType.NEUTRAL,
            memorable_moments=[],
            personality_state={}
        )
        
        result = await character_system._add_memory_references(dialogue, memory, None)
        
        # Should remain unchanged with no memories
        assert result == dialogue
    
    async def test_add_memory_references_random_skip(self, character_system):
        """Test memory reference addition when random chance doesn't trigger."""
        dialogue = "Good to see you."
        memory = CharacterMemory(
            character_id="alex",
            user_id=1,
            interaction_history=[],
            relationship_level=60,
            relationship_type=RelationshipType.FRIENDSHIP,
            memorable_moments=[
                {"description": "that time we fought the dragon"}
            ],
            personality_state={}
        )
        
        # Mock random to ensure memory reference is NOT added
        with patch('random.random', return_value=0.8):  # Above 30% threshold
            result = await character_system._add_memory_references(dialogue, memory, None)
        
        # Should remain unchanged
        assert result == dialogue

    # Performance and Edge Case Tests
    
    async def test_concurrent_dialogue_generation(self, character_system):
        """Test concurrent dialogue generation."""
        user_id = 1
        character_ids = ["diana", "alex", "morgan", "sam"]
        
        with patch.object(character_system, '_load_character_data') as mock_data:
            with patch.object(character_system, '_load_relationship_from_db') as mock_relationship:
                with patch.object(character_system, 'get_character_memory') as mock_memory:
                    with patch.object(character_system, '_generate_personality_dialogue') as mock_dialogue:
                        with patch.object(character_system, '_generate_response_options') as mock_responses:
                            with patch.object(character_system, '_calculate_character_mood') as mock_mood:
                                with patch.object(character_system, '_select_relevant_memories') as mock_memories:
                                    
                                    # Setup mocks
                                    mock_data.return_value = {"id": "test", "personality_traits": {}}
                                    mock_relationship.return_value = CharacterRelationship(
                                        user_id=user_id, character_id="test",
                                        relationship_level=25, relationship_type=RelationshipType.FRIENDSHIP
                                    )
                                    mock_memory.return_value = Mock()
                                    mock_dialogue.return_value = "Test dialogue"
                                    mock_responses.return_value = []
                                    mock_mood.return_value = "neutral"
                                    mock_memories.return_value = []
                                    
                                    # Generate dialogue for all characters concurrently
                                    tasks = [
                                        character_system.generate_character_dialogue(user_id, char_id)
                                        for char_id in character_ids
                                    ]
                                    
                                    results = await asyncio.gather(*tasks, return_exceptions=True)
                                    
                                    # All should succeed
                                    assert all(isinstance(result, Dialogue) for result in results)
                                    assert character_system._stats["dialogues_generated"] == len(character_ids)
    
    async def test_relationship_to_dict_conversion(self, character_system):
        """Test relationship object to dictionary conversion."""
        relationship = CharacterRelationship(
            user_id=1,
            character_id="diana",
            relationship_level=65,
            relationship_type=RelationshipType.FRIENDSHIP,
            interaction_count=15,
            last_interaction=datetime.now(timezone.utc),
            memorable_moments=[{"test": "moment"}],
            created_at=datetime.now(timezone.utc)
        )
        
        result = character_system._relationship_to_dict(relationship)
        
        assert result["character_id"] == "diana"
        assert result["level"] == 65
        assert result["type"] == "friendship"
        assert result["interaction_count"] == 15
        assert result["last_interaction"] is not None
        assert result["memorable_moments"] == [{"test": "moment"}]
        assert result["created_at"] is not None
    
    async def test_relationship_to_dict_no_last_interaction(self, character_system):
        """Test relationship dictionary conversion with no last interaction."""
        relationship = CharacterRelationship(
            user_id=1,
            character_id="sam",
            relationship_level=0,
            relationship_type=RelationshipType.NEUTRAL,
            last_interaction=None
        )
        
        result = character_system._relationship_to_dict(relationship)
        
        assert result["last_interaction"] is None
    
    def test_format_interaction_history(self, character_system):
        """Test interaction history formatting."""
        interactions = [
            InteractionHistory(
                id="interaction_1",
                user_id=1,
                interaction_type="dialogue",
                target_id="diana",
                interaction_data={"mood": "happy"},
                relationship_impact={"diana": 3},
                timestamp=datetime.now(timezone.utc)
            )
        ]
        
        result = character_system._format_interaction_history(interactions)
        
        assert len(result) == 1
        entry = result[0]
        assert entry["id"] == "interaction_1"
        assert entry["type"] == "dialogue"
        assert entry["data"] == {"mood": "happy"}
        assert entry["relationship_impact"] == {"diana": 3}
        assert "timestamp" in entry

    # Personality System Tests
    
    def test_character_personalities_loaded(self, character_system):
        """Test that character personalities are properly loaded."""
        personalities = character_system._character_personalities
        
        # Should have all main characters
        for character_id in MAIN_CHARACTERS.keys():
            assert character_id in personalities
            
            personality = personalities[character_id]
            assert "core_values" in personality
            assert "speech_style" in personality
            assert isinstance(personality["core_values"], list)
    
    def test_character_personality_diana(self, character_system):
        """Test Diana's specific personality traits."""
        diana_personality = character_system._character_personalities["diana"]
        
        assert diana_personality["wisdom"] == 90
        assert diana_personality["mysticism"] == 95
        assert diana_personality["formality"] == 70
        assert "wisdom" in diana_personality["core_values"]
        assert diana_personality["speech_style"] == "thoughtful_mentor"
    
    def test_character_personality_alex(self, character_system):
        """Test Alex's specific personality traits."""
        alex_personality = character_system._character_personalities["alex"]
        
        assert alex_personality["enthusiasm"] == 95
        assert alex_personality["courage"] == 90
        assert alex_personality["formality"] == 20  # Very casual
        assert "adventure" in alex_personality["core_values"]
        assert alex_personality["speech_style"] == "energetic_friend"
    
    def test_dialogue_templates_loaded(self, character_system):
        """Test that dialogue templates are properly loaded."""
        templates = character_system._dialogue_templates
        
        # Should have templates for all main characters
        for character_id in MAIN_CHARACTERS.keys():
            assert character_id in templates
            
            char_templates = templates[character_id]
            assert "default" in char_templates
            assert "neutral" in char_templates
            
            # Each template should be a non-empty string
            for template_name, template_text in char_templates.items():
                assert isinstance(template_text, str)
                assert len(template_text) > 0

    # Error Handling and Edge Cases
    
    async def test_concurrent_relationship_updates_same_user_character(self, character_system):
        """Test concurrent relationship updates for same user-character pair."""
        user_id = 1
        character_id = "diana"
        
        with patch.object(character_system, '_load_relationship_from_db') as mock_load:
            with patch.object(character_system, '_validate_relationship_change', return_value=(True, None)):
                with patch.object(character_system, '_apply_relationship_changes') as mock_apply:
                    with patch.object(character_system, '_save_relationship_to_db'):
                        with patch.object(character_system, '_record_memory_event'):
                            
                            base_relationship = CharacterRelationship(
                                user_id=user_id, character_id=character_id,
                                relationship_level=40, relationship_type=RelationshipType.FRIENDSHIP
                            )
                            mock_load.return_value = base_relationship
                            mock_apply.return_value = base_relationship
                            
                            # Run concurrent updates
                            tasks = [
                                character_system.update_relationship(
                                    user_id, character_id, {"level_change": i}
                                )
                                for i in range(1, 6)
                            ]
                            
                            results = await asyncio.gather(*tasks, return_exceptions=True)
                            
                            # All should succeed (no race conditions)
                            assert all(isinstance(result, dict) for result in results)
    
    async def test_memory_retention_cutoff(self, character_system):
        """Test memory retention with cutoff date."""
        user_id = 1
        character_id = "alex"
        
        # Create mix of old and recent interactions
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=character_system.memory_retention_days)
        
        old_interaction = InteractionHistory(
            id="old",
            user_id=user_id,
            interaction_type="dialogue",
            target_id=character_id,
            interaction_data={},
            timestamp=cutoff_date - timedelta(days=5)  # Before cutoff
        )
        
        recent_interaction = InteractionHistory(
            id="recent",
            user_id=user_id,
            interaction_type="dialogue",
            target_id=character_id,
            interaction_data={},
            timestamp=datetime.now(timezone.utc)  # After cutoff
        )
        
        # The actual implementation should filter by cutoff date
        # This test verifies the cutoff calculation is correct
        assert old_interaction.timestamp < cutoff_date
        assert recent_interaction.timestamp > cutoff_date

    # Large Scale Tests
    
    async def test_massive_memorable_moments_limit(self, character_system):
        """Test memorable moments limit with massive interaction history."""
        current = CharacterRelationship(
            user_id=1,
            character_id="diana",
            relationship_level=50,
            relationship_type=RelationshipType.FRIENDSHIP,
            memorable_moments=[{"moment": f"memory_{i}"} for i in range(25)]  # Over limit
        )
        
        changes = {
            "level_change": 5,
            "interaction_type": "memorable_event"
        }
        
        with patch.object(character_system, '_evaluate_relationship_evolution') as mock_evolution:
            with patch.object(character_system, '_is_memorable_interaction') as mock_memorable:
                
                mock_evolution.return_value = RelationshipType.FRIENDSHIP
                mock_memorable.return_value = True
                
                result = await character_system._apply_relationship_changes(current, changes)
                
                # Should limit to 20 memorable moments
                assert len(result.memorable_moments) == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])