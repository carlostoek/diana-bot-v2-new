"""Integration test between UserService and GamificationService."""

import pytest
from unittest.mock import AsyncMock

from src.modules.user.service import UserService
from src.modules.user.models import User


class MockGamificationService:
    """Mock GamificationService for testing integration."""
    
    def __init__(self):
        self.initialized_users = []
        self.user_data_requests = []
    
    async def initialize_user(self, user_id, user_data):
        """Mock user initialization in gamification."""
        self.initialized_users.append({
            "user_id": user_id,
            "user_data": user_data
        })
        return {"points": 0, "level": 1, "achievements": []}
    
    async def get_user_data(self, user_ids):
        """Mock getting user data for gamification."""
        self.user_data_requests.extend(user_ids)
        return [{"user_id": uid, "points": 100} for uid in user_ids]


class MockUserRepository:
    """Mock user repository."""
    
    def __init__(self):
        self.users = {}
    
    async def create(self, user):
        self.users[user.user_id] = user
        return user
    
    async def get_by_user_id(self, user_id):
        return self.users.get(user_id)
    
    async def update(self, user):
        self.users[user.user_id] = user
        return user
    
    async def get_users_for_service(self, user_ids):
        return [self.users[uid] for uid in user_ids if uid in self.users]
    
    async def count_users(self):
        return len(self.users)


@pytest.mark.asyncio
async def test_user_service_provides_data_to_gamification():
    """Test UserService can provide user data to GamificationService."""
    repository = MockUserRepository()
    user_service = UserService(repository, None)
    gamification_service = MockGamificationService()
    
    # Register users in UserService
    users_data = [
        {"id": 123, "first_name": "User1", "language_code": "es"},
        {"id": 456, "first_name": "User2", "language_code": "en"},
        {"id": 789, "first_name": "User3", "language_code": "es"}
    ]
    
    for data in users_data:
        await user_service.register_user(data)
    
    # GamificationService requests user data
    user_ids = [123, 456, 789]
    users = await user_service.get_users_for_service(user_ids)
    
    # Verify correct users returned
    assert len(users) == 3
    assert all(isinstance(user, User) for user in users)
    
    user_map = {user.user_id: user for user in users}
    assert 123 in user_map
    assert 456 in user_map
    assert 789 in user_map
    
    # Verify user data is correct for gamification
    assert user_map[123].first_name == "User1"
    assert user_map[123].language_code == "es"
    assert user_map[456].language_code == "en"


@pytest.mark.asyncio
async def test_user_vip_status_for_gamification():
    """Test VIP status integration with gamification."""
    repository = MockUserRepository()
    user_service = UserService(repository, None)
    
    # Register user
    await user_service.register_user({"id": 123, "first_name": "VIPUser"})
    
    # Check initial VIP status
    is_vip_before = await user_service.is_vip_user(123)
    assert is_vip_before is False
    
    # Set VIP status (could be triggered by gamification achievements)
    await user_service.set_vip_status(123, True)
    
    # Verify VIP status
    is_vip_after = await user_service.is_vip_user(123)
    assert is_vip_after is True
    
    # Get user data for gamification service
    users = await user_service.get_users_for_service([123])
    assert len(users) == 1
    assert users[0].is_vip is True


@pytest.mark.asyncio
async def test_user_preferences_for_gamification():
    """Test user preferences available to gamification service."""
    repository = MockUserRepository()
    user_service = UserService(repository, None)
    
    # Register user
    await user_service.register_user({"id": 123, "first_name": "GamerUser"})
    
    # Set gaming preferences
    gaming_prefs = {
        "achievement_notifications": True,
        "leaderboard_visible": True,
        "difficulty_preference": "normal"
    }
    
    await user_service.update_preferences(123, gaming_prefs)
    
    # Get user for gamification service
    users = await user_service.get_users_for_service([123])
    user = users[0]
    
    # Verify preferences are available
    assert user.preferences["achievement_notifications"] is True
    assert user.preferences["leaderboard_visible"] is True
    assert user.preferences["difficulty_preference"] == "normal"


@pytest.mark.asyncio
async def test_user_language_for_gamification_localization():
    """Test user language preferences for gamification localization."""
    repository = MockUserRepository()
    user_service = UserService(repository, None)
    
    # Register users with different languages
    await user_service.register_user({
        "id": 123, 
        "first_name": "SpanishUser", 
        "language_code": "es"
    })
    
    await user_service.register_user({
        "id": 456, 
        "first_name": "EnglishUser", 
        "language_code": "en"
    })
    
    # Get language preferences for gamification
    spanish_lang = await user_service.get_user_language(123)
    english_lang = await user_service.get_user_language(456)
    
    assert spanish_lang == "es"
    assert english_lang == "en"
    
    # Test default language for non-existent user
    default_lang = await user_service.get_user_language(999)
    assert default_lang == "es"  # Default Spanish


@pytest.mark.asyncio
async def test_bulk_user_activity_for_gamification():
    """Test bulk user activity updates (useful for gamification events)."""
    repository = MockUserRepository()
    user_service = UserService(repository, None)
    
    # Register multiple users
    user_ids = []
    for i in range(5):
        user_id = 100 + i
        await user_service.register_user({
            "id": user_id,
            "first_name": f"User{i}"
        })
        user_ids.append(user_id)
    
    # Simulate gamification event affecting multiple users
    successful_updates = await user_service.bulk_mark_users_active(user_ids)
    assert successful_updates == 5
    
    # Verify all users are marked as active
    users = await user_service.get_users_for_service(user_ids)
    for user in users:
        # All users should have recent activity (updated timestamps)
        assert user.last_active is not None


@pytest.mark.asyncio
async def test_integration_performance_simulation():
    """Test integration performance with realistic load."""
    repository = MockUserRepository()
    user_service = UserService(repository, None)
    
    # Register 100 users (simulating small community)
    user_ids = []
    for i in range(100):
        user_id = 1000 + i
        await user_service.register_user({
            "id": user_id,
            "first_name": f"User{i}",
            "language_code": "es" if i % 2 == 0 else "en"
        })
        user_ids.append(user_id)
    
    # Test bulk retrieval (common gamification scenario)
    batch_size = 20
    for start in range(0, 100, batch_size):
        batch_ids = user_ids[start:start + batch_size]
        users = await user_service.get_users_for_service(batch_ids)
        assert len(users) == min(batch_size, 100 - start)
    
    # Test user count (useful for leaderboards)
    total_users = await user_service.get_user_count()
    assert total_users == 100


if __name__ == "__main__":
    pytest.main([__file__])