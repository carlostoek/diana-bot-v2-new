"""
Event Handlers for Diana Bot V2 Gamification System.

This module contains all event handlers that subscribe to events from other services
and trigger gamification mechanics like points, achievements, streaks, and leaderboards.
"""

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional

from ...core.event_bus import BaseEventHandler
from ...core.events.core import UserActionEvent
from ...core.events.narrative import (
    ChapterCompletedEvent,
    DecisionMadeEvent,
    StoryCompletionEvent,
    StoryStartedEvent,
)
from ...core.interfaces import IEvent, IEventHandler
from ...models.gamification import StreakType, UserGamification
from .interfaces import IGamificationService


class GamificationEventHandlerBase(BaseEventHandler):
    """
    Base class for gamification event handlers.

    Provides common functionality and error handling patterns
    for all gamification event handlers.
    """

    def __init__(self, gamification_service: IGamificationService, handler_name: str):
        """
        Initialize the base handler.

        Args:
            gamification_service: The gamification service instance
            handler_name: Name of the specific handler
        """
        self.gamification_service = gamification_service
        self.logger = logging.getLogger(__name__)

        super().__init__(
            service_name="gamification",
            handler_id=f"gamification_{handler_name}_{uuid.uuid4().hex[:8]}",
        )

    async def on_error(self, event: IEvent, error: Exception) -> bool:
        """Enhanced error handling for gamification events."""
        self.logger.error(
            f"Error handling {event.event_type} in {self.handler_id}: {str(error)}",
            extra={
                "event_id": event.event_id,
                "event_type": event.event_type,
                "user_id": getattr(event, "user_id", None),
                "error_type": type(error).__name__,
            },
        )

        # Don't retry on validation errors or user not found errors
        from ...core.interfaces import EventValidationError
        from .interfaces import AntiAbuseError, UserNotFoundError

        non_retryable_errors = (
            EventValidationError,
            UserNotFoundError,
            AntiAbuseError,
            ValueError,
        )
        return not isinstance(error, non_retryable_errors)


class UserActionEventHandler(GamificationEventHandlerBase):
    """
    Handles UserActionEvent to award points and update streaks.

    This handler processes general user actions like daily logins,
    button clicks, and other interactions that should earn points.
    """

    def __init__(self, gamification_service: IGamificationService):
        super().__init__(gamification_service, "user_action")
        self.add_supported_event_type("core.user_action")

    async def _process_event(self, event: UserActionEvent) -> bool:
        """Process user action event for gamification rewards."""
        try:
            action_type = event.action_type
            action_data = event.action_data

            # Map action types to gamification mechanics
            await self._handle_action_type(event, action_type, action_data)

            return True

        except Exception as e:
            self.logger.error(
                f"Failed to process user action event {event.event_id}: {e}"
            )
            raise

    async def _handle_action_type(
        self,
        event: UserActionEvent,
        action_type: str,
        action_data: Dict[str, Any],
    ) -> None:
        """Handle specific action types with appropriate gamification responses."""

        # Daily login handling
        if action_type == "daily_login":
            await self._handle_daily_login(event, action_data)

        # General interaction points
        elif action_type in ["button_click", "menu_navigation", "feature_usage"]:
            await self._handle_general_interaction(event, action_type, action_data)

        # Session-based rewards
        elif action_type == "session_start":
            await self._handle_session_start(event, action_data)
        elif action_type == "session_end":
            await self._handle_session_end(event, action_data)

        # Tutorial and onboarding
        elif action_type == "tutorial_completed":
            await self._handle_tutorial_completion(event, action_data)

        # Social actions
        elif action_type in ["friend_invite", "content_share"]:
            await self._handle_social_action(event, action_type, action_data)

        # Premium/VIP actions
        elif action_type in ["subscription_purchase", "premium_feature_used"]:
            await self._handle_premium_action(event, action_type, action_data)

    async def _handle_daily_login(
        self, event: UserActionEvent, action_data: Dict[str, Any]
    ) -> None:
        """Handle daily login action."""
        # Award daily login points
        await self.gamification_service.award_points(
            user_id=event.user_id,
            points_amount=50,  # Base daily login points
            action_type="daily_login",
            source_event_id=event.event_id,
            metadata={
                "login_time": action_data.get("login_time"),
                "platform": action_data.get("platform"),
            },
        )

        # Update daily login streak
        await self.gamification_service.update_streak(
            user_id=event.user_id,
            streak_type=StreakType.DAILY_LOGIN,
        )

    async def _handle_general_interaction(
        self,
        event: UserActionEvent,
        action_type: str,
        action_data: Dict[str, Any],
    ) -> None:
        """Handle general interaction actions."""
        # Small points for general interactions
        point_values = {
            "button_click": 5,
            "menu_navigation": 3,
            "feature_usage": 10,
        }

        points = point_values.get(action_type, 5)

        await self.gamification_service.award_points(
            user_id=event.user_id,
            points_amount=points,
            action_type=action_type,
            source_event_id=event.event_id,
            metadata=action_data,
        )

        # Update interaction streak
        await self.gamification_service.update_streak(
            user_id=event.user_id,
            streak_type=StreakType.INTERACTION,
        )

    async def _handle_session_start(
        self, event: UserActionEvent, action_data: Dict[str, Any]
    ) -> None:
        """Handle session start."""
        # Award small points for starting a session
        await self.gamification_service.award_points(
            user_id=event.user_id,
            points_amount=10,
            action_type="session_start",
            source_event_id=event.event_id,
            metadata=action_data,
        )

    async def _handle_session_end(
        self, event: UserActionEvent, action_data: Dict[str, Any]
    ) -> None:
        """Handle session end with duration-based rewards."""
        session_duration = action_data.get("duration_seconds", 0)

        # Bonus points for longer sessions
        if session_duration >= 600:  # 10+ minutes
            bonus_points = min(
                100, session_duration // 60
            )  # 1 point per minute, max 100

            await self.gamification_service.award_points(
                user_id=event.user_id,
                points_amount=bonus_points,
                action_type="session_long",
                source_event_id=event.event_id,
                metadata={
                    "session_duration_seconds": session_duration,
                    "bonus_reason": "extended_engagement",
                },
            )

    async def _handle_tutorial_completion(
        self, event: UserActionEvent, action_data: Dict[str, Any]
    ) -> None:
        """Handle tutorial completion."""
        tutorial_id = action_data.get("tutorial_id", "unknown")

        await self.gamification_service.award_points(
            user_id=event.user_id,
            points_amount=100,
            action_type="tutorial_completed",
            source_event_id=event.event_id,
            metadata={
                "tutorial_id": tutorial_id,
                "completion_time": action_data.get("completion_time"),
            },
        )

    async def _handle_social_action(
        self,
        event: UserActionEvent,
        action_type: str,
        action_data: Dict[str, Any],
    ) -> None:
        """Handle social actions like invites and sharing."""
        point_values = {
            "friend_invite": 500,
            "content_share": 25,
        }

        points = point_values.get(action_type, 25)

        await self.gamification_service.award_points(
            user_id=event.user_id,
            points_amount=points,
            action_type=action_type,
            source_event_id=event.event_id,
            metadata=action_data,
        )

    async def _handle_premium_action(
        self,
        event: UserActionEvent,
        action_type: str,
        action_data: Dict[str, Any],
    ) -> None:
        """Handle premium/VIP actions."""
        if action_type == "subscription_purchase":
            # Large reward for purchasing subscription
            await self.gamification_service.award_points(
                user_id=event.user_id,
                points_amount=2000,
                action_type="subscription_purchase",
                source_event_id=event.event_id,
                metadata=action_data,
            )
        elif action_type == "premium_feature_used":
            # Moderate reward for using premium features
            await self.gamification_service.award_points(
                user_id=event.user_id,
                points_amount=50,
                action_type="premium_feature_used",
                source_event_id=event.event_id,
                metadata=action_data,
            )


class StoryCompletionEventHandler(GamificationEventHandlerBase):
    """
    Handles StoryCompletionEvent to award major completion rewards.

    This handler processes full story completions, which are major milestones
    that should trigger significant rewards and achievements.
    """

    def __init__(self, gamification_service: IGamificationService):
        super().__init__(gamification_service, "story_completion")
        self.add_supported_event_type("narrative.story_completion")

    async def _process_event(self, event: StoryCompletionEvent) -> bool:
        """Process story completion for major gamification rewards."""
        try:
            # Calculate base story completion reward
            base_points = 500

            # Calculate bonuses
            bonus_points = await self._calculate_completion_bonuses(event)

            # Award points with bonuses
            await self.gamification_service.award_points(
                user_id=event.user_id,
                points_amount=base_points,
                action_type="story_complete",
                bonus_points=bonus_points,
                source_event_id=event.event_id,
                metadata={
                    "story_id": event.story_id,
                    "story_title": event.story_title,
                    "story_category": event.story_category,
                    "completion_time_seconds": event.total_completion_time_seconds,
                    "chapters_completed": event.total_chapters_completed,
                    "decisions_made": event.total_decisions_made,
                    "ending_achieved": event.ending_achieved,
                    "overall_rating": event.overall_rating,
                    "completion_percentage": event.completion_percentage,
                },
            )

            # Update story progress streak
            await self.gamification_service.update_streak(
                user_id=event.user_id,
                streak_type=StreakType.STORY_PROGRESS,
            )

            # Check for story-related achievements
            await self._check_story_achievements(event)

            return True

        except Exception as e:
            self.logger.error(
                f"Failed to process story completion event {event.event_id}: {e}"
            )
            raise

    async def _calculate_completion_bonuses(self, event: StoryCompletionEvent) -> int:
        """Calculate bonus points for story completion."""
        bonus_points = 0

        # Perfect completion bonus (100% completion)
        if event.completion_percentage >= 100.0:
            bonus_points += 200

        # High rating bonus
        if event.overall_rating and event.overall_rating >= 4:
            bonus_points += 100

        # Speed completion bonus (under 2 hours for stories)
        if event.total_completion_time_seconds < 7200:  # 2 hours
            bonus_points += 150

        # Decision engagement bonus (many decisions made)
        if event.total_decisions_made >= 20:
            bonus_points += 100

        # Chapter completion bonus
        if event.total_chapters_completed >= 10:
            bonus_points += 50

        return bonus_points

    async def _check_story_achievements(self, event: StoryCompletionEvent) -> None:
        """Check for story-related achievements."""
        # Get user stats for achievement checking
        user_stats = await self.gamification_service.get_user_statistics(event.user_id)

        # Update stats with current completion
        stories_completed = user_stats.get("stories_completed", 0) + 1
        total_decisions = (
            user_stats.get("total_decisions_made", 0) + event.total_decisions_made
        )

        trigger_context = {
            "action_type": "story_complete",
            "story_category": event.story_category,
            "stories_completed": stories_completed,
            "total_decisions_made": total_decisions,
            "ending_achieved": event.ending_achieved,
            "completion_percentage": event.completion_percentage,
            "source_event_id": event.event_id,
        }

        # Check achievements
        await self.gamification_service.check_achievements(
            user_id=event.user_id, trigger_context=trigger_context
        )


class ChapterCompletedEventHandler(GamificationEventHandlerBase):
    """
    Handles ChapterCompletedEvent to award progress rewards.

    This handler processes individual chapter completions,
    which are smaller milestones that provide steady progression rewards.
    """

    def __init__(self, gamification_service: IGamificationService):
        super().__init__(gamification_service, "chapter_completion")
        self.add_supported_event_type("narrative.chapter_completed")

    async def _process_event(self, event: ChapterCompletedEvent) -> bool:
        """Process chapter completion for progress rewards."""
        try:
            # Base chapter completion points
            base_points = 150

            # Calculate bonuses
            bonus_points = await self._calculate_chapter_bonuses(event)

            # Award points
            await self.gamification_service.award_points(
                user_id=event.user_id,
                points_amount=base_points,
                action_type="chapter_complete",
                bonus_points=bonus_points,
                source_event_id=event.event_id,
                metadata={
                    "story_id": event.story_id,
                    "chapter_id": event.chapter_id,
                    "chapter_title": event.chapter_title,
                    "completion_time_seconds": event.completion_time_seconds,
                    "decisions_made": event.decisions_made,
                    "character_interactions": event.character_interactions,
                    "chapter_rating": event.chapter_rating,
                },
            )

            return True

        except Exception as e:
            self.logger.error(
                f"Failed to process chapter completion event {event.event_id}: {e}"
            )
            raise

    async def _calculate_chapter_bonuses(self, event: ChapterCompletedEvent) -> int:
        """Calculate bonus points for chapter completion."""
        bonus_points = 0

        # High rating bonus
        if event.chapter_rating and event.chapter_rating >= 4:
            bonus_points += 50

        # Engagement bonus (many decisions/interactions)
        if event.decisions_made >= 5:
            bonus_points += 30

        if event.character_interactions >= 3:
            bonus_points += 20

        # Fast completion bonus (under 30 minutes)
        if event.completion_time_seconds < 1800:  # 30 minutes
            bonus_points += 25

        return bonus_points


class DecisionMadeEventHandler(GamificationEventHandlerBase):
    """
    Handles DecisionMadeEvent to award engagement points.

    This handler processes story decisions, which represent
    active user engagement with the narrative content.
    """

    def __init__(self, gamification_service: IGamificationService):
        super().__init__(gamification_service, "decision_made")
        self.add_supported_event_type("narrative.decision_made")

    async def _process_event(self, event: DecisionMadeEvent) -> bool:
        """Process decision making for engagement rewards."""
        try:
            # Base decision points
            base_points = 25

            # Calculate bonuses based on decision impact
            bonus_points = await self._calculate_decision_bonuses(event)

            # Award points
            await self.gamification_service.award_points(
                user_id=event.user_id,
                points_amount=base_points,
                action_type="decision_made",
                bonus_points=bonus_points,
                source_event_id=event.event_id,
                metadata={
                    "story_id": event.story_id,
                    "chapter_id": event.chapter_id,
                    "decision_point_id": event.decision_point_id,
                    "decision_id": event.decision_id,
                    "decision_text": event.decision_text,
                    "decision_consequences": event.decision_consequences,
                    "characters_affected": len(event.character_relationships_affected),
                    "branches_unlocked": len(event.story_branches_unlocked),
                },
            )

            # Check for decision-based achievements
            await self._check_decision_achievements(event)

            return True

        except Exception as e:
            self.logger.error(
                f"Failed to process decision made event {event.event_id}: {e}"
            )
            raise

    async def _calculate_decision_bonuses(self, event: DecisionMadeEvent) -> int:
        """Calculate bonus points for decision impact."""
        bonus_points = 0

        # High-impact decision bonus (affects many characters)
        if len(event.character_relationships_affected) >= 2:
            bonus_points += 15

        # Story branching bonus (unlocks new content)
        if len(event.story_branches_unlocked) >= 1:
            bonus_points += 20

        # Complex consequences bonus
        if len(event.decision_consequences) >= 3:
            bonus_points += 10

        return bonus_points

    async def _check_decision_achievements(self, event: DecisionMadeEvent) -> None:
        """Check for decision-related achievements."""
        # Get user stats
        user_stats = await self.gamification_service.get_user_statistics(event.user_id)

        # Update decision count
        decisions_made = user_stats.get("decisions_made", 0) + 1

        trigger_context = {
            "action_type": "decision_made",
            "decisions_made": decisions_made,
            "characters_affected": len(event.character_relationships_affected),
            "branches_unlocked": len(event.story_branches_unlocked),
            "source_event_id": event.event_id,
        }

        # Check achievements
        await self.gamification_service.check_achievements(
            user_id=event.user_id, trigger_context=trigger_context
        )


class StoryStartedEventHandler(GamificationEventHandlerBase):
    """
    Handles StoryStartedEvent to track engagement and potentially award starting bonuses.

    This handler processes story starts for tracking purposes and
    may award bonuses for trying new content or difficult stories.
    """

    def __init__(self, gamification_service: IGamificationService):
        super().__init__(gamification_service, "story_started")
        self.add_supported_event_type("narrative.story_started")

    async def _process_event(self, event: StoryStartedEvent) -> bool:
        """Process story start for engagement tracking and bonuses."""
        try:
            # Small bonus for starting a story
            base_points = 25
            bonus_points = 0

            # Bonus for difficult stories
            if event.payload.get("difficulty_level") == "advanced":
                bonus_points += 25
            elif event.payload.get("difficulty_level") == "intermediate":
                bonus_points += 10

            # Award starting bonus
            await self.gamification_service.award_points(
                user_id=event.user_id,
                points_amount=base_points,
                action_type="story_started",
                bonus_points=bonus_points,
                source_event_id=event.event_id,
                metadata={
                    "story_id": event.story_id,
                    "story_title": event.story_title,
                    "story_category": event.story_category,
                    "difficulty_level": event.payload.get("difficulty_level"),
                    "estimated_duration": event.payload.get(
                        "estimated_duration_minutes"
                    ),
                },
            )

            return True

        except Exception as e:
            self.logger.error(
                f"Failed to process story started event {event.event_id}: {e}"
            )
            raise


# Helper function to create all handlers
def create_gamification_event_handlers(
    gamification_service: IGamificationService,
) -> List[IEventHandler]:
    """
    Create all gamification event handlers.

    Args:
        gamification_service: The gamification service instance

    Returns:
        List of all event handlers
    """
    return [
        UserActionEventHandler(gamification_service),
        StoryCompletionEventHandler(gamification_service),
        ChapterCompletedEventHandler(gamification_service),
        DecisionMadeEventHandler(gamification_service),
        StoryStartedEventHandler(gamification_service),
    ]


# Export main classes
__all__ = [
    "GamificationEventHandlerBase",
    "UserActionEventHandler",
    "StoryCompletionEventHandler",
    "ChapterCompletedEventHandler",
    "DecisionMadeEventHandler",
    "StoryStartedEventHandler",
    "create_gamification_event_handlers",
]
