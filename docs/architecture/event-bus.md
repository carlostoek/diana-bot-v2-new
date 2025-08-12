# Diana Bot V2 - Event Bus Architecture

## Overview

The Event Bus is the central nervous system of Diana Bot V2, providing a robust, scalable foundation for inter-service communication using event-driven architecture principles. Built on Redis pub/sub with comprehensive error handling, retry logic, and performance monitoring.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)  
3. [Event Types and Structure](#event-types-and-structure)
4. [Event Bus Implementation](#event-bus-implementation)
5. [Error Handling and Resilience](#error-handling-and-resilience)
6. [Performance and Monitoring](#performance-and-monitoring)
7. [Usage Patterns](#usage-patterns)
8. [Best Practices](#best-practices)
9. [Testing Strategy](#testing-strategy)
10. [Deployment Considerations](#deployment-considerations)

## Architecture Overview

### Design Principles

The Event Bus follows Clean Architecture principles with clear separation of concerns:

- **Interface Segregation**: Clear contracts through interfaces (`IEvent`, `IEventBus`, `IEventHandler`)
- **Dependency Inversion**: Depend on abstractions, not concretions
- **Single Responsibility**: Each component has one clear purpose
- **Open/Closed Principle**: Extensible without modifying existing code

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Diana Bot V2                         │
│                                                         │
│  ┌─────────────────┐    ┌─────────────────┐           │
│  │  Gamification   │    │   Narrative     │           │
│  │    Service      │    │    Service      │           │
│  │                 │    │                 │           │
│  │ ┌─────────────┐ │    │ ┌─────────────┐ │    ...    │
│  │ │   Handler   │ │    │ │   Handler   │ │           │
│  │ └─────────────┘ │    │ └─────────────┘ │           │
│  └─────────┬───────┘    └─────────┬───────┘           │
│            │                      │                   │
│            ▼                      ▼                   │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Event Bus                          │   │
│  │                                                 │   │
│  │  ┌─────────────┐  ┌─────────────┐              │   │
│  │  │ Subscription│  │   Message   │              │   │
│  │  │ Management  │  │ Processing  │              │   │
│  │  └─────────────┘  └─────────────┘              │   │
│  │                                                 │   │
│  │  ┌─────────────┐  ┌─────────────┐              │   │
│  │  │ Error       │  │ Performance │              │   │
│  │  │ Handling    │  │ Monitoring  │              │   │
│  │  └─────────────┘  └─────────────┘              │   │
│  └─────────────────┬───────────────────────────────┘   │
│                    │                                   │
│                    ▼                                   │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Redis Pub/Sub                      │   │
│  │                                                 │   │
│  │  Channels: diana:events:{event_type}           │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Event Interface Hierarchy

```python
IEvent (Interface)
├── BaseEvent (Abstract Implementation)
    ├── PointsAwardedEvent
    ├── AchievementUnlockedEvent
    ├── StoryChapterStartedEvent
    ├── UserRegisteredEvent
    └── AdminActionPerformedEvent
```

### 2. Event Bus Interface

```python
IEventBus (Interface)
└── RedisEventBus (Implementation)
```

### 3. Event Handler Interface

```python
IEventHandler (Interface)
└── BaseEventHandler (Abstract Implementation)
    ├── GameHandler (Example)
    ├── NarrativeHandler (Example)
    └── AdminHandler (Example)
```

## Event Types and Structure

### Event Categories

#### Gamification Events
- `gamification.points.awarded` - Points awarded to user
- `gamification.achievement.unlocked` - Achievement unlocked
- `gamification.streak.updated` - Streak progress updated
- `gamification.leaderboard.updated` - Leaderboard changes

#### Narrative Events  
- `narrative.chapter.started` - Story chapter begun
- `narrative.decision.made` - Story decision made
- `narrative.character.interaction` - Character interaction
- `narrative.progress.updated` - Story progress updated

#### User Events
- `user.registered` - New user registered
- `user.profile.updated` - Profile changes
- `user.subscription.changed` - Subscription status change
- `user.activity.detected` - User activity detected

#### Admin Events
- `admin.action.performed` - Admin action executed
- `admin.user.moderated` - User moderation action
- `admin.content.moderated` - Content moderation
- `admin.config.changed` - System configuration change

#### System Events
- `system.service.started` - Service startup
- `system.error.occurred` - System error
- `system.health.failed` - Health check failure

### Event Structure

All events follow a consistent structure:

```python
{
    "event_id": "uuid4-string",
    "event_type": "service.category.action",
    "timestamp": "2024-01-01T12:00:00Z",
    "source_service": "service_name",
    "correlation_id": "optional-correlation-id",
    "priority": "NORMAL|HIGH|CRITICAL",
    "payload": {
        # Event-specific data
    }
}
```

### Event Priority Levels

- **LOW**: Background processing, analytics
- **NORMAL**: Regular user interactions, story progression
- **HIGH**: Achievement unlocks, user registration, important state changes
- **CRITICAL**: System errors, admin actions, security events

## Event Bus Implementation

### RedisEventBus Class

The `RedisEventBus` provides a production-ready implementation with:

#### Core Features
- **Pub/Sub Messaging**: Redis channels for event distribution
- **Subscription Management**: Dynamic subscription/unsubscription
- **Error Handling**: Comprehensive error recovery
- **Retry Logic**: Exponential backoff for failed processing
- **Performance Monitoring**: Built-in metrics tracking
- **Health Monitoring**: Continuous health checks

#### Initialization

```python
from src.core import EventBusConfig, RedisEventBus

config = EventBusConfig(
    redis_url="redis://localhost:6379/0",
    max_retry_attempts=3,
    retry_delay_seconds=1.0,
    health_check_interval_seconds=30
)

event_bus = RedisEventBus(config)
await event_bus.initialize()
```

#### Publishing Events

```python
from src.core import PointsAwardedEvent

event = PointsAwardedEvent(
    user_id=12345,
    points_amount=100,
    action_type="story_completion",
    multiplier=1.5
)

await event_bus.publish(event)
```

#### Subscribing to Events

```python
from src.core import BaseEventHandler, EventType

class GamificationHandler(BaseEventHandler):
    def __init__(self):
        super().__init__("gamification", "points_handler")
        self.add_supported_event_type(EventType.POINTS_AWARDED)

    async def _process_event(self, event: IEvent) -> bool:
        # Process the event
        print(f"Processing {event.event_type}: {event.payload}")
        return True

handler = GamificationHandler()
subscription_id = await event_bus.subscribe(
    EventType.POINTS_AWARDED,
    handler
)
```

## Error Handling and Resilience

### Multi-Layer Error Handling

1. **Validation Layer**: Event validation before processing
2. **Network Layer**: Redis connection failures and retries
3. **Processing Layer**: Handler execution errors and recovery
4. **Circuit Breaker**: Prevent cascading failures

### Retry Strategy

```python
# Exponential backoff with jitter
def calculate_retry_delay(attempt: int, base_delay: float = 1.0) -> float:
    return base_delay * (2 ** attempt) + random.uniform(0, 1)
```

### Error Types and Handling

- **EventValidationError**: Invalid event structure → Reject immediately
- **EventPublishError**: Redis publication failure → Retry with backoff  
- **EventHandlingError**: Handler processing failure → Retry with limits
- **EventSerializationError**: JSON serialization failure → Log and skip

### Dead Letter Queue (Future Enhancement)

Failed events after retry exhaustion will be moved to a dead letter queue for manual inspection and recovery.

## Performance and Monitoring

### Metrics Tracked

#### Event Bus Metrics
- Events published per second
- Events processed per second  
- Events failed per second
- Average processing time
- Success/failure rates
- Active subscriptions count

#### Subscription Metrics
- Handler processing times
- Error rates per handler
- Last processed timestamp
- Queue depths (future)

#### Redis Metrics
- Connection health
- Memory usage
- Network latency
- Pub/sub channel activity

### Health Monitoring

```python
# Get Event Bus health status
metrics = await event_bus.get_metrics()
health = await event_bus.get_subscription_health()

# Example metrics output
{
    "events_published": 1523,
    "events_processed": 1487,
    "events_failed": 36,
    "success_rate": 0.976,
    "average_processing_time_ms": 45.2,
    "active_subscriptions": 12,
    "is_healthy": True
}
```

### Performance Optimizations

1. **Connection Pooling**: Redis connection reuse
2. **Batch Processing**: Group related events
3. **Async Processing**: Non-blocking I/O throughout
4. **Memory Management**: Efficient event serialization
5. **Caching**: Redis-based result caching where appropriate

## Usage Patterns

### 1. Service Integration Pattern

```python
# Service initialization
class GamificationService:
    def __init__(self, event_bus: IEventBus):
        self.event_bus = event_bus
        self.handler = GamificationHandler()

    async def initialize(self):
        # Subscribe to relevant events
        await self.event_bus.subscribe(
            EventType.STORY_CHAPTER_COMPLETED,
            self.handler
        )

    async def award_points(self, user_id: int, amount: int, reason: str):
        # Business logic
        # ...

        # Publish event
        event = PointsAwardedEvent(
            user_id=user_id,
            points_amount=amount,
            action_type=reason
        )
        await self.event_bus.publish(event)
```

### 2. Cross-Service Communication Pattern

```python
# Narrative service publishes decision event
decision_event = StoryDecisionMadeEvent(
    user_id=user_id,
    chapter_id="chapter_1",
    decision_id="save_character",
    consequences={"relationship_boost": 10}
)
await event_bus.publish(decision_event)

# Gamification service handles it
class GameHandler(BaseEventHandler):
    async def _process_event(self, event: StoryDecisionMadeEvent):
        # Award points for story decisions
        if event.consequences.get("relationship_boost"):
            points_event = PointsAwardedEvent(
                user_id=event.user_id,
                points_amount=50,
                action_type="story_decision"
            )
            await self.event_bus.publish(points_event)
        return True
```

### 3. Event Sourcing Pattern

```python
# Store events for audit trail and replay
class EventStore:
    async def store_critical_event(self, event: IEvent):
        if event.priority in [EventPriority.HIGH, EventPriority.CRITICAL]:
            await self.database.store_event(event.to_dict())

    async def replay_events(self, start_time: datetime):
        events = await self.database.get_events(start_time=start_time)
        for event_data in events:
            event = EventFactory.from_dict(event_data)
            await self.event_bus.publish(event)
```

### 4. Saga Pattern for Complex Workflows

```python
# Multi-step user registration saga
class UserRegistrationSaga(BaseEventHandler):
    def __init__(self):
        super().__init__("user_saga", "registration_saga")
        self.add_supported_event_type(EventType.USER_REGISTERED)

    async def _process_event(self, event: UserRegisteredEvent):
        # Step 1: Initialize gamification profile
        gamification_event = # Create gamification init event
        await self.event_bus.publish(gamification_event)

        # Step 2: Send welcome message
        welcome_event = # Create welcome event
        await self.event_bus.publish(welcome_event)

        # Step 3: Start onboarding flow
        onboarding_event = # Create onboarding event
        await self.event_bus.publish(onboarding_event)

        return True
```

## Best Practices

### Event Design

1. **Make Events Immutable**: Events represent facts that have occurred
2. **Include All Necessary Data**: Avoid requiring handlers to make additional queries
3. **Use Descriptive Names**: `user.points.awarded` not `user.updated`
4. **Keep Events Small**: Avoid large payloads that slow down processing
5. **Include Correlation IDs**: Enable tracing across service boundaries

### Handler Implementation

1. **Make Handlers Idempotent**: Safe to process the same event multiple times
2. **Fail Fast**: Validate inputs early and fail quickly for invalid data
3. **Use Structured Logging**: Include event ID and correlation ID in logs
4. **Handle Errors Gracefully**: Don't let one bad event crash the handler
5. **Monitor Performance**: Track processing times and error rates

### Operational Practices

1. **Version Events Carefully**: Changes to event structure require compatibility
2. **Monitor Queue Depths**: Watch for processing bottlenecks
3. **Set Up Alerting**: Alert on error rates, processing delays, connection failures
4. **Plan for Scaling**: Design handlers to scale horizontally
5. **Test Error Scenarios**: Verify retry logic and error handling work correctly

### Security Considerations

1. **Validate All Inputs**: Never trust event data without validation
2. **Sanitize Sensitive Data**: Don't include passwords or tokens in events
3. **Use Correlation IDs Carefully**: Don't expose sensitive user information
4. **Audit Critical Events**: Log admin actions and security-related events
5. **Encrypt at Rest**: Store sensitive event data encrypted

## Testing Strategy

### Unit Tests

Test individual components in isolation:

```python
class TestEventBus:
    @pytest.mark.asyncio
    async def test_publish_event(self, mock_redis, event_bus):
        event = PointsAwardedEvent(user_id=123, points_amount=100, action_type="test")
        result = await event_bus.publish(event)

        assert result is True
        mock_redis.publish.assert_called_once()
```

### Integration Tests  

Test complete workflows:

```python
@pytest.mark.asyncio
async def test_event_workflow(self, event_bus):
    handler = TestHandler()
    await event_bus.subscribe(EventType.POINTS_AWARDED, handler)

    event = PointsAwardedEvent(user_id=123, points_amount=100, action_type="test")
    await event_bus.publish(event)

    # Wait for processing
    await asyncio.sleep(0.1)

    assert len(handler.processed_events) == 1
```

### Performance Tests

Validate system behavior under load:

```python
@pytest.mark.asyncio
async def test_high_throughput(self, event_bus):
    events = [create_test_event() for _ in range(1000)]

    start_time = time.time()
    for event in events:
        await event_bus.publish(event)
    duration = time.time() - start_time

    assert duration < 5.0  # Should handle 1000 events in under 5 seconds
```

## Deployment Considerations

### Redis Configuration

```yaml
# Production Redis settings
redis:
  maxmemory: 2gb
  maxmemory-policy: allkeys-lru
  save: "900 1 300 10 60 10000"
  appendonly: yes
  tcp-keepalive: 300
  timeout: 0
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: diana-event-bus
spec:
  replicas: 3
  selector:
    matchLabels:
      app: diana-event-bus
  template:
    spec:
      containers:
      - name: event-bus
        image: diana-bot:latest
        env:
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-credentials
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

### Monitoring and Alerting

```yaml
# Prometheus alerts
groups:
  - name: event_bus_alerts
    rules:
      - alert: EventProcessingDelayed
        expr: rate(events_processed_total[5m]) < rate(events_published_total[5m]) * 0.9
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Event processing falling behind"

      - alert: HighEventErrorRate
        expr: rate(events_failed_total[5m]) / rate(events_total[5m]) > 0.05
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "High event processing error rate"
```

### Scaling Considerations

1. **Horizontal Scaling**: Multiple Event Bus instances can share Redis
2. **Partitioning**: Use consistent hashing for event distribution
3. **Load Balancing**: Distribute handlers across multiple processes
4. **Connection Pooling**: Share Redis connections across handlers
5. **Circuit Breakers**: Prevent cascading failures during overload

## Migration and Versioning

### Event Schema Evolution

1. **Additive Changes**: New optional fields are safe
2. **Deprecation Process**: Mark old fields as deprecated, maintain compatibility
3. **Breaking Changes**: Require new event type with version suffix
4. **Migration Tools**: Scripts to transform old events to new format

### Backward Compatibility

```python
# Handle multiple event versions
class PointsHandler(BaseEventHandler):
    async def _process_event(self, event: IEvent) -> bool:
        if event.event_type == "points.awarded.v1":
            return await self._handle_v1(event)
        elif event.event_type == "points.awarded.v2":  
            return await self._handle_v2(event)
        else:
            logger.warning(f"Unknown event version: {event.event_type}")
            return False
```

## Conclusion

The Diana Bot V2 Event Bus provides a robust, scalable foundation for event-driven architecture. With comprehensive error handling, performance monitoring, and clean separation of concerns, it enables reliable inter-service communication while maintaining system resilience and observability.

The architecture supports the key requirements:

- ✅ **Scalability**: Handle 100K+ concurrent users
- ✅ **Reliability**: Comprehensive error handling and retry logic
- ✅ **Observability**: Built-in metrics and health monitoring  
- ✅ **Maintainability**: Clean Architecture principles and comprehensive tests
- ✅ **Extensibility**: Easy to add new event types and handlers

This Event Bus will serve as the backbone for all Diana Bot V2 services, enabling loose coupling, high cohesion, and reliable message delivery across the entire system.
