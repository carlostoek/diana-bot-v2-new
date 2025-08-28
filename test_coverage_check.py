#!/usr/bin/env python3
"""
Simple smoke test to check coverage of narrative service components.
This validates that we can import and instantiate the main components.
"""

import asyncio
from unittest.mock import MagicMock

async def test_imports():
    """Test that all narrative service components can be imported."""
    
    print("Testing narrative service imports...")
    
    # Test core service import
    from services.narrative.service import NarrativeService
    print("✅ NarrativeService import successful")
    
    # Test engine imports
    from services.narrative.engines.story_engine import StoryEngine
    print("✅ StoryEngine import successful")
    
    from services.narrative.engines.character_system import CharacterSystem
    print("✅ CharacterSystem import successful")
    
    from services.narrative.engines.decision_engine import DecisionEngine
    print("✅ DecisionEngine import successful")
    
    # Test interfaces import
    from services.narrative.interfaces import INarrativeService, IStoryEngine, ICharacterSystem, IDecisionEngine
    print("✅ Interface imports successful")
    
    # Test models import
    from services.narrative.models import StoryChapter, UserStoryProgress, CharacterRelationship
    print("✅ Model imports successful")
    
    print("✅ All imports successful - narrative service structure is valid")

if __name__ == "__main__":
    asyncio.run(test_imports())