"""
Narrative Events for Diana Bot V2.

This module defines all events related to the interactive narrative system
including story progress, decisions, character interactions, and story state changes.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..interfaces import EventPriority
from .base import DomainEvent, EventCategory


class StoryProgressEvent(DomainEvent):
    """
    Event fired when a user progresses through the story.

    This is a fundamental narrative event that tracks user journey
    through interactive stories and triggers various game mechanics.
    """

    def __init__(
        self,
        user_id: int,
        story_id: str,
        chapter_id: str,
        previous_chapter_id: Optional[str],
        progress_percentage: float,
        reading_time_seconds: Optional[int] = None,
        interaction_count: int = 0,
        source_service: str = "narrative",
        correlation_id: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize StoryProgressEvent.

        Args:
            user_id: ID of the user progressing through the story
            story_id: ID of the story being read
            chapter_id: ID of the current chapter
            previous_chapter_id: ID of the previous chapter (if any)
            progress_percentage: Overall story completion percentage (0.0-100.0)
            reading_time_seconds: Time spent reading this chapter
            interaction_count: Number of interactions in this chapter
            source_service: Service tracking the progress
            correlation_id: ID for tracing related events
            **kwargs: Additional arguments
        """
        payload = {
            "story_id": story_id,
            "chapter_id": chapter_id,
            "previous_chapter_id": previous_chapter_id,
            "progress_percentage": progress_percentage,
            "reading_time_seconds": reading_time_seconds,
            "interaction_count": interaction_count,
            "progressed_at": datetime.utcnow().isoformat(),
            # These will be set by the narrative service
            "total_chapters_completed": None,
            "user_reading_speed_wpm": None,
            "chapter_difficulty_rating": None,
        }

        super().__init__(
            user_id=user_id,
            source_service=source_service,
            correlation_id=correlation_id,
            priority=EventPriority.NORMAL,
            payload=payload,
            **kwargs,
        )

    @property
    def story_id(self) -> str:
        """ID of the story being read."""
        return self.payload["story_id"]

    @property
    def chapter_id(self) -> str:
        """ID of the current chapter."""
        return self.payload["chapter_id"]

    @property
    def previous_chapter_id(self) -> Optional[str]:
        """ID of the previous chapter."""
        return self.payload.get("previous_chapter_id")

    @property
    def progress_percentage(self) -> float:
        """Overall story completion percentage."""
        return self.payload["progress_percentage"]

    @property
    def reading_time_seconds(self) -> Optional[int]:
        """Time spent reading this chapter."""
        return self.payload.get("reading_time_seconds")

    @property
    def interaction_count(self) -> int:
        """Number of interactions in this chapter."""
        return self.payload["interaction_count"]

    def _get_event_category(self) -> EventCategory:
        """Story progress events belong to the NARRATIVE category."""
        return EventCategory.NARRATIVE

    def _custom_validation(self, errors: List[str]) -> None:
        """Validate story progress specific requirements."""
        super()._custom_validation(errors)

        if not self.story_id or not isinstance(self.story_id, str):
            errors.append("Story ID must be a non-empty string")

        if not self.chapter_id or not isinstance(self.chapter_id, str):
            errors.append("Chapter ID must be a non-empty string")

        if not isinstance(self.progress_percentage, (int, float)) or not (
            0 <= self.progress_percentage <= 100
        ):
            errors.append("Progress percentage must be between 0 and 100")

        if self.reading_time_seconds is not None and (
            not isinstance(self.reading_time_seconds, int)
            or self.reading_time_seconds < 0
        ):
            errors.append("Reading time must be a non-negative integer")


class DecisionMadeEvent(DomainEvent):
    """
    Event fired when a user makes a decision in an interactive story.

    This is a critical narrative event that affects story branching,
    character relationships, and future story paths.
    """

    def __init__(
        self,
        user_id: int,
        story_id: str,
        chapter_id: str,
        decision_point_id: str,
        decision_id: str,
        decision_text: str,
        decision_consequences: Dict[str, Any],
        character_relationships_affected: Dict[str, float] = None,
        story_branches_unlocked: List[str] = None,
        decision_time_seconds: Optional[int] = None,
        source_service: str = "narrative",
        correlation_id: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize DecisionMadeEvent.

        Args:
            user_id: ID of the user making the decision
            story_id: ID of the story
            chapter_id: ID of the chapter containing the decision
            decision_point_id: ID of the decision point in the story
            decision_id: ID of the specific decision chosen
            decision_text: Text of the decision made
            decision_consequences: Consequences of this decision
            character_relationships_affected: Characters and relationship changes
            story_branches_unlocked: New story branches unlocked by this decision
            decision_time_seconds: Time taken to make the decision
            source_service: Service processing the decision
            correlation_id: ID for tracing related events
            **kwargs: Additional arguments
        """
        payload = {
            "story_id": story_id,
            "chapter_id": chapter_id,
            "decision_point_id": decision_point_id,
            "decision_id": decision_id,
            "decision_text": decision_text,
            "decision_consequences": decision_consequences,
            "character_relationships_affected": character_relationships_affected or {},
            "story_branches_unlocked": story_branches_unlocked or [],
            "decision_time_seconds": decision_time_seconds,
            "decided_at": datetime.utcnow().isoformat(),
            # These will be set by the narrative service
            "user_decision_pattern": None,
            "alternative_outcomes": None,
            "story_impact_score": None,
        }

        super().__init__(
            user_id=user_id,
            source_service=source_service,
            correlation_id=correlation_id,
            priority=EventPriority.HIGH,  # Decisions are important story events
            payload=payload,
            **kwargs,
        )

    @property
    def story_id(self) -> str:
        """ID of the story."""
        return self.payload["story_id"]

    @property
    def chapter_id(self) -> str:
        """ID of the chapter."""
        return self.payload["chapter_id"]

    @property
    def decision_point_id(self) -> str:
        """ID of the decision point."""
        return self.payload["decision_point_id"]

    @property
    def decision_id(self) -> str:
        """ID of the chosen decision."""
        return self.payload["decision_id"]

    @property
    def decision_text(self) -> str:
        """Text of the decision made."""
        return self.payload["decision_text"]

    @property
    def decision_consequences(self) -> Dict[str, Any]:
        """Consequences of this decision."""
        return self.payload["decision_consequences"]

    @property
    def character_relationships_affected(self) -> Dict[str, float]:
        """Characters and relationship changes."""
        return self.payload["character_relationships_affected"]

    @property
    def story_branches_unlocked(self) -> List[str]:
        """New story branches unlocked."""
        return self.payload["story_branches_unlocked"]

    def _get_event_category(self) -> EventCategory:
        """Decision events belong to the NARRATIVE category."""
        return EventCategory.NARRATIVE

    def _custom_validation(self, errors: List[str]) -> None:
        """Validate decision made specific requirements."""
        super()._custom_validation(errors)

        required_string_fields = [
            "story_id",
            "chapter_id",
            "decision_point_id",
            "decision_id",
            "decision_text",
        ]
        for field in required_string_fields:
            value = getattr(self, field)
            if not value or not isinstance(value, str):
                errors.append(
                    f"{field.replace('_', ' ').title()} must be a non-empty string"
                )

        if not isinstance(self.decision_consequences, dict):
            errors.append("Decision consequences must be a dictionary")


class ChapterCompletedEvent(DomainEvent):
    """
    Event fired when a user completes a story chapter.

    This event marks chapter milestones and often triggers rewards,
    achievements, and progress tracking.
    """

    def __init__(
        self,
        user_id: int,
        story_id: str,
        chapter_id: str,
        chapter_title: str,
        completion_time_seconds: int,
        decisions_made: int,
        character_interactions: int,
        chapter_rating: Optional[int] = None,  # 1-5 stars
        next_chapter_id: Optional[str] = None,
        rewards_earned: Dict[str, Any] = None,
        source_service: str = "narrative",
        correlation_id: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize ChapterCompletedEvent.

        Args:
            user_id: ID of the user completing the chapter
            story_id: ID of the story
            chapter_id: ID of the completed chapter
            chapter_title: Title of the completed chapter
            completion_time_seconds: Time taken to complete the chapter
            decisions_made: Number of decisions made in the chapter
            character_interactions: Number of character interactions
            chapter_rating: User's rating of the chapter (1-5 stars)
            next_chapter_id: ID of the next chapter (if available)
            rewards_earned: Rewards earned for completing the chapter
            source_service: Service processing the completion
            correlation_id: ID for tracing related events
            **kwargs: Additional arguments
        """
        payload = {
            "story_id": story_id,
            "chapter_id": chapter_id,
            "chapter_title": chapter_title,
            "completion_time_seconds": completion_time_seconds,
            "decisions_made": decisions_made,
            "character_interactions": character_interactions,
            "chapter_rating": chapter_rating,
            "next_chapter_id": next_chapter_id,
            "rewards_earned": rewards_earned or {},
            "completed_at": datetime.utcnow().isoformat(),
            # These will be set by the narrative service
            "reading_speed_wpm": None,
            "engagement_score": None,
            "story_completion_percentage": None,
        }

        super().__init__(
            user_id=user_id,
            source_service=source_service,
            correlation_id=correlation_id,
            priority=EventPriority.HIGH,  # Chapter completion is a milestone
            payload=payload,
            **kwargs,
        )

    @property
    def story_id(self) -> str:
        """ID of the story."""
        return self.payload["story_id"]

    @property
    def chapter_id(self) -> str:
        """ID of the completed chapter."""
        return self.payload["chapter_id"]

    @property
    def chapter_title(self) -> str:
        """Title of the completed chapter."""
        return self.payload["chapter_title"]

    @property
    def completion_time_seconds(self) -> int:
        """Time taken to complete the chapter."""
        return self.payload["completion_time_seconds"]

    @property
    def decisions_made(self) -> int:
        """Number of decisions made."""
        return self.payload["decisions_made"]

    @property
    def character_interactions(self) -> int:
        """Number of character interactions."""
        return self.payload["character_interactions"]

    @property
    def chapter_rating(self) -> Optional[int]:
        """User's rating of the chapter."""
        return self.payload.get("chapter_rating")

    def _get_event_category(self) -> EventCategory:
        """Chapter completion events belong to the NARRATIVE category."""
        return EventCategory.NARRATIVE

    def _custom_validation(self, errors: List[str]) -> None:
        """Validate chapter completed specific requirements."""
        super()._custom_validation(errors)

        required_string_fields = ["story_id", "chapter_id", "chapter_title"]
        for field in required_string_fields:
            value = getattr(self, field)
            if not value or not isinstance(value, str):
                errors.append(
                    f"{field.replace('_', ' ').title()} must be a non-empty string"
                )

        if (
            not isinstance(self.completion_time_seconds, int)
            or self.completion_time_seconds < 0
        ):
            errors.append("Completion time must be a non-negative integer")

        if not isinstance(self.decisions_made, int) or self.decisions_made < 0:
            errors.append("Decisions made must be a non-negative integer")

        if self.chapter_rating is not None and (
            not isinstance(self.chapter_rating, int)
            or not (1 <= self.chapter_rating <= 5)
        ):
            errors.append("Chapter rating must be an integer between 1 and 5")


class NarrativeStateChangedEvent(DomainEvent):
    """
    Event fired when the user's narrative state changes significantly.

    This event tracks major changes in the user's story context,
    character relationships, or narrative flags that affect future content.
    """

    def __init__(
        self,
        user_id: int,
        story_id: str,
        state_change_type: str,  # relationship, flag, branch, inventory, etc.
        previous_state: Dict[str, Any],
        new_state: Dict[str, Any],
        change_reason: str,
        affected_characters: List[str] = None,
        unlocked_content: List[str] = None,
        locked_content: List[str] = None,
        source_service: str = "narrative",
        correlation_id: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize NarrativeStateChangedEvent.

        Args:
            user_id: ID of the user whose state changed
            story_id: ID of the story
            state_change_type: Type of state change
            previous_state: Previous state values
            new_state: New state values
            change_reason: Reason for the state change
            affected_characters: Characters affected by this change
            unlocked_content: Content unlocked by this change
            locked_content: Content locked by this change
            source_service: Service processing the state change
            correlation_id: ID for tracing related events
            **kwargs: Additional arguments
        """
        payload = {
            "story_id": story_id,
            "state_change_type": state_change_type,
            "previous_state": previous_state,
            "new_state": new_state,
            "change_reason": change_reason,
            "affected_characters": affected_characters or [],
            "unlocked_content": unlocked_content or [],
            "locked_content": locked_content or [],
            "changed_at": datetime.utcnow().isoformat(),
            # These will be set by the narrative service
            "state_impact_score": None,
            "narrative_complexity": None,
        }

        super().__init__(
            user_id=user_id,
            source_service=source_service,
            correlation_id=correlation_id,
            priority=EventPriority.NORMAL,
            payload=payload,
            **kwargs,
        )

    @property
    def story_id(self) -> str:
        """ID of the story."""
        return self.payload["story_id"]

    @property
    def state_change_type(self) -> str:
        """Type of state change."""
        return self.payload["state_change_type"]

    @property
    def previous_state(self) -> Dict[str, Any]:
        """Previous state values."""
        return self.payload["previous_state"]

    @property
    def new_state(self) -> Dict[str, Any]:
        """New state values."""
        return self.payload["new_state"]

    @property
    def change_reason(self) -> str:
        """Reason for the state change."""
        return self.payload["change_reason"]

    @property
    def affected_characters(self) -> List[str]:
        """Characters affected by this change."""
        return self.payload["affected_characters"]

    @property
    def unlocked_content(self) -> List[str]:
        """Content unlocked by this change."""
        return self.payload["unlocked_content"]

    def _get_event_category(self) -> EventCategory:
        """Narrative state events belong to the NARRATIVE category."""
        return EventCategory.NARRATIVE

    def _custom_validation(self, errors: List[str]) -> None:
        """Validate narrative state changed specific requirements."""
        super()._custom_validation(errors)

        required_string_fields = ["story_id", "state_change_type", "change_reason"]
        for field in required_string_fields:
            value = getattr(self, field)
            if not value or not isinstance(value, str):
                errors.append(
                    f"{field.replace('_', ' ').title()} must be a non-empty string"
                )

        if not isinstance(self.previous_state, dict):
            errors.append("Previous state must be a dictionary")

        if not isinstance(self.new_state, dict):
            errors.append("New state must be a dictionary")


class CharacterInteractionEvent(DomainEvent):
    """
    Event fired when a user interacts with a character in the story.

    This event tracks character relationships and dialogue patterns
    which affect future story branches and character behavior.
    """

    def __init__(
        self,
        user_id: int,
        story_id: str,
        chapter_id: str,
        character_id: str,
        character_name: str,
        interaction_type: str,  # dialogue, action, gift, etc.
        interaction_data: Dict[str, Any],
        relationship_change: float = 0.0,
        mood_change: Optional[str] = None,
        source_service: str = "narrative",
        correlation_id: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize CharacterInteractionEvent.

        Args:
            user_id: ID of the user interacting
            story_id: ID of the story
            chapter_id: ID of the current chapter
            character_id: ID of the character
            character_name: Name of the character
            interaction_type: Type of interaction
            interaction_data: Detailed interaction data
            relationship_change: Change in relationship score
            mood_change: Change in character's mood
            source_service: Service processing the interaction
            correlation_id: ID for tracing related events
            **kwargs: Additional arguments
        """
        payload = {
            "story_id": story_id,
            "chapter_id": chapter_id,
            "character_id": character_id,
            "character_name": character_name,
            "interaction_type": interaction_type,
            "interaction_data": interaction_data,
            "relationship_change": relationship_change,
            "mood_change": mood_change,
            "interacted_at": datetime.utcnow().isoformat(),
            # These will be set by the narrative service
            "current_relationship_level": None,
            "character_trust_level": None,
            "interaction_history_count": None,
        }

        super().__init__(
            user_id=user_id,
            source_service=source_service,
            correlation_id=correlation_id,
            priority=EventPriority.NORMAL,
            payload=payload,
            **kwargs,
        )

    @property
    def character_id(self) -> str:
        """ID of the character."""
        return self.payload["character_id"]

    @property
    def character_name(self) -> str:
        """Name of the character."""
        return self.payload["character_name"]

    @property
    def interaction_type(self) -> str:
        """Type of interaction."""
        return self.payload["interaction_type"]

    @property
    def relationship_change(self) -> float:
        """Change in relationship score."""
        return self.payload["relationship_change"]

    def _get_event_category(self) -> EventCategory:
        """Character interaction events belong to the NARRATIVE category."""
        return EventCategory.NARRATIVE

    def _custom_validation(self, errors: List[str]) -> None:
        """Validate character interaction specific requirements."""
        super()._custom_validation(errors)

        required_string_fields = [
            "story_id",
            "chapter_id",
            "character_id",
            "character_name",
            "interaction_type",
        ]
        for field in required_string_fields:
            value = getattr(self, field)
            if not value or not isinstance(value, str):
                errors.append(
                    f"{field.replace('_', ' ').title()} must be a non-empty string"
                )

        if not isinstance(self.payload["interaction_data"], dict):
            errors.append("Interaction data must be a dictionary")


class StoryStartedEvent(DomainEvent):
    """
    Event fired when a user starts a new story.

    This event marks the beginning of a user's journey through
    a particular narrative and is used for onboarding and analytics.
    """

    def __init__(
        self,
        user_id: int,
        story_id: str,
        story_title: str,
        story_category: str,
        estimated_duration_minutes: Optional[int] = None,
        difficulty_level: Optional[str] = None,
        tags: List[str] = None,
        source_service: str = "narrative",
        correlation_id: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize StoryStartedEvent.

        Args:
            user_id: ID of the user starting the story
            story_id: ID of the story
            story_title: Title of the story
            story_category: Category of the story
            estimated_duration_minutes: Estimated time to complete
            difficulty_level: Difficulty level (beginner, intermediate, advanced)
            tags: Tags associated with the story
            source_service: Service handling the story start
            correlation_id: ID for tracing related events
            **kwargs: Additional arguments
        """
        payload = {
            "story_id": story_id,
            "story_title": story_title,
            "story_category": story_category,
            "estimated_duration_minutes": estimated_duration_minutes,
            "difficulty_level": difficulty_level,
            "tags": tags or [],
            "started_at": datetime.utcnow().isoformat(),
            # These will be set by the narrative service
            "user_story_count": None,
            "recommended_by": None,
        }

        super().__init__(
            user_id=user_id,
            source_service=source_service,
            correlation_id=correlation_id,
            priority=EventPriority.HIGH,  # Story starts are important milestones
            payload=payload,
            **kwargs,
        )

    @property
    def story_id(self) -> str:
        """ID of the story."""
        return self.payload["story_id"]

    @property
    def story_title(self) -> str:
        """Title of the story."""
        return self.payload["story_title"]

    @property
    def story_category(self) -> str:
        """Category of the story."""
        return self.payload["story_category"]

    def _get_event_category(self) -> EventCategory:
        """Story started events belong to the NARRATIVE category."""
        return EventCategory.NARRATIVE

    def _custom_validation(self, errors: List[str]) -> None:
        """Validate story started specific requirements."""
        super()._custom_validation(errors)

        required_fields = ["story_id", "story_title", "story_category"]
        for field in required_fields:
            value = getattr(self, field)
            if not value or not isinstance(value, str):
                errors.append(
                    f"{field.replace('_', ' ').title()} must be a non-empty string"
                )


# Export all narrative events
__all__ = [
    "StoryProgressEvent",
    "DecisionMadeEvent",
    "ChapterCompletedEvent",
    "NarrativeStateChangedEvent",
    "CharacterInteractionEvent",
    "StoryStartedEvent",
]
