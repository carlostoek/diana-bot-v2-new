"""
Services package for Diana Bot V2.

This package contains all service implementations including the gamification
service, narrative service, and other core business logic services.
"""

from .gamification.interfaces import IGamificationService
from .gamification.service import GamificationService

__all__ = [
    "IGamificationService",
    "GamificationService",
]
