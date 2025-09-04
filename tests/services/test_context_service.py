import pytest
from src.services.context_service import ContextService
from src.domain.models import UserProfile, UserMood, UserArchetype


@pytest.fixture
def context_service():
    return ContextService()


@pytest.fixture
def user_profile():
    return UserProfile(user_id=1, mood=UserMood.NEUTRAL, archetype=UserArchetype.EXPLORER, engagement_score=0)


@pytest.mark.asyncio
async def test_detect_user_mood(context_service: ContextService, user_profile: UserProfile):
    """
    Test that detect_user_mood updates the profile's mood.
    """
    initial_mood = user_profile.mood
    new_mood = await context_service.detect_user_mood(user_profile)

    assert isinstance(new_mood, UserMood)
    assert user_profile.mood == new_mood
    # It's random, so we can't be sure it's different, but we can check it's a valid mood
    assert new_mood in list(UserMood)


@pytest.mark.asyncio
async def test_classify_user_archetype(context_service: ContextService, user_profile: UserProfile):
    """
    Test that classify_user_archetype updates the profile's archetype.
    """
    initial_archetype = user_profile.archetype
    new_archetype = await context_service.classify_user_archetype(user_profile)

    assert isinstance(new_archetype, UserArchetype)
    assert user_profile.archetype == new_archetype
    assert new_archetype in list(UserArchetype)


@pytest.mark.asyncio
async def test_update_engagement_score(context_service: ContextService, user_profile: UserProfile):
    """
    Test that update_engagement_score correctly increments the score.
    """
    initial_score = user_profile.engagement_score
    score_change = 5
    new_score = await context_service.update_engagement_score(user_profile, score_change)

    assert new_score == initial_score + score_change
    assert user_profile.engagement_score == new_score
