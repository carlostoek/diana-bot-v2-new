"""
Comprehensive Unit Tests for Story Engine

This module provides extensive unit test coverage for the Story Engine component,
including branching narrative logic, personalization, and consistency validation.
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

from services.narrative.engines.story_engine import StoryEngine
from services.narrative.interfaces import (
    ChapterContent,
    StoryState,
    UnlockedContent,
    ContentType,
    StoryEngineError,
    ChapterNotFoundError,
    VIPRequiredError,
    StoryConsistencyError,
)
from services.narrative.models import (
    StoryChapter,
    UserStoryProgress,
    PersonalizationProfile,
    STORY_CHAPTERS,
    MORAL_ALIGNMENTS,
)
from core.interfaces import IEventBus


class TestStoryEngine:
    """Comprehensive test suite for StoryEngine."""
    
    @pytest.fixture
    async def event_bus_mock(self):
        """Create a mock event bus."""
        mock = AsyncMock(spec=IEventBus)
        return mock
    
    @pytest.fixture
    async def story_engine(self, event_bus_mock):
        """Create a story engine instance for testing."""
        return StoryEngine(
            event_bus=event_bus_mock,
            content_cache_ttl=3600,
            enable_consistency_checks=True
        )
    
    @pytest.fixture
    async def story_engine_no_consistency(self, event_bus_mock):
        """Create a story engine instance with consistency checks disabled."""
        return StoryEngine(
            event_bus=event_bus_mock,
            content_cache_ttl=3600,
            enable_consistency_checks=False
        )

    # Initialization Tests
    
    def test_initialization_default(self, event_bus_mock):
        """Test default initialization of story engine."""
        engine = StoryEngine(event_bus_mock)
        
        assert engine.event_bus == event_bus_mock
        assert engine.content_cache_ttl == 3600
        assert engine.enable_consistency_checks is True
        assert len(engine._chapter_cache) == 0
        assert len(engine._user_state_cache) == 0
        assert engine._stats["chapters_loaded"] == 0
    
    def test_initialization_custom_settings(self, event_bus_mock):
        """Test initialization with custom settings."""
        engine = StoryEngine(
            event_bus=event_bus_mock,
            content_cache_ttl=1800,
            enable_consistency_checks=False
        )
        
        assert engine.content_cache_ttl == 1800
        assert engine.enable_consistency_checks is False

    # Load Story State Tests
    
    async def test_load_story_state_success(self, story_engine):
        """Test successful story state loading."""
        user_id = 1
        
        with patch.object(story_engine, '_load_user_progress') as mock_progress:
            with patch.object(story_engine, '_load_user_flags') as mock_flags:
                with patch.object(story_engine, '_load_user_relationships') as mock_relationships:
                    with patch.object(story_engine, '_check_vip_status') as mock_vip:
                        with patch.object(story_engine, '_calculate_unlocked_branches') as mock_branches:
                            
                            # Setup mocks
                            mock_progress_obj = UserStoryProgress(
                                user_id=user_id,
                                current_chapter="chapter_01",
                                completed_chapters=["prologue"],
                                moral_alignment={"compassionate": 50}
                            )
                            mock_progress.return_value = mock_progress_obj
                            mock_flags.return_value = {"tutorial_complete": True}
                            mock_relationships.return_value = {"diana": {"level": 25}}
                            mock_vip.return_value = False
                            mock_branches.return_value = ["main_story"]
                            
                            result = await story_engine.load_story_state(user_id)
                            
                            assert isinstance(result, StoryState)
                            assert result.user_id == user_id
                            assert result.current_chapter == "chapter_01"
                            assert result.completed_chapters == ["prologue"]
                            assert result.vip_content_available is False
                            assert result.unlocked_branches == ["main_story"]
    
    async def test_load_story_state_caching(self, story_engine):
        """Test story state caching mechanism."""
        user_id = 1
        
        with patch.object(story_engine, '_load_user_progress') as mock_progress:
            with patch.object(story_engine, '_load_user_flags') as mock_flags:
                with patch.object(story_engine, '_load_user_relationships') as mock_relationships:
                    with patch.object(story_engine, '_check_vip_status') as mock_vip:
                        with patch.object(story_engine, '_calculate_unlocked_branches') as mock_branches:
                            
                            # Setup mocks
                            mock_progress_obj = UserStoryProgress(user_id=user_id, current_chapter="chapter_01")
                            mock_progress.return_value = mock_progress_obj
                            mock_flags.return_value = {}
                            mock_relationships.return_value = {}
                            mock_vip.return_value = False
                            mock_branches.return_value = []
                            
                            # First call - should hit database
                            result1 = await story_engine.load_story_state(user_id)
                            assert story_engine._stats["cache_misses"] == 1
                            
                            # Second call - should hit cache
                            result2 = await story_engine.load_story_state(user_id)
                            assert story_engine._stats["cache_hits"] == 1
                            
                            # Results should be the same
                            assert result1.user_id == result2.user_id
                            assert result1.current_chapter == result2.current_chapter
    
    async def test_load_story_state_cache_expiration(self, story_engine):
        """Test story state cache expiration."""
        user_id = 1
        
        with patch.object(story_engine, '_load_user_progress') as mock_progress:
            with patch.object(story_engine, '_load_user_flags') as mock_flags:
                with patch.object(story_engine, '_load_user_relationships') as mock_relationships:
                    with patch.object(story_engine, '_check_vip_status') as mock_vip:
                        with patch.object(story_engine, '_calculate_unlocked_branches') as mock_branches:
                            
                            mock_progress_obj = UserStoryProgress(user_id=user_id, current_chapter="chapter_01")
                            mock_progress.return_value = mock_progress_obj
                            mock_flags.return_value = {}
                            mock_relationships.return_value = {}
                            mock_vip.return_value = False
                            mock_branches.return_value = []
                            
                            # First call
                            await story_engine.load_story_state(user_id)
                            
                            # Manually expire cache by setting old timestamp
                            cache_key = user_id
                            if cache_key in story_engine._user_state_cache:
                                state, _ = story_engine._user_state_cache[cache_key]
                                expired_time = datetime.now(timezone.utc) - timedelta(minutes=10)
                                story_engine._user_state_cache[cache_key] = (state, expired_time)
                            
                            # Second call should miss cache due to expiration
                            await story_engine.load_story_state(user_id)
                            assert story_engine._stats["cache_misses"] == 2
    
    async def test_load_story_state_error(self, story_engine):
        """Test story state loading error handling."""
        user_id = 1
        
        with patch.object(story_engine, '_load_user_progress') as mock_progress:
            mock_progress.side_effect = Exception("Database error")
            
            with pytest.raises(StoryEngineError, match="Cannot load story state"):
                await story_engine.load_story_state(user_id)

    # Generate Chapter Content Tests
    
    async def test_generate_chapter_content_success(self, story_engine):
        """Test successful chapter content generation."""
        user_id = 1
        chapter_id = "prologue"
        
        with patch.object(story_engine, '_load_chapter_data') as mock_chapter:
            with patch.object(story_engine, '_verify_chapter_access') as mock_verify:
                with patch.object(story_engine, '_personalize_content') as mock_personalize:
                    with patch.object(story_engine, '_personalize_decisions') as mock_decisions:
                        with patch.object(story_engine, '_get_chapter_characters') as mock_characters:
                            with patch.object(story_engine, '_load_personalization_profile') as mock_profile:
                                with patch.object(story_engine, '_get_moral_context') as mock_context:
                                    
                                    # Setup mocks
                                    mock_chapter_obj = StoryChapter(
                                        id=chapter_id,
                                        chapter_number=0,
                                        title="The Beginning",
                                        content="Chapter content",
                                        vip_required=False
                                    )
                                    mock_chapter.return_value = mock_chapter_obj
                                    mock_personalize.return_value = "Personalized content"
                                    mock_decisions.return_value = [{"id": "choice_1", "text": "Choose wisely"}]
                                    mock_characters.return_value = ["diana"]
                                    mock_profile.return_value = PersonalizationProfile(
                                        user_id=user_id, preferred_pacing="normal"
                                    )
                                    mock_context.return_value = {"dominant_alignment": "compassionate"}
                                    
                                    result = await story_engine.generate_chapter_content(
                                        user_id, chapter_id, personalize=True
                                    )
                                    
                                    assert isinstance(result, ChapterContent)
                                    assert result.chapter_id == chapter_id
                                    assert result.title == "The Beginning"
                                    assert result.content == "Personalized content"
                                    assert len(result.decisions) == 1
                                    assert result.character_appearances == ["diana"]
                                    assert result.personalization_data["dominant_alignment"] == "compassionate"
                                    assert story_engine._stats["personalization_applied"] == 1
    
    async def test_generate_chapter_content_no_personalization(self, story_engine):
        """Test chapter content generation without personalization."""
        user_id = 1
        chapter_id = "prologue"
        
        with patch.object(story_engine, '_load_chapter_data') as mock_chapter:
            with patch.object(story_engine, '_verify_chapter_access') as mock_verify:
                with patch.object(story_engine, '_load_chapter_decisions') as mock_decisions:
                    with patch.object(story_engine, '_get_chapter_characters') as mock_characters:
                        
                        mock_chapter_obj = StoryChapter(
                            id=chapter_id,
                            chapter_number=0,
                            title="The Beginning",
                            content="Original content",
                            vip_required=False
                        )
                        mock_chapter.return_value = mock_chapter_obj
                        mock_decisions.return_value = [{"id": "choice_1", "text": "Basic choice"}]
                        mock_characters.return_value = ["diana"]
                        
                        result = await story_engine.generate_chapter_content(
                            user_id, chapter_id, personalize=False
                        )
                        
                        assert result.content == "Original content"
                        assert len(result.personalization_data) == 0
                        assert story_engine._stats["personalization_applied"] == 0
    
    async def test_generate_chapter_content_vip_error(self, story_engine):
        """Test VIP required error for chapter content."""
        user_id = 1
        chapter_id = "vip_chapter"
        
        with patch.object(story_engine, '_load_chapter_data') as mock_chapter:
            with patch.object(story_engine, '_verify_chapter_access') as mock_verify:
                
                mock_chapter_obj = StoryChapter(
                    id=chapter_id,
                    chapter_number=5,
                    title="VIP Chapter",
                    content="VIP content",
                    vip_required=True
                )
                mock_chapter.return_value = mock_chapter_obj
                mock_verify.side_effect = VIPRequiredError("VIP required")
                
                with pytest.raises(VIPRequiredError):
                    await story_engine.generate_chapter_content(user_id, chapter_id)
    
    async def test_generate_chapter_content_chapter_not_found(self, story_engine):
        """Test chapter not found error."""
        user_id = 1
        chapter_id = "nonexistent_chapter"
        
        with patch.object(story_engine, '_load_chapter_data') as mock_chapter:
            mock_chapter.side_effect = ChapterNotFoundError("Chapter not found")
            
            with pytest.raises(ChapterNotFoundError):
                await story_engine.generate_chapter_content(user_id, chapter_id)

    # Calculate Available Branches Tests
    
    async def test_calculate_available_branches_success(self, story_engine):
        """Test successful branch calculation."""
        user_id = 1
        
        with patch.object(story_engine, 'load_story_state') as mock_state:
            with patch.object(story_engine, '_load_branch_definitions') as mock_branches:
                with patch.object(story_engine, '_evaluate_branch_requirements') as mock_evaluate:
                    
                    mock_story_state = StoryState(
                        user_id=user_id,
                        current_chapter="chapter_02",
                        completed_chapters=["prologue", "chapter_01"],
                        story_flags={"moral_path": True},
                        character_relationships={},
                        unlocked_branches=[],
                        vip_content_available=False,
                        moral_alignment={"compassionate": 75}
                    )
                    mock_state.return_value = mock_story_state
                    
                    mock_branches.return_value = [
                        ("hero_path", {
                            "title": "Hero's Journey",
                            "description": "Path of righteousness",
                            "difficulty": "hard",
                            "chapter_count": 5,
                            "vip_required": True,
                            "main_characters": ["diana", "alex"]
                        }),
                        ("romance_path", {
                            "title": "Love's Journey",
                            "description": "Path of heart",
                            "difficulty": "normal",
                            "chapter_count": 3,
                            "vip_required": False,
                            "main_characters": ["alex"]
                        })
                    ]
                    
                    mock_evaluate.side_effect = [True, False]  # First branch available, second not
                    
                    result = await story_engine.calculate_available_branches(user_id)
                    
                    assert len(result) == 1
                    branch = result[0]
                    assert branch["branch_id"] == "hero_path"
                    assert branch["title"] == "Hero's Journey"
                    assert branch["difficulty"] == "hard"
                    assert branch["estimated_chapters"] == 5
                    assert branch["vip_required"] is True
                    assert branch["character_focus"] == ["diana", "alex"]
    
    async def test_calculate_available_branches_no_branches(self, story_engine):
        """Test branch calculation when no branches are available."""
        user_id = 1
        
        with patch.object(story_engine, 'load_story_state') as mock_state:
            with patch.object(story_engine, '_load_branch_definitions') as mock_branches:
                with patch.object(story_engine, '_evaluate_branch_requirements') as mock_evaluate:
                    
                    mock_state.return_value = Mock()
                    mock_branches.return_value = [
                        ("hero_path", {"title": "Hero's Journey"}),
                        ("villain_path", {"title": "Dark Path"})
                    ]
                    mock_evaluate.return_value = False  # No branches available
                    
                    result = await story_engine.calculate_available_branches(user_id)
                    
                    assert len(result) == 0
    
    async def test_calculate_available_branches_error(self, story_engine):
        """Test branch calculation error handling."""
        user_id = 1
        
        with patch.object(story_engine, 'load_story_state') as mock_state:
            mock_state.side_effect = Exception("State loading error")
            
            # Should return empty list on error, not raise exception
            result = await story_engine.calculate_available_branches(user_id)
            assert result == []

    # Unlock Next Content Tests
    
    async def test_unlock_next_content_success(self, story_engine):
        """Test successful content unlock calculation."""
        user_id = 1
        current_progress = {
            "completed_chapters": ["prologue", "chapter_01"],
            "story_flags": {"diana_trust": 75},
            "character_relationships": {"diana": {"level": 80}},
            "moral_alignment": {"compassionate": 90}
        }
        
        with patch.object(story_engine, '_check_chapter_unlocks') as mock_chapters:
            with patch.object(story_engine, '_check_character_unlocks') as mock_characters:
                with patch.object(story_engine, '_check_vip_unlocks') as mock_vip:
                    with patch.object(story_engine, '_check_side_quest_unlocks') as mock_quests:
                        
                        # Setup mock returns
                        chapter_unlocks = [
                            UnlockedContent(
                                content_id="chapter_03_heroic",
                                content_type=ContentType.MAIN_STORY,
                                title="Heroic Chapter",
                                description="Unlocked by moral alignment",
                                unlock_reason="moral_progress"
                            )
                        ]
                        character_unlocks = [
                            UnlockedContent(
                                content_id="diana_deep_talk",
                                content_type=ContentType.CHARACTER_INTERACTION,
                                title="Heart to Heart with Diana",
                                description="Deep conversation unlocked",
                                unlock_reason="high_relationship"
                            )
                        ]
                        vip_unlocks = []
                        quest_unlocks = []
                        
                        mock_chapters.return_value = chapter_unlocks
                        mock_characters.return_value = character_unlocks
                        mock_vip.return_value = vip_unlocks
                        mock_quests.return_value = quest_unlocks
                        
                        result = await story_engine.unlock_next_content(user_id, current_progress)
                        
                        assert len(result) == 2
                        assert result[0].content_id == "chapter_03_heroic"
                        assert result[1].content_id == "diana_deep_talk"
                        
                        # Verify all unlock methods were called
                        mock_chapters.assert_called_once_with(user_id, current_progress)
                        mock_characters.assert_called_once_with(user_id, current_progress)
                        mock_vip.assert_called_once_with(user_id, current_progress)
                        mock_quests.assert_called_once_with(user_id, current_progress)
    
    async def test_unlock_next_content_no_unlocks(self, story_engine):
        """Test content unlock with no new unlocks."""
        user_id = 1
        current_progress = {"completed_chapters": []}
        
        with patch.object(story_engine, '_check_chapter_unlocks', return_value=[]):
            with patch.object(story_engine, '_check_character_unlocks', return_value=[]):
                with patch.object(story_engine, '_check_vip_unlocks', return_value=[]):
                    with patch.object(story_engine, '_check_side_quest_unlocks', return_value=[]):
                        
                        result = await story_engine.unlock_next_content(user_id, current_progress)
                        assert len(result) == 0
    
    async def test_unlock_next_content_error(self, story_engine):
        """Test content unlock error handling."""
        user_id = 1
        current_progress = {}
        
        with patch.object(story_engine, '_check_chapter_unlocks') as mock_chapters:
            mock_chapters.side_effect = Exception("Unlock check error")
            
            # Should return empty list on error
            result = await story_engine.unlock_next_content(user_id, current_progress)
            assert result == []

    # Validate Story Consistency Tests
    
    async def test_validate_story_consistency_enabled_success(self, story_engine):
        """Test successful story consistency validation."""
        user_id = 1
        proposed_state = {
            "current_chapter": "chapter_02",
            "story_flags": {"tutorial_complete": True},
            "character_relationships": {"diana": {"level": 30}},
            "moral_alignment": {"compassionate": 60}
        }
        
        with patch.object(story_engine, 'load_story_state') as mock_state:
            with patch.object(story_engine, '_validate_chapter_progression') as mock_chapter:
                with patch.object(story_engine, '_validate_story_flags') as mock_flags:
                    with patch.object(story_engine, '_validate_relationships') as mock_relations:
                        with patch.object(story_engine, '_validate_moral_alignment') as mock_moral:
                            
                            mock_state.return_value = Mock()
                            mock_chapter.return_value = (True, None)
                            mock_flags.return_value = (True, None)
                            mock_relations.return_value = (True, None)
                            mock_moral.return_value = (True, None)
                            
                            is_valid, error = await story_engine.validate_story_consistency(
                                user_id, proposed_state
                            )
                            
                            assert is_valid is True
                            assert error is None
                            assert story_engine._stats["consistency_checks"] == 1
    
    async def test_validate_story_consistency_chapter_error(self, story_engine):
        """Test story consistency validation with chapter error."""
        user_id = 1
        proposed_state = {"current_chapter": "invalid_chapter"}
        
        with patch.object(story_engine, 'load_story_state') as mock_state:
            with patch.object(story_engine, '_validate_chapter_progression') as mock_chapter:
                
                mock_state.return_value = Mock()
                mock_chapter.return_value = (False, "Invalid chapter progression")
                
                is_valid, error = await story_engine.validate_story_consistency(
                    user_id, proposed_state
                )
                
                assert is_valid is False
                assert "Chapter progression error" in error
    
    async def test_validate_story_consistency_flags_error(self, story_engine):
        """Test story consistency validation with flags error."""
        user_id = 1
        proposed_state = {"story_flags": {"invalid_flag": True}}
        
        with patch.object(story_engine, 'load_story_state') as mock_state:
            with patch.object(story_engine, '_validate_story_flags') as mock_flags:
                
                mock_state.return_value = Mock()
                mock_flags.return_value = (False, "Invalid flag combination")
                
                is_valid, error = await story_engine.validate_story_consistency(
                    user_id, proposed_state
                )
                
                assert is_valid is False
                assert "Story flags error" in error
    
    async def test_validate_story_consistency_relationships_error(self, story_engine):
        """Test story consistency validation with relationship error."""
        user_id = 1
        proposed_state = {"character_relationships": {"diana": {"level": -200}}}
        
        with patch.object(story_engine, 'load_story_state') as mock_state:
            with patch.object(story_engine, '_validate_relationships') as mock_relations:
                
                mock_state.return_value = Mock()
                mock_relations.return_value = (False, "Invalid relationship level")
                
                is_valid, error = await story_engine.validate_story_consistency(
                    user_id, proposed_state
                )
                
                assert is_valid is False
                assert "Relationship consistency error" in error
    
    async def test_validate_story_consistency_moral_error(self, story_engine):
        """Test story consistency validation with moral alignment error."""
        user_id = 1
        proposed_state = {"moral_alignment": {"compassionate": 150}}
        
        with patch.object(story_engine, 'load_story_state') as mock_state:
            with patch.object(story_engine, '_validate_moral_alignment') as mock_moral:
                
                mock_state.return_value = Mock()
                mock_moral.return_value = (False, "Invalid moral value")
                
                is_valid, error = await story_engine.validate_story_consistency(
                    user_id, proposed_state
                )
                
                assert is_valid is False
                assert "Moral alignment error" in error
    
    async def test_validate_story_consistency_disabled(self, story_engine_no_consistency):
        """Test story consistency validation when disabled."""
        user_id = 1
        proposed_state = {"current_chapter": "any_chapter"}
        
        is_valid, error = await story_engine_no_consistency.validate_story_consistency(
            user_id, proposed_state
        )
        
        assert is_valid is True
        assert error is None
    
    async def test_validate_story_consistency_exception(self, story_engine):
        """Test story consistency validation error handling."""
        user_id = 1
        proposed_state = {"current_chapter": "test"}
        
        with patch.object(story_engine, 'load_story_state') as mock_state:
            mock_state.side_effect = Exception("Validation error")
            
            is_valid, error = await story_engine.validate_story_consistency(
                user_id, proposed_state
            )
            
            assert is_valid is False
            assert "Validation error" in error

    # Private Helper Method Tests
    
    async def test_load_chapter_data_caching(self, story_engine):
        """Test chapter data loading and caching."""
        chapter_id = "prologue"
        
        # First call - should load from "database"
        result1 = await story_engine._load_chapter_data(chapter_id)
        assert isinstance(result1, StoryChapter)
        assert result1.id == chapter_id
        assert story_engine._stats["chapters_loaded"] == 1
        
        # Second call - should hit cache
        result2 = await story_engine._load_chapter_data(chapter_id)
        assert result2.id == chapter_id
        assert story_engine._stats["chapters_loaded"] == 1  # Should not increment
    
    async def test_load_chapter_data_not_found(self, story_engine):
        """Test loading non-existent chapter."""
        chapter_id = "nonexistent_chapter"
        
        with pytest.raises(ChapterNotFoundError, match="Chapter not found"):
            await story_engine._load_chapter_data(chapter_id)
    
    async def test_verify_chapter_access_vip_required(self, story_engine):
        """Test chapter access verification for VIP content."""
        user_id = 1
        chapter = StoryChapter(
            id="vip_chapter",
            chapter_number=10,
            title="VIP Chapter",
            content="VIP content",
            vip_required=True
        )
        
        with patch.object(story_engine, '_check_vip_status', return_value=False):
            with pytest.raises(VIPRequiredError, match="requires VIP access"):
                await story_engine._verify_chapter_access(user_id, chapter)
    
    async def test_verify_chapter_access_unlock_conditions_not_met(self, story_engine):
        """Test chapter access verification with unmet unlock conditions."""
        user_id = 1
        chapter = StoryChapter(
            id="locked_chapter",
            chapter_number=5,
            title="Locked Chapter",
            content="Locked content",
            unlock_conditions={"completed_chapters": ["chapter_04"]},
            vip_required=False
        )
        
        with patch.object(story_engine, 'load_story_state') as mock_state:
            with patch.object(story_engine, '_evaluate_unlock_conditions', return_value=False):
                
                mock_state.return_value = Mock()
                
                with pytest.raises(StoryEngineError, match="unlock conditions not met"):
                    await story_engine._verify_chapter_access(user_id, chapter)
    
    async def test_personalize_content_fast_pacing(self, story_engine):
        """Test content personalization with fast pacing preference."""
        user_id = 1
        chapter = StoryChapter(
            id="test_chapter",
            chapter_number=1,
            title="Test",
            content="This is a long chapter with detailed descriptions. It goes on for a while."
        )
        
        with patch.object(story_engine, '_load_personalization_profile') as mock_profile:
            with patch.object(story_engine, 'load_story_state') as mock_state:
                
                mock_profile.return_value = PersonalizationProfile(
                    user_id=user_id,
                    preferred_pacing="fast"
                )
                mock_state.return_value = Mock()
                mock_state.return_value.character_relationships = {}
                mock_state.return_value.moral_alignment = {}
                
                result = await story_engine._personalize_content(user_id, chapter)
                
                # Should compress content for fast pacing
                assert len(result) <= len(chapter.content)
    
    async def test_personalize_content_slow_pacing(self, story_engine):
        """Test content personalization with slow pacing preference."""
        user_id = 1
        chapter = StoryChapter(
            id="test_chapter",
            chapter_number=1,
            title="Test",
            content="Short content."
        )
        
        with patch.object(story_engine, '_load_personalization_profile') as mock_profile:
            with patch.object(story_engine, 'load_story_state') as mock_state:
                
                mock_profile.return_value = PersonalizationProfile(
                    user_id=user_id,
                    preferred_pacing="slow"
                )
                mock_state.return_value = Mock()
                mock_state.return_value.character_relationships = {}
                mock_state.return_value.moral_alignment = {}
                
                result = await story_engine._personalize_content(user_id, chapter)
                
                # Should expand content for slow pacing
                assert len(result) > len(chapter.content)
    
    async def test_personalize_decisions_complexity_filtering(self, story_engine):
        """Test decision personalization with complexity filtering."""
        user_id = 1
        chapter_id = "test_chapter"
        
        with patch.object(story_engine, '_load_chapter_decisions') as mock_decisions:
            with patch.object(story_engine, '_load_personalization_profile') as mock_profile:
                with patch.object(story_engine, 'load_story_state') as mock_state:
                    
                    base_decisions = [
                        {"id": "simple", "text": "Simple choice", "complexity": "simple"},
                        {"id": "normal", "text": "Normal choice", "complexity": "normal"},
                        {"id": "complex", "text": "Complex choice", "complexity": "complex"}
                    ]
                    mock_decisions.return_value = base_decisions
                    
                    mock_profile.return_value = PersonalizationProfile(
                        user_id=user_id,
                        complexity_level="simple"
                    )
                    mock_state.return_value = Mock()
                    mock_state.return_value.character_relationships = {}
                    
                    result = await story_engine._personalize_decisions(user_id, chapter_id)
                    
                    # Should filter out complex decisions for simple preference
                    decision_ids = [d["id"] for d in result]
                    assert "simple" in decision_ids
                    assert "normal" in decision_ids
                    assert "complex" not in decision_ids
    
    def test_evaluate_unlock_conditions_completed_chapters(self, story_engine):
        """Test unlock condition evaluation for completed chapters."""
        story_state = StoryState(
            user_id=1,
            current_chapter="chapter_03",
            completed_chapters=["prologue", "chapter_01", "chapter_02"],
            story_flags={},
            character_relationships={},
            unlocked_branches=[],
            vip_content_available=False,
            moral_alignment={}
        )
        
        # Should pass - all required chapters completed
        conditions1 = {"completed_chapters": ["prologue", "chapter_01"]}
        result1 = asyncio.run(story_engine._evaluate_unlock_conditions(story_state, conditions1))
        assert result1 is True
        
        # Should fail - missing required chapter
        conditions2 = {"completed_chapters": ["chapter_04"]}
        result2 = asyncio.run(story_engine._evaluate_unlock_conditions(story_state, conditions2))
        assert result2 is False
    
    def test_evaluate_unlock_conditions_story_flags(self, story_engine):
        """Test unlock condition evaluation for story flags."""
        story_state = StoryState(
            user_id=1,
            current_chapter="chapter_02",
            completed_chapters=[],
            story_flags={"hero_path": True, "villain_defeated": False},
            character_relationships={},
            unlocked_branches=[],
            vip_content_available=False,
            moral_alignment={}
        )
        
        # Should pass - flag matches
        conditions1 = {"story_flags": {"hero_path": True}}
        result1 = asyncio.run(story_engine._evaluate_unlock_conditions(story_state, conditions1))
        assert result1 is True
        
        # Should fail - flag doesn't match
        conditions2 = {"story_flags": {"villain_defeated": True}}
        result2 = asyncio.run(story_engine._evaluate_unlock_conditions(story_state, conditions2))
        assert result2 is False
        
        # Should fail - flag doesn't exist
        conditions3 = {"story_flags": {"nonexistent_flag": True}}
        result3 = asyncio.run(story_engine._evaluate_unlock_conditions(story_state, conditions3))
        assert result3 is False
    
    def test_compress_content_pacing(self, story_engine):
        """Test content compression for fast pacing."""
        content = "This is a sentence. This is another sentence. And one more sentence."
        result = story_engine._compress_content_pacing(content)
        # Should compress by reducing spaces
        assert len(result) <= len(content)
    
    def test_expand_content_detail(self, story_engine):
        """Test content expansion for slow pacing."""
        content = "This is short content."
        result = story_engine._expand_content_detail(content)
        # Should add detail
        assert len(result) > len(content)
        assert "moment lingers" in result
    
    def test_add_moral_context(self, story_engine):
        """Test moral context addition to content."""
        content = "Original content"
        moral_alignment = {"compassionate": 75, "pragmatic": 25}
        
        result = story_engine._add_moral_context(content, moral_alignment)
        
        # Should add moral context for dominant trait
        assert len(result) > len(content)
        assert "compassionate" in result.lower()
    
    def test_adapt_decision_style(self, story_engine):
        """Test decision text adaptation for different styles."""
        decision_text = "Make your choice"
        
        # Test action style
        result_action = story_engine._adapt_decision_style(decision_text, "action")
        assert "⚔️" in result_action
        assert "Bold action" in result_action
        
        # Test romance style
        result_romance = story_engine._adapt_decision_style(decision_text, "romance")
        assert "💕" in result_romance
        assert "Heart-driven" in result_romance
        
        # Test mystery style
        result_mystery = story_engine._adapt_decision_style(decision_text, "mystery")
        assert "🔍" in result_mystery
        assert "Investigate" in result_mystery
        
        # Test balanced (no change)
        result_balanced = story_engine._adapt_decision_style(decision_text, "balanced")
        assert result_balanced == decision_text

    # Performance and Edge Case Tests
    
    async def test_concurrent_chapter_loading(self, story_engine):
        """Test concurrent chapter loading with caching."""
        chapter_id = "prologue"
        
        # Load same chapter concurrently
        tasks = [story_engine._load_chapter_data(chapter_id) for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        # All results should be the same chapter
        for result in results:
            assert result.id == chapter_id
        
        # Should only load once due to caching
        assert story_engine._stats["chapters_loaded"] == 1
    
    async def test_cache_lock_behavior(self, story_engine):
        """Test cache lock prevents race conditions."""
        user_id = 1
        
        with patch.object(story_engine, '_load_user_progress') as mock_progress:
            with patch.object(story_engine, '_load_user_flags', return_value={}):
                with patch.object(story_engine, '_load_user_relationships', return_value={}):
                    with patch.object(story_engine, '_check_vip_status', return_value=False):
                        with patch.object(story_engine, '_calculate_unlocked_branches', return_value=[]):
                            
                            mock_progress.return_value = UserStoryProgress(
                                user_id=user_id, current_chapter="chapter_01"
                            )
                            
                            # Run concurrent loads
                            tasks = [story_engine.load_story_state(user_id) for _ in range(5)]
                            results = await asyncio.gather(*tasks)
                            
                            # All should succeed
                            for result in results:
                                assert result.user_id == user_id
    
    async def test_large_moral_alignment_values(self, story_engine):
        """Test handling of edge case moral alignment values."""
        content = "Test content"
        moral_alignment = {"extreme_trait": 9999}
        
        # Should handle extreme values gracefully
        result = story_engine._add_moral_context(content, moral_alignment)
        assert isinstance(result, str)
        assert len(result) >= len(content)
    
    async def test_empty_personalization_profile(self, story_engine):
        """Test personalization with minimal profile data."""
        user_id = 1
        chapter = StoryChapter(
            id="test",
            chapter_number=1,
            title="Test",
            content="Test content"
        )
        
        with patch.object(story_engine, '_load_personalization_profile') as mock_profile:
            with patch.object(story_engine, 'load_story_state') as mock_state:
                
                # Minimal profile
                mock_profile.return_value = PersonalizationProfile(user_id=user_id)
                mock_state.return_value = Mock()
                mock_state.return_value.character_relationships = {}
                mock_state.return_value.moral_alignment = {}
                
                # Should not fail with minimal profile
                result = await story_engine._personalize_content(user_id, chapter)
                assert isinstance(result, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])