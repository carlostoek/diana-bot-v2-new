"""
Database Transaction Integrity Integration Tests

This module tests the integrity of database transactions across service boundaries,
ensuring that the integration between UserService, GamificationService, and EventBus
maintains data consistency even during complex operations and failure scenarios.
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import pytest
import pytest_asyncio

from core.events import EventBus
from core.interfaces import IEvent
from services.gamification.interfaces import (
    ActionType,
    MultiplierType,
    PointsAwardResult,
)
from services.gamification.service import GamificationService


class MockDatabase:
    """Mock database for testing transaction integrity."""

    def __init__(self):
        self.users = {}
        self.gamification_data = {}
        self.transactions = []
        self.transaction_id_counter = 1000

        # Fault injection
        self.should_fail_next_transaction = False
        self.should_delay_transaction = False
        self.transaction_delay = 0

    async def begin_transaction(self):
        """Begin a new database transaction."""
        transaction_id = self.transaction_id_counter
        self.transaction_id_counter += 1

        self.transactions.append(
            {
                "id": transaction_id,
                "status": "active",
                "operations": [],
                "start_time": datetime.now(timezone.utc),
            }
        )

        return transaction_id

    async def commit_transaction(self, transaction_id):
        """Commit a database transaction."""
        # Find the transaction
        for i, tx in enumerate(self.transactions):
            if tx["id"] == transaction_id and tx["status"] == "active":
                # Simulate transaction delay if enabled
                if self.should_delay_transaction:
                    await asyncio.sleep(self.transaction_delay)

                # Simulate transaction failure if enabled
                if self.should_fail_next_transaction:
                    self.should_fail_next_transaction = (
                        False  # Reset for next transaction
                    )
                    tx["status"] = "failed"
                    raise Exception(
                        f"Simulated transaction failure for TX-{transaction_id}"
                    )

                # Normal commit
                tx["status"] = "committed"
                tx["commit_time"] = datetime.now(timezone.utc)
                return True

        raise Exception(f"Transaction {transaction_id} not found or not active")

    async def rollback_transaction(self, transaction_id):
        """Rollback a database transaction."""
        for i, tx in enumerate(self.transactions):
            if tx["id"] == transaction_id and tx["status"] == "active":
                tx["status"] = "rolled_back"
                tx["rollback_time"] = datetime.now(timezone.utc)
                return True

        raise Exception(f"Transaction {transaction_id} not found or not active")

    async def record_operation(self, transaction_id, operation_type, data):
        """Record an operation within a transaction."""
        for tx in self.transactions:
            if tx["id"] == transaction_id and tx["status"] == "active":
                tx["operations"].append(
                    {
                        "type": operation_type,
                        "data": data,
                        "time": datetime.now(timezone.utc),
                    }
                )
                return True

        raise Exception(f"Transaction {transaction_id} not found or not active")

    async def get_user(self, user_id):
        """Get user data."""
        return self.users.get(user_id, None)

    async def get_gamification_data(self, user_id):
        """Get gamification data for user."""
        return self.gamification_data.get(user_id, None)

    async def create_user(self, transaction_id, user_data):
        """Create a new user within a transaction."""
        user_id = user_data["user_id"]
        await self.record_operation(transaction_id, "create_user", user_data)

        self.users[user_id] = user_data
        return user_id

    async def update_user(self, transaction_id, user_id, update_data):
        """Update user data within a transaction."""
        await self.record_operation(
            transaction_id, "update_user", {"user_id": user_id, "updates": update_data}
        )

        if user_id in self.users:
            self.users[user_id].update(update_data)
            return True
        return False

    async def create_gamification_profile(self, transaction_id, user_id, profile_data):
        """Create gamification profile within a transaction."""
        await self.record_operation(
            transaction_id,
            "create_gamification_profile",
            {"user_id": user_id, "profile": profile_data},
        )

        self.gamification_data[user_id] = profile_data
        return True

    async def update_gamification_data(self, transaction_id, user_id, update_data):
        """Update gamification data within a transaction."""
        await self.record_operation(
            transaction_id,
            "update_gamification_data",
            {"user_id": user_id, "updates": update_data},
        )

        if user_id in self.gamification_data:
            self.gamification_data[user_id].update(update_data)
            return True
        return False

    async def record_points_transaction(self, transaction_id, points_data):
        """Record a points transaction."""
        await self.record_operation(transaction_id, "points_transaction", points_data)

        user_id = points_data["user_id"]
        points = points_data["points"]

        if user_id in self.gamification_data:
            if "points" not in self.gamification_data[user_id]:
                self.gamification_data[user_id]["points"] = 0

            self.gamification_data[user_id]["points"] += points

            if "points_history" not in self.gamification_data[user_id]:
                self.gamification_data[user_id]["points_history"] = []

            self.gamification_data[user_id]["points_history"].append(points_data)

            return True
        return False


class TransactionAwareGamificationService(GamificationService):
    """Extension of GamificationService with explicit transaction support for testing."""

    def __init__(self, event_bus, database):
        super().__init__(event_bus=event_bus)
        self.database = database

    async def award_points_transactional(
        self, user_id: int, action_type: ActionType, points: int
    ) -> Tuple[bool, Optional[PointsAwardResult]]:
        """Award points with explicit transaction control."""
        try:
            # Begin transaction
            tx_id = await self.database.begin_transaction()

            try:
                # Check if user exists
                user_data = await self.database.get_user(user_id)
                if not user_data:
                    # Create user if not exists
                    await self.database.create_user(
                        tx_id,
                        {"user_id": user_id, "created_at": datetime.now(timezone.utc)},
                    )

                # Check if gamification profile exists
                gam_data = await self.database.get_gamification_data(user_id)
                if not gam_data:
                    # Create gamification profile
                    await self.database.create_gamification_profile(
                        tx_id,
                        user_id,
                        {"points": 0, "created_at": datetime.now(timezone.utc)},
                    )

                # Record points transaction
                await self.database.record_points_transaction(
                    tx_id,
                    {
                        "user_id": user_id,
                        "points": points,
                        "action_type": action_type.value,
                        "timestamp": datetime.now(timezone.utc),
                    },
                )

                # Commit transaction
                await self.database.commit_transaction(tx_id)

                # Return success result
                result = PointsAwardResult(
                    success=True,
                    user_id=user_id,
                    action_type=action_type,
                    points_awarded=points,
                    base_points=points,
                    multipliers_applied={},
                    new_balance=(
                        gam_data.get("points", 0) + points if gam_data else points
                    ),
                )

                # Publish event to Event Bus
                from core.events import GameEvent

                event = GameEvent(
                    user_id=user_id,
                    action="points_awarded",
                    points_earned=points,
                    context={"action_type": action_type.value, "transaction_id": tx_id},
                )

                try:
                    await self.event_bus.publish(event)
                except Exception as e:
                    # Log but don't fail the transaction - events are eventual consistency
                    print(f"Failed to publish event: {e}")

                return True, result

            except Exception as e:
                # Rollback on error
                await self.database.rollback_transaction(tx_id)
                raise e

        except Exception as e:
            print(f"Transaction failed: {e}")
            return False, None


class MockUserService:
    """Mock UserService with transaction support for testing."""

    def __init__(self, event_bus, database):
        self.event_bus = event_bus
        self.database = database
        self._initialized = False
        self.event_handlers = {}

    async def initialize(self):
        """Initialize the service."""
        if self._initialized:
            return

        # Set up event handlers
        handler = self._handle_points_awarded
        await self.event_bus.subscribe("game.points_awarded", handler)
        self.event_handlers["game.points_awarded"] = handler

        self._initialized = True

    async def cleanup(self):
        """Clean up resources."""
        if not self._initialized:
            return

        # Clean up subscriptions
        for pattern, handler in self.event_handlers.items():
            await self.event_bus.unsubscribe(pattern, handler)

        self._initialized = False

    async def _handle_points_awarded(self, event: IEvent):
        """Handle points awarded events."""
        event_data = event.data
        user_id = event_data.get("user_id")
        points = event_data.get("points_earned", 0)

        if not user_id:
            return

        try:
            # Begin transaction to update user record
            tx_id = await self.database.begin_transaction()

            try:
                # Get user data
                user_data = await self.database.get_user(user_id)
                if not user_data:
                    # User doesn't exist, create it
                    await self.database.create_user(
                        tx_id,
                        {
                            "user_id": user_id,
                            "created_at": datetime.now(timezone.utc),
                            "points": 0,
                        },
                    )
                    user_data = {"points": 0}

                # Update user points data
                current_points = user_data.get("points", 0)
                await self.database.update_user(
                    tx_id,
                    user_id,
                    {
                        "points": current_points + points,
                        "last_points_update": datetime.now(timezone.utc),
                    },
                )

                # Commit transaction
                await self.database.commit_transaction(tx_id)

            except Exception as e:
                # Rollback on error
                await self.database.rollback_transaction(tx_id)
                raise e

        except Exception as e:
            print(f"Error updating user points: {e}")

    async def create_user_transactional(self, user_id, first_name, username=None):
        """Create a user with transaction support."""
        try:
            # Begin transaction
            tx_id = await self.database.begin_transaction()

            try:
                # Create user
                await self.database.create_user(
                    tx_id,
                    {
                        "user_id": user_id,
                        "first_name": first_name,
                        "username": username,
                        "created_at": datetime.now(timezone.utc),
                        "points": 0,
                    },
                )

                # Commit transaction
                await self.database.commit_transaction(tx_id)

                # Publish event
                from modules.user.events import UserCreatedEvent

                event = UserCreatedEvent(
                    user_id=user_id,
                    first_name=first_name,
                    username=username,
                    language_code="en",
                )

                await self.event_bus.publish(event)

                return True

            except Exception as e:
                # Rollback on error
                await self.database.rollback_transaction(tx_id)
                raise e

        except Exception as e:
            print(f"Failed to create user: {e}")
            return False


class TestDatabaseTransactionIntegration:
    """Test database transaction integrity across service boundaries."""

    @pytest_asyncio.fixture
    async def database(self):
        """Create a mock database for testing."""
        return MockDatabase()

    @pytest_asyncio.fixture
    async def event_bus(self):
        """Create an Event Bus for testing."""
        bus = EventBus(test_mode=True)
        await bus.initialize()
        yield bus
        await bus.cleanup()

    @pytest_asyncio.fixture
    async def gamification_service(self, event_bus, database):
        """Create a GamificationService with database for testing."""
        service = TransactionAwareGamificationService(event_bus, database)
        await service.initialize()
        yield service
        await service.cleanup()

    @pytest_asyncio.fixture
    async def user_service(self, event_bus, database):
        """Create a UserService with database for testing."""
        service = MockUserService(event_bus, database)
        await service.initialize()
        yield service
        await service.cleanup()

    @pytest.mark.asyncio
    async def test_basic_transaction_integrity(
        self, database, event_bus, user_service, gamification_service
    ):
        """Test basic transaction integrity for user creation and points award."""
        user_id = int(uuid.uuid4().int % 100000000)

        # Create user
        success = await user_service.create_user_transactional(
            user_id=user_id, first_name="TransactionUser", username="tx_user"
        )
        assert success is True, "Failed to create user"

        # Verify user exists in database
        user_data = await database.get_user(user_id)
        assert user_data is not None, "User not created in database"
        assert user_data["first_name"] == "TransactionUser"

        # Award points
        success, result = await gamification_service.award_points_transactional(
            user_id=user_id, action_type=ActionType.LOGIN, points=50
        )
        assert success is True, "Failed to award points"
        assert result.points_awarded == 50

        # Allow events to process
        await asyncio.sleep(0.1)

        # Verify gamification data in database
        gam_data = await database.get_gamification_data(user_id)
        assert gam_data is not None, "Gamification data not created"
        assert gam_data["points"] == 50, "Points not recorded correctly"

        # Verify user data also updated via event
        user_data = await database.get_user(user_id)
        assert user_data["points"] == 50, "User points not updated via event"

    @pytest.mark.asyncio
    async def test_transaction_rollback(
        self, database, event_bus, gamification_service
    ):
        """Test transaction rollback on failure."""
        user_id = int(uuid.uuid4().int % 100000000)

        # Create initial user data
        tx_id = await database.begin_transaction()
        await database.create_user(
            tx_id, {"user_id": user_id, "first_name": "RollbackUser", "points": 100}
        )
        await database.create_gamification_profile(
            tx_id, user_id, {"points": 100, "created_at": datetime.now(timezone.utc)}
        )
        await database.commit_transaction(tx_id)

        # Set database to fail next transaction
        database.should_fail_next_transaction = True

        # Attempt to award points - should fail
        success, result = await gamification_service.award_points_transactional(
            user_id=user_id, action_type=ActionType.TRIVIA_COMPLETED, points=200
        )
        assert success is False, "Transaction should have failed"

        # Verify data was not changed
        gam_data = await database.get_gamification_data(user_id)
        assert (
            gam_data["points"] == 100
        ), "Points should not have changed after rollback"

        # Verify transaction was recorded as rolled back
        found_rolled_back = False
        for tx in database.transactions:
            if tx["status"] == "rolled_back":
                found_rolled_back = True
                break

        assert found_rolled_back, "No rolled back transaction found"

    @pytest.mark.asyncio
    async def test_concurrent_transactions(
        self, database, event_bus, gamification_service
    ):
        """Test concurrent transactions between services."""
        user_id = int(uuid.uuid4().int % 100000000)

        # Create initial user
        tx_id = await database.begin_transaction()
        await database.create_user(
            tx_id, {"user_id": user_id, "first_name": "ConcurrentUser", "points": 0}
        )
        await database.create_gamification_profile(
            tx_id, user_id, {"points": 0, "created_at": datetime.now(timezone.utc)}
        )
        await database.commit_transaction(tx_id)

        # Set transaction delay to simulate concurrent operations
        database.should_delay_transaction = True
        database.transaction_delay = 0.2

        # Start multiple concurrent point award operations
        task1 = asyncio.create_task(
            gamification_service.award_points_transactional(
                user_id=user_id, action_type=ActionType.LOGIN, points=10
            )
        )

        task2 = asyncio.create_task(
            gamification_service.award_points_transactional(
                user_id=user_id, action_type=ActionType.MESSAGE_SENT, points=20
            )
        )

        task3 = asyncio.create_task(
            gamification_service.award_points_transactional(
                user_id=user_id, action_type=ActionType.TRIVIA_COMPLETED, points=30
            )
        )

        # Wait for all tasks to complete
        results = await asyncio.gather(task1, task2, task3)

        # Reset delay
        database.should_delay_transaction = False

        # Allow events to process
        await asyncio.sleep(0.2)

        # Check all transactions completed
        success_count = sum(1 for success, _ in results if success)
        assert success_count == 3, f"Not all transactions succeeded: {success_count}/3"

        # Verify final points - should be sum of all awards
        gam_data = await database.get_gamification_data(user_id)
        assert (
            gam_data["points"] == 60
        ), f"Points mismatch: expected 60, got {gam_data['points']}"

        # Verify all transactions were recorded
        committed_count = sum(
            1 for tx in database.transactions if tx["status"] == "committed"
        )
        assert (
            committed_count >= 4
        ), f"Expected at least 4 committed transactions, got {committed_count}"

    @pytest.mark.asyncio
    async def test_cross_service_transaction_consistency(
        self, database, event_bus, user_service, gamification_service
    ):
        """Test consistency between services when transactions span service boundaries."""
        user_id = int(uuid.uuid4().int % 100000000)

        # Create user
        await user_service.create_user_transactional(
            user_id=user_id, first_name="ConsistencyUser", username="consistency_test"
        )

        # Allow event processing
        await asyncio.sleep(0.1)

        # Award points multiple times
        total_points = 0
        for i in range(5):
            points = (i + 1) * 10
            total_points += points

            success, result = await gamification_service.award_points_transactional(
                user_id=user_id, action_type=ActionType.LOGIN, points=points
            )
            assert success is True, f"Failed to award points in iteration {i}"

            # Allow event processing
            await asyncio.sleep(0.1)

        # Verify consistency between services
        user_data = await database.get_user(user_id)
        gam_data = await database.get_gamification_data(user_id)

        assert (
            user_data["points"] == total_points
        ), f"User points mismatch: expected {total_points}, got {user_data['points']}"

        assert (
            gam_data["points"] == total_points
        ), f"Gamification points mismatch: expected {total_points}, got {gam_data['points']}"

        # Verify transaction history
        assert (
            len(gam_data["points_history"]) == 5
        ), f"Expected 5 point transactions, got {len(gam_data['points_history'])}"

    @pytest.mark.asyncio
    async def test_transaction_with_event_bus_failure(
        self, database, event_bus, gamification_service
    ):
        """Test transaction integrity when Event Bus fails."""
        user_id = int(uuid.uuid4().int % 100000000)

        # Create initial user
        tx_id = await database.begin_transaction()
        await database.create_user(
            tx_id,
            {"user_id": user_id, "first_name": "EventBusFailureUser", "points": 50},
        )
        await database.create_gamification_profile(
            tx_id, user_id, {"points": 50, "created_at": datetime.now(timezone.utc)}
        )
        await database.commit_transaction(tx_id)

        # Disconnect Event Bus
        original_connected = event_bus._is_connected
        event_bus._is_connected = False

        try:
            # Attempt to award points
            # Should succeed in database but fail to publish event
            success, result = await gamification_service.award_points_transactional(
                user_id=user_id, action_type=ActionType.LOGIN, points=25
            )

            # Transaction should succeed even if event publishing fails
            assert (
                success is True
            ), "Transaction should succeed despite Event Bus failure"

            # Verify points were awarded in database
            gam_data = await database.get_gamification_data(user_id)
            assert (
                gam_data["points"] == 75
            ), "Points should be updated despite Event Bus failure"

            # But user data won't be updated since event didn't go through
            user_data = await database.get_user(user_id)
            assert (
                user_data["points"] == 50
            ), "User points shouldn't update without event"

        finally:
            # Restore Event Bus connection
            event_bus._is_connected = original_connected
