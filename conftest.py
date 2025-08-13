"""
Pytest configuration and shared fixtures for Diana Bot V2.

This module provides common test fixtures and configuration for all tests.
"""

import asyncio
import os
import tempfile
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.core.event_bus import RedisEventBus
from src.models.gamification import Base
from src.services.gamification.repository import GamificationRepository
from src.services.gamification.service import GamificationService


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db_engine():
    """Create a test database engine with in-memory SQLite."""
    # Use in-memory SQLite for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        pool_pre_ping=True,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest.fixture
async def test_db_session(test_db_engine):
    """Create a test database session."""
    async_session = sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session


@pytest.fixture
async def mock_event_bus():
    """Create a mock event bus for testing."""
    mock_bus = Mock(spec=RedisEventBus)
    mock_bus.publish = AsyncMock()
    mock_bus.subscribe = AsyncMock()
    mock_bus.start_consuming = AsyncMock()
    mock_bus.stop_consuming = AsyncMock()
    mock_bus.health_check = AsyncMock(return_value=True)
    return mock_bus


@pytest.fixture
async def test_repository(test_db_engine):
    """Create a test gamification repository."""
    repo = GamificationRepository("sqlite+aiosqlite:///:memory:")

    # Override the engine with our test engine
    repo.engine = test_db_engine
    repo.async_session = sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    yield repo

    # Cleanup
    if repo.engine:
        await repo.engine.dispose()


@pytest.fixture
async def test_gamification_service(test_repository, mock_event_bus):
    """Create a test gamification service."""
    service = GamificationService(repository=test_repository, event_bus=mock_event_bus)
    yield service


@pytest.fixture
def mock_user_data():
    """Sample user data for testing."""
    return {
        "user_id": 12345,
        "username": "test_user",
        "first_name": "Test",
        "last_name": "User",
        "is_vip": False,
    }


@pytest.fixture
def sample_achievement_data():
    """Sample achievement data for testing."""
    return {
        "achievement_id": "first_steps",
        "name": "First Steps",
        "description": "Complete your first story chapter",
        "category": "story",
        "tier": "bronze",
        "criteria": {"chapters_completed": 1},
        "points_reward": 100,
        "is_active": True,
    }


@pytest.fixture
def sample_points_transaction():
    """Sample points transaction data for testing."""
    return {
        "user_id": 12345,
        "amount": 50,
        "transaction_type": "story_completion",
        "description": "Completed chapter 1",
        "source_event_id": "evt_123",
    }


@pytest.fixture
def current_time():
    """Current timestamp for testing."""
    return datetime.now(timezone.utc)


# Test configuration
def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


# Async test helper
def pytest_collection_modifyitems(config, items):
    """Add asyncio marker to async tests."""
    for item in items:
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)
