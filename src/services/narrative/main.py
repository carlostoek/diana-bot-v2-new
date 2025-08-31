from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uuid

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from .models.narrative_models import Base
from .services.narrative_service import UserNarrativeService, NarrativeContentService
from .engines.narrative_engine import NarrativeEngine

# Database setup (this would typically come from config)
DATABASE_URL = "postgresql+asyncpg://user:password@localhost/narrative_db"

engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

app = FastAPI()

# Pydantic models for API requests and responses
class Choice(BaseModel):
    choice_id: str
    text: str

class NarrativeState(BaseModel):
    node_id: str
    character: str
    text: str
    choices: Optional[List[Choice]] = None

class UserDecision(BaseModel):
    node_id: str
    choice_id: str

class StartNarrativeResponse(BaseModel):
    message: str
    initial_state: NarrativeState

@app.post("/narrative/start", response_model=StartNarrativeResponse)
async def start_narrative(x_user_id: str = Header(...), x_tenant_id: str = Header(...)):
    """
    Start a new narrative for a user or return existing state.
    """
    async with async_session() as session:
        try:
            # Initialize services
            user_service = UserNarrativeService(session)
            content_service = NarrativeContentService(session)
            
            # Check if user already has a state
            user_state = await user_service.get_user_state(x_user_id)
            
            if user_state:
                # User already has a state, return current state
                scene_data = await content_service.get_scene_with_choices(str(user_state.current_scene_id))
                if not scene_data:
                    raise HTTPException(status_code=500, detail="Current scene not found")
                
                scene = scene_data["scene"]
                decisions = scene_data["decisions"]
                
                choices = [
                    Choice(choice_id=str(d.id), text=d.choice_text)
                    for d in decisions
                ]
                
                narrative_state = NarrativeState(
                    node_id=str(scene.id),
                    character=scene.character_speaker or "System",
                    text=scene.dialogue,
                    choices=choices
                )
                
                return StartNarrativeResponse(
                    message="Continuing existing narrative",
                    initial_state=narrative_state
                )
            else:
                # Create new narrative state
                # TODO: Determine initial scene ID from configuration or database
                initial_scene_id = "00000000-0000-0000-0000-000000000001"  # Placeholder
                
                try:
                    uuid.UUID(initial_scene_id)
                except ValueError:
                    raise HTTPException(status_code=500, detail="Invalid initial scene ID")
                
                # Create user state
                user_state = await user_service.create_user_state(x_user_id, initial_scene_id)
                
                # Get scene data
                scene_data = await content_service.get_scene_with_choices(initial_scene_id)
                if not scene_data:
                    raise HTTPException(status_code=500, detail="Initial scene not found")
                
                scene = scene_data["scene"]
                decisions = scene_data["decisions"]
                
                choices = [
                    Choice(choice_id=str(d.id), text=d.choice_text)
                    for d in decisions
                ]
                
                narrative_state = NarrativeState(
                    node_id=str(scene.id),
                    character=scene.character_speaker or "System",
                    text=scene.dialogue,
                    choices=choices
                )
                
                return StartNarrativeResponse(
                    message="New narrative started",
                    initial_state=narrative_state
                )
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/narrative/state", response_model=NarrativeState)
async def get_narrative_state(x_user_id: str = Header(...), x_tenant_id: str = Header(...)):
    """
    Fetches the user's current narrative state.
    """
    async with async_session() as session:
        try:
            # Initialize services
            user_service = UserNarrativeService(session)
            content_service = NarrativeContentService(session)
            
            # Get user state
            user_state = await user_service.get_user_state(x_user_id)
            if not user_state:
                raise HTTPException(status_code=404, detail="User narrative state not found")
            
            # Get scene data
            scene_data = await content_service.get_scene_with_choices(str(user_state.current_scene_id))
            if not scene_data:
                raise HTTPException(status_code=500, detail="Current scene not found")
            
            scene = scene_data["scene"]
            decisions = scene_data["decisions"]
            
            choices = [
                Choice(choice_id=str(d.id), text=d.choice_text)
                for d in decisions
            ]
            
            return NarrativeState(
                node_id=str(scene.id),
                character=scene.character_speaker or "System",
                text=scene.dialogue,
                choices=choices
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/narrative/choice", response_model=NarrativeState)
async def make_choice(decision: UserDecision, x_user_id: str = Header(...), x_tenant_id: str = Header(...)):
    """
    Submits a user's choice and returns the new narrative state.
    """
    async with async_session() as session:
        try:
            # Initialize engine
            engine = NarrativeEngine(session)
            
            # Process the decision
            result = await engine.process_decision(x_user_id, decision.choice_id)
            
            if not result:
                raise HTTPException(status_code=400, detail="Invalid decision or user state not found")
            
            return NarrativeState(**result)
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/narrative/validate", response_model=dict)
async def validate_narrative_structure():
    """
    Validate the narrative structure for consistency.
    """
    async with async_session() as session:
        try:
            # Initialize service
            content_service = NarrativeContentService(session)
            
            # Validate structure
            validation_report = await content_service.validate_narrative_structure()
            
            return validation_report
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
