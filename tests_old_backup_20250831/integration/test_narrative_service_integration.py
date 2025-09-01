import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.narrative.services.narrative_service import UserNarrativeService, NarrativeContentService
from src.services.narrative.models.narrative_models import UserNarrativeState, UserDecisionLog, NarrativeScene, NarrativeDecision


class TestUserNarrativeServiceIntegration:
    """Integration tests for the UserNarrativeService."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return MagicMock(spec=AsyncSession)

    @pytest.fixture
    def user_narrative_service(self, mock_db_session):
        """Create a user narrative service with a mock database session."""
        return UserNarrativeService(mock_db_session)

    @pytest.mark.asyncio
    async def test_create_user_state_new_user(self, user_narrative_service, mock_db_session):
        """Test creating a narrative state for a new user."""
        # Setup
        user_id = "user_123"
        initial_scene_id = "scene_001"
        
        # Mock the get_user_state to return None (user doesn't exist)
        mock_execute_result = MagicMock()
        mock_execute_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_execute_result
        
        # Mock the add/commit/refresh methods
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        # Execute
        result = await user_narrative_service.create_user_state(user_id, initial_scene_id)

        # Verify
        assert isinstance(result, UserNarrativeState)
        assert result.user_id == user_id
        assert result.current_scene_id == initial_scene_id
        assert result.emotional_variables == {}
        
        # Verify database operations
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_state_existing_user(self, user_narrative_service, mock_db_session):
        """Test creating a narrative state for an existing user."""
        # Setup
        user_id = "user_123"
        initial_scene_id = "scene_001"
        
        # Create an existing user state
        existing_state = UserNarrativeState(
            user_id=user_id,
            current_scene_id="scene_002",
            emotional_variables={"anxiety": 0.5}
        )
        
        # Mock the get_user_state to return the existing state
        mock_execute_result = MagicMock()
        mock_execute_result.scalar_one_or_none.return_value = existing_state
        mock_db_session.execute.return_value = mock_execute_result

        # Execute
        result = await user_narrative_service.create_user_state(user_id, initial_scene_id)

        # Verify
        assert result == existing_state
        # Should not have called add/commit/refresh for existing user
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_not_called()
        mock_db_session.refresh.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_user_state_exists(self, user_narrative_service, mock_db_session):
        """Test getting a user's narrative state when it exists."""
        # Setup
        user_id = "user_123"
        expected_state = UserNarrativeState(
            user_id=user_id,
            current_scene_id="scene_002",
            emotional_variables={"anxiety": 0.5}
        )
        
        # Mock the database response
        mock_execute_result = MagicMock()
        mock_execute_result.scalar_one_or_none.return_value = expected_state
        mock_db_session.execute.return_value = mock_execute_result

        # Execute
        result = await user_narrative_service.get_user_state(user_id)

        # Verify
        assert result == expected_state
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_state_not_exists(self, user_narrative_service, mock_db_session):
        """Test getting a user's narrative state when it doesn't exist."""
        # Setup
        user_id = "user_123"
        
        # Mock the database response
        mock_execute_result = MagicMock()
        mock_execute_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_execute_result

        # Execute
        result = await user_narrative_service.get_user_state(user_id)

        # Verify
        assert result is None
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_state_existing_user(self, user_narrative_service, mock_db_session):
        """Test updating a user's narrative state."""
        # Setup
        user_id = "user_123"
        scene_id = "scene_003"
        emotional_variables = {"anxiety": 0.3, "hope": 0.7}
        
        # Create an existing user state
        existing_state = UserNarrativeState(
            user_id=user_id,
            current_scene_id="scene_002",
            emotional_variables={"anxiety": 0.5}
        )
        
        # Mock the get_user_state to return the existing state
        mock_execute_result = MagicMock()
        mock_execute_result.scalar_one_or_none.return_value = existing_state
        mock_db_session.execute.return_value = mock_execute_result
        
        # Mock commit and refresh
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        # Execute
        result = await user_narrative_service.update_user_state(user_id, scene_id, emotional_variables)

        # Verify
        assert isinstance(result, UserNarrativeState)
        assert result.user_id == user_id
        assert result.current_scene_id == scene_id
        assert result.emotional_variables == emotional_variables
        
        # Verify the existing state was updated
        assert existing_state.current_scene_id == scene_id
        assert existing_state.emotional_variables == emotional_variables
        
        # Verify database operations
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once_with(existing_state)

    @pytest.mark.asyncio
    async def test_update_user_state_new_user(self, user_narrative_service, mock_db_session):
        """Test updating a user's narrative state when it doesn't exist."""
        # Setup
        user_id = "user_123"
        scene_id = "scene_001"
        emotional_variables = {"anxiety": 0.1}
        
        # Mock the get_user_state to return None (user doesn't exist)
        mock_execute_result1 = MagicMock()
        mock_execute_result1.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_execute_result1
        
        # Mock the create_user_state process
        new_state = UserNarrativeState(
            user_id=user_id,
            current_scene_id=scene_id,
            emotional_variables=emotional_variables
        )
        
        mock_execute_result2 = MagicMock()
        mock_execute_result2.scalar_one_or_none.return_value = new_state
        
        # Mock add/commit/refresh
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        # Execute
        result = await user_narrative_service.update_user_state(user_id, scene_id, emotional_variables)

        # Verify
        assert isinstance(result, UserNarrativeState)
        assert result.user_id == user_id
        assert result.current_scene_id == scene_id
        assert result.emotional_variables == emotional_variables
        
        # Verify database operations
        mock_db_session.add.assert_called_once()
        assert mock_db_session.commit.call_count == 2  # Once for create, once for update
        assert mock_db_session.refresh.call_count == 2  # Once for create, once for update

    @pytest.mark.asyncio
    async def test_log_user_decision(self, user_narrative_service, mock_db_session):
        """Test logging a user's decision."""
        # Setup
        user_id = "user_123"
        decision_id = "decision_001"
        scene_id = "scene_001"
        
        # Create expected decision log
        expected_log = UserDecisionLog(
            user_id=user_id,
            decision_id=decision_id,
            scene_id=scene_id
        )
        
        # Mock add/commit/refresh
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        # Execute
        result = await user_narrative_service.log_user_decision(user_id, decision_id, scene_id)

        # Verify
        assert isinstance(result, UserDecisionLog)
        assert result.user_id == user_id
        assert result.decision_id == decision_id
        assert result.scene_id == scene_id
        
        # Verify database operations
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_decision_history(self, user_narrative_service, mock_db_session):
        """Test getting a user's decision history."""
        # Setup
        user_id = "user_123"
        
        # Create decision history
        decision_history = [
            UserDecisionLog(user_id=user_id, decision_id="decision_001", scene_id="scene_001"),
            UserDecisionLog(user_id=user_id, decision_id="decision_002", scene_id="scene_002"),
            UserDecisionLog(user_id=user_id, decision_id="decision_003", scene_id="scene_003")
        ]
        
        # Mock the database response
        mock_execute_result = MagicMock()
        mock_execute_result.scalars().all.return_value = decision_history
        mock_db_session.execute.return_value = mock_execute_result

        # Execute
        result = await user_narrative_service.get_user_decision_history(user_id)

        # Verify
        assert result == decision_history
        assert len(result) == 3
        assert all(isinstance(log, UserDecisionLog) for log in result)
        assert all(log.user_id == user_id for log in result)
        
        mock_db_session.execute.assert_called_once()


class TestNarrativeContentServiceIntegration:
    """Integration tests for the NarrativeContentService."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return MagicMock(spec=AsyncSession)

    @pytest.fixture
    def narrative_content_service(self, mock_db_session):
        """Create a narrative content service with a mock database session."""
        return NarrativeContentService(mock_db_session)

    @pytest.mark.asyncio
    async def test_get_scene_with_choices_exists(self, narrative_content_service, mock_db_session):
        """Test getting a scene with its choices when they exist."""
        # Setup
        scene_id = "scene_001"
        
        # Create scene and decisions
        scene = NarrativeScene(
            id=scene_id,
            title="The Beginning",
            content="You wake up in a strange place...",
            is_active=True
        )
        
        decisions = [
            NarrativeDecision(
                id="decision_001",
                scene_id=scene_id,
                text="Investigate the room",
                next_scene_id="scene_002",
                sort_order=1
            ),
            NarrativeDecision(
                id="decision_002",
                scene_id=scene_id,
                text="Call out for help",
                next_scene_id="scene_003",
                sort_order=2
            )
        ]
        
        # Mock database responses
        # First call for scene
        mock_scene_result = MagicMock()
        mock_scene_result.scalar_one_or_none.return_value = scene
        
        # Second call for decisions
        mock_decisions_result = MagicMock()
        mock_decisions_result.scalars().all.return_value = decisions
        
        # Configure execute to return different results for different calls
        mock_db_session.execute.side_effect = [mock_scene_result, mock_decisions_result]

        # Execute
        result = await narrative_content_service.get_scene_with_choices(scene_id)

        # Verify
        assert result is not None
        assert "scene" in result
        assert "decisions" in result
        assert result["scene"] == scene
        assert result["decisions"] == decisions

    @pytest.mark.asyncio
    async def test_get_scene_with_choices_scene_not_found(self, narrative_content_service, mock_db_session):
        """Test getting a scene with its choices when the scene doesn't exist."""
        # Setup
        scene_id = "nonexistent_scene"
        
        # Mock database response for scene (not found)
        mock_scene_result = MagicMock()
        mock_scene_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_scene_result

        # Execute
        result = await narrative_content_service.get_scene_with_choices(scene_id)

        # Verify
        assert result is None
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_narrative_structure_empty(self, narrative_content_service, mock_db_session):
        """Test validating narrative structure with no scenes or decisions."""
        # Setup
        # Mock database responses for empty scenes and decisions
        mock_scenes_result = MagicMock()
        mock_scenes_result.scalars().all.return_value = []
        
        mock_decisions_result = MagicMock()
        mock_decisions_result.scalars().all.return_value = []
        
        # Configure execute to return different results for different calls
        mock_db_session.execute.side_effect = [mock_scenes_result, mock_decisions_result]

        # Execute
        result = await narrative_content_service.validate_narrative_structure()

        # Verify
        assert isinstance(result, dict)
        assert result["is_valid"] is True
        assert result["orphaned_scenes"] == []
        assert result["dead_end_decisions"] == []

    @pytest.mark.asyncio
    async def test_validate_narrative_structure_with_issues(self, narrative_content_service, mock_db_session):
        """Test validating narrative structure with issues."""
        # Setup
        # Create scenes and decisions with issues
        scenes = [
            NarrativeScene(id="scene_001", title="Scene 1", content="Content 1", is_active=True),
            NarrativeScene(id="scene_002", title="Scene 2", content="Content 2", is_active=True),
            NarrativeScene(id="scene_003", title="Scene 3", content="Content 3", is_active=True)
        ]
        
        # Decision that leads to a non-existent scene (orphaned)
        # Decision without next scene (dead end)
        decisions = [
            NarrativeDecision(id="decision_001", scene_id="scene_001", text="Decision 1", next_scene_id="scene_999", sort_order=1),
            NarrativeDecision(id="decision_002", scene_id="scene_002", text="Decision 2", next_scene_id=None, sort_order=1)
        ]
        
        # Mock database responses
        mock_scenes_result = MagicMock()
        mock_scenes_result.scalars().all.return_value = scenes
        
        mock_decisions_result = MagicMock()
        mock_decisions_result.scalars().all.return_value = decisions
        
        # Configure execute to return different results for different calls
        mock_db_session.execute.side_effect = [mock_scenes_result, mock_decisions_result]

        # Execute
        result = await narrative_content_service.validate_narrative_structure()

        # Verify
        assert isinstance(result, dict)
        assert result["is_valid"] is False  # Should be invalid due to orphaned scenes
        assert "scene_003" in result["orphaned_scenes"]  # scene_003 is not referenced by any decision
        assert "decision_002" in result["dead_end_decisions"]  # decision_002 has no next scene


if __name__ == "__main__":
    pytest.main([__file__])