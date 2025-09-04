import pytest
from src.services.personalization_service import PersonalizationService
from src.domain.models import UserProfile, UserMood, UserArchetype


@pytest.fixture
def personalization_service():
    return PersonalizationService()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "archetype, expected_keyword",
    [
        (UserArchetype.EXPLORER, "jardín"),
        (UserArchetype.ACHIEVER, "desafío"),
        (UserArchetype.SOCIALIZER, "sueños"),
    ],
)
async def test_get_content_recommendations(
    personalization_service: PersonalizationService, archetype: UserArchetype, expected_keyword: str
):
    """
    Test that content recommendations are tailored to the user's archetype.
    """
    profile = UserProfile(user_id=1, archetype=archetype)
    recommendations = await personalization_service.get_content_recommendations(profile)

    assert isinstance(recommendations, list)
    assert len(recommendations) > 0
    assert any(expected_keyword in rec for rec in recommendations)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mood, archetype, expected_mood_msg, expected_archetype_msg",
    [
        (UserMood.HAPPY, UserArchetype.EXPLORER, "alegre", "caminos"),
        (UserMood.SAD, UserArchetype.ACHIEVER, "animes", "reto"),
        (UserMood.CURIOUS, UserArchetype.PHILOSOPHER, "curiosidad", "pregunta"),
    ],
)
async def test_generate_adaptive_message(
    personalization_service: PersonalizationService,
    mood: UserMood,
    archetype: UserArchetype,
    expected_mood_msg: str,
    expected_archetype_msg: str,
):
    """
    Test that the adaptive message is tailored to the user's mood and archetype.
    """
    profile = UserProfile(user_id=1, mood=mood, archetype=archetype)
    message = await personalization_service.generate_adaptive_message(profile)

    assert isinstance(message, str)
    assert expected_mood_msg in message
    assert expected_archetype_msg in message
