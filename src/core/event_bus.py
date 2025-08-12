"""
Core Event Bus implementation for Diana Bot V2.

This module provides the central Event Bus system with Redis pub/sub backend,
comprehensive error handling, retry logic, and subscription management.
Implements Clean Architecture principles with proper separation of concerns.
"""

import asyncio
import json
import logging
import time
import traceback
from typing import Any, Dict, List, Optional, Set, Callable, Tuple
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import uuid

import redis.asyncio as aioredis
from redis.asyncio.client import PubSub

from .interfaces import (
    IEvent,
    IEventBus,
    IEventHandler,
    IEventStore,
    IEventMetrics,
    EventBusConfig,
    EventPublishError,
    EventSubscriptionError,
    EventHandlingError,
    EventValidationError,
    EventPriority
)
from .events import EventFactory


logger = logging.getLogger(__name__)


@dataclass
class Subscription:
    """Represents an active event subscription."""
    
    subscription_id: str
    event_type: str
    handler: IEventHandler
    service_name: Optional[str]
    created_at: datetime
    last_processed: Optional[datetime] = None
    success_count: int = 0
    error_count: int = 0
    is_active: bool = True


@dataclass 
class EventProcessingResult:
    """Result of event processing."""
    
    success: bool
    processing_time: float
    error: Optional[Exception] = None
    retry_count: int = 0


class RedisEventBus(IEventBus):
    """
    Redis-backed Event Bus implementation.
    
    Provides scalable pub/sub messaging with comprehensive error handling,
    retry logic, and subscription management.
    """
    
    def __init__(self, config: EventBusConfig):
        self.config = config
        self._redis: Optional[aioredis.Redis] = None
        self._pubsub: Optional[PubSub] = None
        self._subscriptions: Dict[str, Subscription] = {}
        self._event_handlers: Dict[str, List[str]] = {}  # event_type -> subscription_ids
        self._processing_tasks: Set[asyncio.Task] = set()
        self._shutdown_event = asyncio.Event()
        self._health_check_task: Optional[asyncio.Task] = None
        self._is_initialized = False
        
        # Metrics tracking
        self._metrics = {
            'events_published': 0,
            'events_processed': 0,
            'events_failed': 0,
            'processing_time_total': 0.0,
            'last_activity': datetime.utcnow()
        }
        
        # Event store for persistence (optional)
        self._event_store: Optional[IEventStore] = None
        
        logger.info(f"EventBus initialized with config: Redis={config.redis_url}")
    
    async def initialize(self) -> None:
        """Initialize the event bus and establish Redis connections."""
        if self._is_initialized:
            logger.warning("EventBus already initialized")
            return
        
        try:
            # Initialize Redis connection
            self._redis = aioredis.from_url(
                self.config.redis_url,
                decode_responses=True,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self._redis.ping()
            logger.info("Redis connection established successfully")
            
            # Initialize pub/sub
            self._pubsub = self._redis.pubsub()
            
            # Start background tasks
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            self._is_initialized = True
            logger.info("EventBus initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize EventBus: {str(e)}")
            await self._cleanup_resources()
            raise EventSubscriptionError(f"EventBus initialization failed: {str(e)}")
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the event bus and clean up resources."""
        logger.info("Starting EventBus shutdown...")
        
        # Signal shutdown to all background tasks
        self._shutdown_event.set()
        
        # Cancel health check task
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Wait for processing tasks to complete (with timeout)
        if self._processing_tasks:
            logger.info(f"Waiting for {len(self._processing_tasks)} processing tasks to complete...")
            done, pending = await asyncio.wait(
                self._processing_tasks, 
                timeout=10.0, 
                return_when=asyncio.ALL_COMPLETED
            )
            
            # Cancel any remaining tasks
            for task in pending:
                task.cancel()
        
        # Clean up resources
        await self._cleanup_resources()
        
        self._is_initialized = False
        logger.info("EventBus shutdown completed")
    
    async def _cleanup_resources(self) -> None:
        """Clean up Redis connections and resources."""
        if self._pubsub:
            try:
                await self._pubsub.close()
            except Exception as e:
                logger.warning(f"Error closing pubsub: {str(e)}")
        
        if self._redis:
            try:
                await self._redis.close()
            except Exception as e:
                logger.warning(f"Error closing Redis connection: {str(e)}")
    
    async def publish(
        self, 
        event: IEvent,
        target_services: Optional[List[str]] = None
    ) -> bool:
        """
        Publish an event to the bus.
        
        Args:
            event: The event to publish
            target_services: Optional list of specific services to target
            
        Returns:
            True if published successfully
            
        Raises:
            EventPublishError: If publishing fails
        """
        if not self._is_initialized or not self._redis:
            raise EventPublishError("EventBus not initialized", event.event_id)
        
        start_time = time.time()
        
        try:
            # Validate event
            if not event.validate():
                raise EventValidationError(f"Event validation failed: {event.event_id}")
            
            # Prepare message
            message_data = {
                'event': event.to_dict(),
                'target_services': target_services,
                'published_at': datetime.utcnow().isoformat(),
                'message_id': str(uuid.uuid4())
            }
            
            message_json = json.dumps(message_data)
            
            # Determine Redis channel
            channel = self._get_channel_name(event.event_type)
            
            # Publish to Redis
            subscribers = await self._redis.publish(channel, message_json)
            
            # Store event if persistence is enabled
            if self.config.event_store_enabled and self._event_store:
                await self._event_store.store_event(event)
            
            # Update metrics
            processing_time = time.time() - start_time
            self._metrics['events_published'] += 1
            self._metrics['processing_time_total'] += processing_time
            self._metrics['last_activity'] = datetime.utcnow()
            
            logger.debug(
                f"Event published successfully: {event.event_id} "
                f"(type: {event.event_type}, subscribers: {subscribers})"
            )
            
            return True
            
        except Exception as e:
            processing_time = time.time() - start_time
            self._metrics['events_failed'] += 1
            
            logger.error(
                f"Failed to publish event {event.event_id}: {str(e)}\n"
                f"Processing time: {processing_time:.3f}s"
            )
            
            raise EventPublishError(
                f"Failed to publish event: {str(e)}", 
                event.event_id
            ) from e
    
    async def subscribe(
        self,
        event_type: str,
        handler: IEventHandler,
        service_name: Optional[str] = None
    ) -> str:
        """
        Subscribe to events of a specific type.
        
        Args:
            event_type: Type of events to subscribe to
            handler: Handler to process the events
            service_name: Optional service name filter
            
        Returns:
            Subscription ID for managing the subscription
            
        Raises:
            EventSubscriptionError: If subscription fails
        """
        if not self._is_initialized or not self._pubsub:
            raise EventSubscriptionError("EventBus not initialized")
        
        try:
            # Create subscription
            subscription_id = str(uuid.uuid4())
            subscription = Subscription(
                subscription_id=subscription_id,
                event_type=event_type,
                handler=handler,
                service_name=service_name,
                created_at=datetime.utcnow()
            )
            
            # Register subscription
            self._subscriptions[subscription_id] = subscription
            
            # Add to event type mapping
            if event_type not in self._event_handlers:
                self._event_handlers[event_type] = []
                # Subscribe to Redis channel for this event type
                channel = self._get_channel_name(event_type)
                await self._pubsub.subscribe(channel)
                
                # Start message processing task if it's the first subscription
                if len(self._event_handlers) == 1:
                    task = asyncio.create_task(self._message_processing_loop())
                    self._processing_tasks.add(task)
            
            self._event_handlers[event_type].append(subscription_id)
            
            logger.info(
                f"Subscription created: {subscription_id} "
                f"(event_type: {event_type}, handler: {handler.handler_id})"
            )
            
            return subscription_id
            
        except Exception as e:
            logger.error(f"Failed to create subscription: {str(e)}")
            raise EventSubscriptionError(f"Subscription failed: {str(e)}") from e
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """
        Remove a subscription.
        
        Args:
            subscription_id: ID of the subscription to remove
            
        Returns:
            True if unsubscribed successfully
        """
        if subscription_id not in self._subscriptions:
            logger.warning(f"Subscription not found: {subscription_id}")
            return False
        
        try:
            subscription = self._subscriptions[subscription_id]
            event_type = subscription.event_type
            
            # Remove from subscriptions
            del self._subscriptions[subscription_id]
            
            # Remove from event type mapping
            if event_type in self._event_handlers:
                self._event_handlers[event_type].remove(subscription_id)
                
                # If no more handlers for this event type, unsubscribe from Redis
                if not self._event_handlers[event_type]:
                    del self._event_handlers[event_type]
                    channel = self._get_channel_name(event_type)
                    if self._pubsub:
                        await self._pubsub.unsubscribe(channel)
            
            logger.info(f"Subscription removed: {subscription_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe {subscription_id}: {str(e)}")
            return False
    
    async def get_active_subscriptions(self) -> Dict[str, List[str]]:
        """Get all active subscriptions grouped by event type."""
        return {
            event_type: subscription_ids.copy() 
            for event_type, subscription_ids in self._event_handlers.items()
        }
    
    async def get_subscription_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all subscriptions."""
        health_data = {}
        
        for sub_id, subscription in self._subscriptions.items():
            health_data[sub_id] = {
                'event_type': subscription.event_type,
                'service_name': subscription.service_name,
                'handler_id': subscription.handler.handler_id,
                'created_at': subscription.created_at.isoformat(),
                'last_processed': subscription.last_processed.isoformat() if subscription.last_processed else None,
                'success_count': subscription.success_count,
                'error_count': subscription.error_count,
                'error_rate': subscription.error_count / max(1, subscription.success_count + subscription.error_count),
                'is_active': subscription.is_active
            }
        
        return health_data
    
    def _get_channel_name(self, event_type: str) -> str:
        """Get Redis channel name for an event type."""
        return f"diana:events:{event_type}"
    
    async def _message_processing_loop(self) -> None:
        """Main message processing loop."""
        logger.info("Starting message processing loop")
        
        try:
            async for message in self._pubsub.listen():
                if self._shutdown_event.is_set():
                    break
                
                if message['type'] == 'message':
                    # Process message in background
                    task = asyncio.create_task(self._process_message(message))
                    self._processing_tasks.add(task)
                    # Clean up completed tasks
                    self._processing_tasks = {t for t in self._processing_tasks if not t.done()}
                    
        except Exception as e:
            logger.error(f"Error in message processing loop: {str(e)}")
        finally:
            logger.info("Message processing loop stopped")
    
    async def _process_message(self, message: Dict[str, Any]) -> None:
        """Process a single message from Redis."""
        try:
            # Parse message data
            message_data = json.loads(message['data'])
            event_data = message_data['event']
            target_services = message_data.get('target_services')
            
            # Recreate event object
            event = EventFactory.from_dict(event_data)
            
            # Find relevant subscriptions
            event_type = event.event_type
            if event_type not in self._event_handlers:
                return
            
            # Process with each handler
            tasks = []
            for subscription_id in self._event_handlers[event_type]:
                if subscription_id in self._subscriptions:
                    subscription = self._subscriptions[subscription_id]
                    
                    # Check service filter
                    if target_services and subscription.service_name:
                        if subscription.service_name not in target_services:
                            continue
                    
                    # Create processing task
                    task = asyncio.create_task(
                        self._handle_event_with_retry(event, subscription)
                    )
                    tasks.append(task)
            
            # Wait for all handlers to complete
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Log any exceptions
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Handler task failed: {str(result)}")
                        
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}\n{traceback.format_exc()}")
    
    async def _handle_event_with_retry(
        self, 
        event: IEvent, 
        subscription: Subscription
    ) -> EventProcessingResult:
        """Handle an event with retry logic."""
        retry_count = 0
        last_error = None
        
        while retry_count <= self.config.max_retry_attempts:
            start_time = time.time()
            
            try:
                # Check if handler can process this event
                if not await subscription.handler.can_handle(event):
                    return EventProcessingResult(
                        success=False,
                        processing_time=time.time() - start_time,
                        error=EventHandlingError("Handler cannot process event", event.event_id)
                    )
                
                # Process the event
                result = await subscription.handler.handle(event)
                processing_time = time.time() - start_time
                
                if result:
                    # Success
                    subscription.success_count += 1
                    subscription.last_processed = datetime.utcnow()
                    
                    # Update metrics
                    self._metrics['events_processed'] += 1
                    self._metrics['processing_time_total'] += processing_time
                    self._metrics['last_activity'] = datetime.utcnow()
                    
                    logger.debug(
                        f"Event processed successfully: {event.event_id} "
                        f"by {subscription.handler.handler_id} "
                        f"(time: {processing_time:.3f}s, retries: {retry_count})"
                    )
                    
                    return EventProcessingResult(
                        success=True,
                        processing_time=processing_time,
                        retry_count=retry_count
                    )
                else:
                    # Handler returned False - treat as error
                    last_error = EventHandlingError(
                        "Handler returned False", 
                        event.event_id, 
                        subscription.handler.handler_id
                    )
                    
            except Exception as e:
                last_error = e
                processing_time = time.time() - start_time
                
                # Let handler handle the error
                try:
                    should_retry = await subscription.handler.on_error(event, e)
                    if not should_retry:
                        break
                except Exception as handler_error:
                    logger.error(f"Handler error callback failed: {str(handler_error)}")
                    break
            
            # Retry logic
            retry_count += 1
            if retry_count <= self.config.max_retry_attempts:
                delay = self.config.retry_delay_seconds * (2 ** (retry_count - 1))  # Exponential backoff
                logger.warning(
                    f"Retrying event {event.event_id} in {delay}s "
                    f"(attempt {retry_count}/{self.config.max_retry_attempts})"
                )
                await asyncio.sleep(delay)
        
        # All retries exhausted
        subscription.error_count += 1
        self._metrics['events_failed'] += 1
        
        logger.error(
            f"Event processing failed permanently: {event.event_id} "
            f"by {subscription.handler.handler_id} "
            f"after {retry_count} attempts. Last error: {str(last_error)}"
        )
        
        return EventProcessingResult(
            success=False,
            processing_time=time.time() - start_time,
            error=last_error,
            retry_count=retry_count
        )
    
    async def _health_check_loop(self) -> None:
        """Background task for health monitoring."""
        logger.info("Starting health check loop")
        
        while not self._shutdown_event.is_set():
            try:
                # Check Redis connection
                if self._redis:
                    await self._redis.ping()
                
                # Check subscription health
                unhealthy_subscriptions = []
                for sub_id, subscription in self._subscriptions.items():
                    total_events = subscription.success_count + subscription.error_count
                    if total_events > 10:  # Only check if enough events processed
                        error_rate = subscription.error_count / total_events
                        if error_rate > 0.1:  # More than 10% error rate
                            unhealthy_subscriptions.append(sub_id)
                
                if unhealthy_subscriptions:
                    logger.warning(
                        f"Unhealthy subscriptions detected: {unhealthy_subscriptions}"
                    )
                
                # Log metrics
                logger.debug(f"EventBus metrics: {self._metrics}")
                
                # Wait for next check
                await asyncio.sleep(self.config.health_check_interval_seconds)
                
            except Exception as e:
                logger.error(f"Health check error: {str(e)}")
                await asyncio.sleep(self.config.health_check_interval_seconds)
        
        logger.info("Health check loop stopped")
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get current Event Bus metrics."""
        avg_processing_time = 0.0
        total_events = self._metrics['events_processed'] + self._metrics['events_failed']
        
        if total_events > 0:
            avg_processing_time = self._metrics['processing_time_total'] / total_events
        
        return {
            'events_published': self._metrics['events_published'],
            'events_processed': self._metrics['events_processed'], 
            'events_failed': self._metrics['events_failed'],
            'success_rate': self._metrics['events_processed'] / max(1, total_events),
            'average_processing_time_ms': avg_processing_time * 1000,
            'active_subscriptions': len(self._subscriptions),
            'event_types_subscribed': len(self._event_handlers),
            'last_activity': self._metrics['last_activity'].isoformat(),
            'is_healthy': self._is_initialized and self._redis is not None
        }


# Event Handler Base Class with Common Functionality
class BaseEventHandler(IEventHandler):
    """
    Base implementation of IEventHandler with common functionality.
    
    Provides default implementations for common handler operations
    and error handling patterns.
    """
    
    def __init__(self, service_name: str, handler_id: Optional[str] = None):
        self._service_name = service_name
        self._handler_id = handler_id or f"{service_name}_{str(uuid.uuid4())[:8]}"
        self._supported_events: List[str] = []
        
        # Performance tracking
        self._processing_count = 0
        self._error_count = 0
        self._total_processing_time = 0.0
        self._last_processed: Optional[datetime] = None
    
    @property
    def handler_id(self) -> str:
        return self._handler_id
    
    @property
    def service_name(self) -> str:
        return self._service_name
    
    @property
    def supported_event_types(self) -> List[str]:
        return self._supported_events.copy()
    
    async def can_handle(self, event: IEvent) -> bool:
        """Default implementation checks supported event types."""
        return event.event_type in self._supported_events
    
    async def on_error(self, event: IEvent, error: Exception) -> bool:
        """Default error handling - log error and allow retry."""
        self._error_count += 1
        
        logger.error(
            f"Event handling error in {self.handler_id}: {str(error)} "
            f"(event: {event.event_id}, type: {event.event_type})"
        )
        
        # Default: allow retry for most errors, but not for validation errors
        return not isinstance(error, EventValidationError)
    
    def add_supported_event_type(self, event_type: str) -> None:
        """Add an event type to the supported types list."""
        if event_type not in self._supported_events:
            self._supported_events.append(event_type)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get handler performance metrics."""
        avg_processing_time = 0.0
        if self._processing_count > 0:
            avg_processing_time = self._total_processing_time / self._processing_count
        
        return {
            'handler_id': self.handler_id,
            'service_name': self.service_name,
            'processing_count': self._processing_count,
            'error_count': self._error_count,
            'success_rate': self._processing_count / max(1, self._processing_count + self._error_count),
            'average_processing_time_ms': avg_processing_time * 1000,
            'last_processed': self._last_processed.isoformat() if self._last_processed else None
        }
    
    async def handle(self, event: IEvent) -> bool:
        """
        Template method that tracks performance and delegates to _process_event.
        
        Subclasses should override _process_event instead of this method.
        """
        start_time = time.time()
        
        try:
            result = await self._process_event(event)
            
            # Update metrics on success
            processing_time = time.time() - start_time
            self._processing_count += 1
            self._total_processing_time += processing_time
            self._last_processed = datetime.utcnow()
            
            return result
            
        except Exception as e:
            self._error_count += 1
            raise e
    
    async def _process_event(self, event: IEvent) -> bool:
        """
        Process the event. Subclasses must implement this method.
        
        Args:
            event: The event to process
            
        Returns:
            True if processed successfully, False otherwise
        """
        raise NotImplementedError("Subclasses must implement _process_event")