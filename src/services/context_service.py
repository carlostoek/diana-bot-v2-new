import random
from src.domain.models import UserProfile, UserMood, UserArchetype


class ContextService:
    """
    Service for analyzing and managing user context (AI-001).
    This is a mock implementation to satisfy the initial DoD.
    """

    async def detect_user_mood(self, profile: UserProfile) -> UserMood:
        """
        Mock implementation for detecting user mood.
        Returns a random mood and updates the profile.
        """
        mood = random.choice(list(UserMood))
        profile.mood = mood
        return mood

    async def classify_user_archetype(self, profile: UserProfile) -> UserArchetype:
        """
        Mock implementation for classifying user archetype.
        Returns a random archetype and updates the profile.
        """
        archetype = random.choice(list(UserArchetype))
        profile.archetype = archetype
        return archetype

    async def update_engagement_score(
        self, profile: UserProfile, score_change: int = 1
    ) -> int:
        """
        Updates the user's engagement score.
        """
        profile.engagement_score += score_change
        return profile.engagement_score
