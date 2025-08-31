import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.services.narrative.engines.narrative_engine import NarrativeEngine
from src.services.narrative.models.narrative_models import (
    UserNarrativeState,
    UserDecisionLog,
    NarrativeScene,
    NarrativeDecision
)

@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return AsyncMock()

@pytest.fixture
def narrative_engine(mock_db_session):
    """Create a NarrativeEngine instance with a mock database session."""
    return NarrativeEngine(mock_db_session)

@pytest.mark.asyncio
async def test_get_user_state(narrative_engine, mock_db_session):
    """Test getting a user's narrative state."""
    # Setup
    user_id = "test_user_123"
    user_state = UserNarrativeState(
        user_id=user_id,
        current_scene_id=str(uuid.uuid4()),
        emotional_variables={"affinity_diana": 50}
    )
    
    # Mock the database response
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user_state
    mock_db_session.execute.return_value = mock_result
    
    # Execute
    result = await narrative_engine.get_user_state(user_id)
    
    # Assert
    assert result == user_state
    mock_db_session.execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_scene(narrative_engine, mock_db_session):
    """Test getting a scene by ID."""
    # Setup
    scene_id = str(uuid.uuid4())
    scene = NarrativeScene(
        id=uuid.UUID(scene_id),
        chapter_id=uuid.uuid4(),
        title="Test Scene",
        dialogue="This is a test scene.",
        character_speaker="Diana",
        sort_order=1
    )
    
    # Mock the database response
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = scene
    mock_db_session.execute.return_value = mock_result
    
    # Execute
    result = await narrative_engine.get_scene(scene_id)
    
    # Assert
    assert result == scene
    mock_db_session.execute.assert_called_once()

@pytest.mark.asyncio
async def test_evaluate_simple_conditions_pass(narrative_engine):
    """Test evaluating simple conditions that pass."""
    # Setup
    conditions = {"affinity_diana_gt": 50}
    user_state = UserNarrativeState(
        user_id="test_user",
        current_scene_id=str(uuid.uuid4()),
        emotional_variables={"affinity_diana": 75}
    )
    user_history = []
    
    # Execute
    result = await narrative_engine.evaluate_conditions(conditions, user_state, user_history)
    
    # Assert
    assert result is True

@pytest.mark.asyncio
async def test_evaluate_simple_conditions_fail(narrative_engine):
    """Test evaluating simple conditions that fail."""
    # Setup
    conditions = {"affinity_diana_gt": 50}
    user_state = UserNarrativeState(
        user_id="test_user",
        current_scene_id=str(uuid.uuid4()),
        emotional_variables={"affinity_diana": 25}
    )
    user_history = []
    
    # Execute
    result = await narrative_engine.evaluate_conditions(conditions, user_state, user_history)
    
    # Assert
    assert result is False

@pytest.mark.asyncio
async def test_apply_emotional_impact(narrative_engine):
    """Test applying emotional variable impacts."""
    # Setup
    current_emotions = {"affinity_diana": 50, "paradox_level": 10}
    impact = {"affinity_diana": 25, "paradox_level": -5, "new_variable": 15}
    
    # Execute
    result = await narrative_engine.apply_emotional_impact(current_emotions, impact)
    
    # Assert
    expected = {"affinity_diana": 75, "paradox_level": 5, "new_variable": 15}
    assert result == expected