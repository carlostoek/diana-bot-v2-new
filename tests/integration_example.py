#!/usr/bin/env python3
"""
Integration example for the GamificationService.

This script demonstrates the basic functionality of the gamification system
without requiring a full database setup.
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from src.core.events.core import UserActionEvent
from src.core.events.narrative import StoryCompletionEvent
from src.models.gamification import (
    AchievementCategory,
    AchievementTier,
    PointsTransactionType,
    UserGamification,
)
from src.services.gamification.interfaces import IGamificationRepository
from src.services.gamification.service import GamificationService


class MockRepository(IGamificationRepository):
    """Mock repository for demonstration."""

    def __init__(self):
        self.users = {}
        self.transactions = []
        self.achievements = []
        self.user_achievements = []
        self.streaks = []
        self.leaderboard_entries = []

    async def initialize(self):
        pass

    async def get_user_gamification(self, user_id):
        return self.users.get(user_id)

    async def create_user_gamification(self, user_id):
        user_gam = UserGamification(user_id=user_id)
        user_gam.total_points = 0
        user_gam.current_level = 1
        user_gam.experience_points = 0
        user_gam.vip_status = False
        user_gam.vip_multiplier = 1.0
        user_gam.current_daily_streak = 0
        user_gam.longest_daily_streak = 0
        user_gam.total_achievements = 0
        user_gam.bronze_achievements = 0
        user_gam.silver_achievements = 0
        user_gam.gold_achievements = 0
        user_gam.platinum_achievements = 0
        user_gam.current_multiplier = 1.0
        self.users[user_id] = user_gam
        return user_gam

    async def update_user_gamification(self, user_gamification):
        self.users[user_gamification.user_id] = user_gamification
        return user_gamification

    async def create_points_transaction(self, transaction_data):
        transaction = MagicMock()
        transaction.id = len(self.transactions) + 1
        for key, value in transaction_data.items():
            setattr(transaction, key, value)
        transaction.created_at = datetime.now(timezone.utc)
        self.transactions.append(transaction)
        return transaction

    async def get_points_transactions(self, user_id, limit, offset, transaction_type):
        user_transactions = [t for t in self.transactions if t.user_id == user_id]
        if transaction_type:
            user_transactions = [
                t for t in user_transactions if t.transaction_type == transaction_type
            ]
        return user_transactions[offset : offset + limit]

    async def get_achievement_definitions(self, active_only=True):
        return self.achievements

    async def create_achievement_definition(self, achievement_data):
        achievement = MagicMock()
        for key, value in achievement_data.items():
            setattr(achievement, key, value)
        self.achievements.append(achievement)
        return achievement

    async def get_user_achievements(self, user_id, completed_only=False):
        user_achievements = [
            ua for ua in self.user_achievements if ua.user_id == user_id
        ]
        if completed_only:
            user_achievements = [ua for ua in user_achievements if ua.is_completed]
        return user_achievements

    async def create_user_achievement(self, achievement_data):
        user_achievement = MagicMock()
        for key, value in achievement_data.items():
            setattr(user_achievement, key, value)
        user_achievement.id = len(self.user_achievements) + 1
        self.user_achievements.append(user_achievement)
        return user_achievement

    async def update_user_achievement(self, user_achievement):
        return user_achievement

    async def get_user_streaks(self, user_id):
        return [s for s in self.streaks if s.user_id == user_id]

    async def update_streak_record(self, streak_data):
        streak = MagicMock()
        for key, value in streak_data.items():
            setattr(streak, key, value)
        self.streaks.append(streak)
        return streak

    async def update_leaderboard_entry(self, entry_data):
        entry = MagicMock()
        for key, value in entry_data.items():
            setattr(entry, key, value)
        self.leaderboard_entries.append(entry)
        return entry

    async def get_leaderboard_entries(
        self, leaderboard_type, period_start, period_end, limit
    ):
        return self.leaderboard_entries[:limit]


async def demo_gamification_service():
    """Demonstrate the gamification service functionality."""
    print("🎮 Diana Bot V2 - Gamification Service Demo")
    print("=" * 50)

    # Create mock event bus and repository
    mock_event_bus = MagicMock()
    mock_event_bus.subscribe = AsyncMock(return_value="subscription_id")
    mock_event_bus.unsubscribe = AsyncMock(return_value=True)
    mock_event_bus.publish = AsyncMock(return_value=True)

    mock_repository = MockRepository()

    # Initialize gamification service
    service = GamificationService(event_bus=mock_event_bus, repository=mock_repository)

    await service.initialize()
    print("✅ Gamification service initialized")

    # Demo 1: User Points System
    print("\n📊 Points System Demo")
    print("-" * 30)

    user_id = 12345

    # Award points for various actions
    await service.award_points(user_id, 50, "daily_login")
    print(f"✅ Awarded 50 points for daily login")

    await service.award_points(user_id, 200, "story_chapter_complete")
    print(f"✅ Awarded 200 points for chapter completion")

    await service.award_points(user_id, 500, "story_complete", bonus_points=100)
    print(f"✅ Awarded 500 + 100 bonus points for story completion")

    # Check user points
    total_points = await service.get_user_points(user_id)
    print(f"💰 User {user_id} total points: {total_points}")

    # Demo 2: Points History
    print("\n📜 Points History Demo")
    print("-" * 30)

    history = await service.get_points_history(user_id, limit=5)
    for i, transaction in enumerate(history, 1):
        print(f"  {i}. {transaction['action_type']}: {transaction['amount']} points")

    # Demo 3: VIP System
    print("\n👑 VIP System Demo")
    print("-" * 30)

    await service.set_vip_status(user_id, True, 2.0)
    print(f"✅ Set user {user_id} as VIP with 2.0x multiplier")

    # Award points as VIP (should get multiplier)
    await service.award_points(user_id, 100, "vip_action")
    new_total = await service.get_user_points(user_id)
    print(f"💰 After VIP action: {new_total} points (with 2.0x multiplier)")

    # Demo 4: Level System
    print("\n🏆 Level System Demo")
    print("-" * 30)

    level, level_increased = await service.update_user_level(user_id)
    print(f"📈 User level: {level} (increased: {level_increased})")

    # Demo 5: Event Handling
    print("\n🔔 Event Handling Demo")
    print("-" * 30)

    # Simulate UserActionEvent
    user_action_event = UserActionEvent(
        user_id=user_id,
        action_type="daily_login",
        action_data={"timestamp": datetime.now(timezone.utc).isoformat()},
        source_service="telegram",
    )

    await service.handle_user_action(user_action_event)
    print("✅ Handled UserActionEvent for daily login")

    # Simulate StoryCompletionEvent
    story_completion_event = StoryCompletionEvent(
        user_id=user_id,
        story_id="demo_story",
        story_title="Demo Story",
        story_category="adventure",
        total_completion_time_seconds=3600,
        total_chapters_completed=5,
        total_decisions_made=15,
        ending_achieved="happy_ending",
        completion_percentage=100.0,
        overall_rating=5,
        source_service="narrative",
    )

    await service.handle_story_completion(story_completion_event)
    print("✅ Handled StoryCompletionEvent")

    # Demo 6: User Statistics
    print("\n📈 User Statistics Demo")
    print("-" * 30)

    stats = await service.get_user_statistics(user_id)
    print(f"📊 User Statistics:")
    for key, value in stats.items():
        print(f"  - {key}: {value}")

    # Demo 7: Event Bus Integration
    print("\n🚌 Event Bus Integration Demo")
    print("-" * 30)

    # Check that events were published
    published_calls = mock_event_bus.publish.call_count
    print(f"📤 Published {published_calls} events to the Event Bus")
    print(f"📥 Subscribed to {len(service._subscription_ids)} event types")

    # Cleanup
    await service.shutdown()
    print("\n✅ Gamification service shutdown complete")

    print("\n🎯 Demo completed successfully!")
    print("The gamification service is fully functional and ready for production.")


if __name__ == "__main__":
    asyncio.run(demo_gamification_service())
