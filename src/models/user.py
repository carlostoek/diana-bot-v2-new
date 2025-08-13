"""
User Database Models for Diana Bot V2.

This module defines all database models related to the user management system
including users, authentication, sessions, and profile data.
"""

from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Any, Dict, Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class UserRole(PyEnum):
    """User role levels for authorization."""

    FREE = "free"
    VIP = "vip"
    ADMIN = "admin"
    MODERATOR = "moderator"
    SUPER_ADMIN = "super_admin"


class UserStatus(PyEnum):
    """User account status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    BANNED = "banned"
    PENDING_VERIFICATION = "pending_verification"


class OnboardingStatus(PyEnum):
    """User onboarding progress status."""

    NOT_STARTED = "not_started"
    PERSONALITY_DETECTION = "personality_detection"
    TUTORIAL_STARTED = "tutorial_started"
    TUTORIAL_COMPLETED = "tutorial_completed"
    COMPLETED = "completed"


class PersonalityTrait(PyEnum):
    """Personality traits detected during onboarding."""

    EXPLORER = "explorer"  # Prefers discovery and exploration
    COMPETITOR = "competitor"  # Motivated by rankings and challenges
    STORYTELLER = "storyteller"  # Enjoys narrative and immersion
    SOCIAL = "social"  # Prefers shared experiences
    COLLECTOR = "collector"  # Motivated by achievements and rewards


class PrivacyLevel(PyEnum):
    """Privacy levels for user data."""

    PUBLIC = "public"
    FRIENDS_ONLY = "friends_only"
    PRIVATE = "private"


class User(Base):
    """
    Core user data and profile information.

    This table stores the main user account data, Telegram integration,
    and core profile information for the Diana Bot system.
    """

    __tablename__ = "users"

    # Primary identification
    user_id = Column(BigInteger, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)

    # Basic profile information
    username = Column(String(100), nullable=True, index=True)
    first_name = Column(String(200), nullable=False)
    last_name = Column(String(200), nullable=True)
    display_name = Column(String(300), nullable=True)

    # Contact and language preferences
    language_code = Column(String(10), default="en", nullable=False)
    timezone = Column(String(50), default="UTC", nullable=False)

    # Account status and permissions
    status = Column(
        Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False, index=True
    )
    role = Column(Enum(UserRole), default=UserRole.FREE, nullable=False, index=True)

    # Privacy settings
    privacy_level = Column(
        Enum(PrivacyLevel), default=PrivacyLevel.PUBLIC, nullable=False
    )
    allow_contact_by_username = Column(Boolean, default=True, nullable=False)
    allow_leaderboard_display = Column(Boolean, default=True, nullable=False)
    allow_analytics_tracking = Column(Boolean, default=True, nullable=False)

    # Telegram-specific data
    telegram_username = Column(String(100), nullable=True, index=True)
    telegram_photo_url = Column(String(500), nullable=True)
    telegram_is_bot = Column(Boolean, default=False, nullable=False)
    telegram_is_premium = Column(Boolean, default=False, nullable=False)
    telegram_language_code = Column(String(10), nullable=True)

    # Profile customization
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    custom_title = Column(String(100), nullable=True)
    favorite_emoji = Column(String(10), nullable=True)

    # User preferences (JSON for flexibility)
    notification_preferences = Column(JSON, nullable=True)
    ui_preferences = Column(JSON, nullable=True)
    content_preferences = Column(JSON, nullable=True)

    # Activity tracking
    last_activity_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    total_sessions = Column(Integer, default=0, nullable=False)
    total_message_count = Column(Integer, default=0, nullable=False)

    # Feature flags and A/B testing
    feature_flags = Column(JSON, nullable=True)
    ab_test_groups = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    onboarding_progress = relationship(
        "UserOnboarding", back_populates="user", uselist=False
    )
    personality_profile = relationship(
        "UserPersonality", back_populates="user", uselist=False
    )
    auth_sessions = relationship("UserAuthSession", back_populates="user")
    subscriptions = relationship("UserSubscription", back_populates="user")

    def __repr__(self):
        return f"<User(user_id={self.user_id}, telegram_id={self.telegram_id}, name={self.first_name})>"


class UserOnboarding(Base):
    """
    Tracks user onboarding progress and completion.

    This table stores detailed information about the user's onboarding
    journey, including completion status and collected data.
    """

    __tablename__ = "user_onboarding"

    user_id = Column(BigInteger, ForeignKey("users.user_id"), primary_key=True)

    # Onboarding status and progress
    status = Column(
        Enum(OnboardingStatus),
        default=OnboardingStatus.NOT_STARTED,
        nullable=False,
        index=True,
    )
    current_step = Column(String(100), nullable=True)
    completed_steps = Column(JSON, nullable=True)  # List of completed step IDs

    # Personality detection results
    personality_questions_answered = Column(Integer, default=0, nullable=False)
    personality_raw_responses = Column(JSON, nullable=True)
    personality_calculated_traits = Column(JSON, nullable=True)

    # Tutorial progress
    tutorial_progress = Column(JSON, nullable=True)
    tutorial_completed_sections = Column(JSON, nullable=True)
    tutorial_skipped = Column(Boolean, default=False, nullable=False)

    # Timing and analytics
    onboarding_started_at = Column(DateTime(timezone=True), nullable=True)
    onboarding_completed_at = Column(DateTime(timezone=True), nullable=True)
    total_onboarding_time_seconds = Column(Integer, nullable=True)
    personality_detection_time_seconds = Column(Integer, nullable=True)
    tutorial_time_seconds = Column(Integer, nullable=True)

    # Drop-off tracking
    last_interaction_step = Column(String(100), nullable=True)
    abandonment_reason = Column(String(200), nullable=True)
    return_count = Column(Integer, default=0, nullable=False)

    # Additional onboarding data
    onboarding_metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="onboarding_progress")

    def __repr__(self):
        return f"<UserOnboarding(user_id={self.user_id}, status={self.status.value}, step={self.current_step})>"


class UserPersonality(Base):
    """
    Stores user personality profile and preferences.

    This table contains the results of personality detection and
    ongoing refinements to user preferences and behavior patterns.
    """

    __tablename__ = "user_personality"

    user_id = Column(BigInteger, ForeignKey("users.user_id"), primary_key=True)

    # Primary personality traits (highest scoring)
    primary_trait = Column(Enum(PersonalityTrait), nullable=True, index=True)
    secondary_trait = Column(Enum(PersonalityTrait), nullable=True)

    # Trait scores (0-100 scale)
    explorer_score = Column(Integer, default=0, nullable=False)
    competitor_score = Column(Integer, default=0, nullable=False)
    storyteller_score = Column(Integer, default=0, nullable=False)
    social_score = Column(Integer, default=0, nullable=False)
    collector_score = Column(Integer, default=0, nullable=False)

    # Content preferences derived from personality
    preferred_content_types = Column(
        JSON, nullable=True
    )  # ["narrative", "competitive", "social"]
    preferred_interaction_style = Column(
        String(50), nullable=True
    )  # "guided", "exploratory", "competitive"
    preferred_reward_types = Column(
        JSON, nullable=True
    )  # ["points", "achievements", "social_recognition"]

    # Behavioral insights
    engagement_patterns = Column(JSON, nullable=True)
    optimal_session_length_minutes = Column(Integer, nullable=True)
    peak_activity_hours = Column(JSON, nullable=True)

    # Adaptability and learning
    confidence_score = Column(
        Integer, default=50, nullable=False
    )  # How confident we are in this profile
    adaptation_count = Column(
        Integer, default=0, nullable=False
    )  # How many times profile was updated
    last_behavior_update = Column(DateTime(timezone=True), nullable=True)

    # Advanced personalization data
    personality_metadata = Column(JSON, nullable=True)
    learning_model_version = Column(String(20), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="personality_profile")

    def __repr__(self):
        return f"<UserPersonality(user_id={self.user_id}, primary={self.primary_trait}, confidence={self.confidence_score})>"


class UserAuthSession(Base):
    """
    Tracks user authentication sessions and security.

    This table manages JWT tokens, session data, and security
    information for API access and bot interactions.
    """

    __tablename__ = "user_auth_sessions"

    id = Column(String(100), primary_key=True)  # UUID for session ID
    user_id = Column(
        BigInteger, ForeignKey("users.user_id"), nullable=False, index=True
    )

    # Session identification
    session_token = Column(String(500), nullable=False, unique=True, index=True)
    refresh_token = Column(String(500), nullable=True, unique=True)

    # Session metadata
    session_type = Column(
        String(50), default="telegram_bot", nullable=False
    )  # "telegram_bot", "web_api", "mobile_api"
    device_info = Column(JSON, nullable=True)
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 support

    # Security and validation
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    refresh_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Activity tracking
    last_activity_at = Column(DateTime(timezone=True), nullable=True)
    login_count = Column(Integer, default=1, nullable=False)

    # Security flags
    is_suspicious = Column(Boolean, default=False, nullable=False)
    security_flags = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="auth_sessions")

    # Indexes for performance
    __table_args__ = (
        Index("ix_auth_sessions_user_active", "user_id", "is_active"),
        Index("ix_auth_sessions_expires", "expires_at"),
    )

    def __repr__(self):
        return f"<UserAuthSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"


class UserSubscription(Base):
    """
    Tracks user VIP subscriptions and payment history.

    This table manages subscription status, billing, and
    VIP feature access for users.
    """

    __tablename__ = "user_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        BigInteger, ForeignKey("users.user_id"), nullable=False, index=True
    )

    # Subscription details
    subscription_type = Column(
        String(50), nullable=False
    )  # "vip_monthly", "vip_yearly", "premium"
    status = Column(
        String(20), default="active", nullable=False, index=True
    )  # "active", "cancelled", "expired", "suspended"

    # Billing information
    price_paid = Column(Integer, nullable=False)  # In cents
    currency = Column(String(3), default="USD", nullable=False)
    payment_provider = Column(
        String(50), nullable=True
    )  # "stripe", "telegram_stars", etc.
    payment_provider_id = Column(String(200), nullable=True)

    # Subscription period
    starts_at = Column(DateTime(timezone=True), nullable=False)
    ends_at = Column(DateTime(timezone=True), nullable=False, index=True)
    auto_renew = Column(Boolean, default=True, nullable=False)

    # Cancellation tracking
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(String(200), nullable=True)

    # Usage tracking
    features_used = Column(JSON, nullable=True)
    usage_statistics = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="subscriptions")

    # Constraints
    __table_args__ = (
        Index("ix_subscriptions_user_status", "user_id", "status"),
        Index("ix_subscriptions_ends_at", "ends_at"),
    )

    def __repr__(self):
        return f"<UserSubscription(id={self.id}, user_id={self.user_id}, type={self.subscription_type}, status={self.status})>"


# Data classes for API and service layer
class UserCreateData:
    """Data structure for creating new users."""

    def __init__(
        self,
        telegram_id: int,
        first_name: str,
        last_name: Optional[str] = None,
        username: Optional[str] = None,
        telegram_username: Optional[str] = None,
        language_code: str = "en",
        telegram_is_premium: bool = False,
        telegram_photo_url: Optional[str] = None,
    ):
        self.telegram_id = telegram_id
        self.first_name = first_name
        self.last_name = last_name
        self.username = username
        self.telegram_username = telegram_username
        self.language_code = language_code
        self.telegram_is_premium = telegram_is_premium
        self.telegram_photo_url = telegram_photo_url


class UserUpdateData:
    """Data structure for updating user profiles."""

    def __init__(self, **kwargs):
        self.updates = kwargs

    def to_dict(self) -> Dict[str, Any]:
        return self.updates


class AuthResult:
    """Result of authentication operations."""

    def __init__(
        self,
        success: bool,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
    ):
        self.success = success
        self.user_id = user_id
        self.session_id = session_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = expires_at
        self.error_message = error_message
