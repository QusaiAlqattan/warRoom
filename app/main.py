import logging
import uuid
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .orchestrator import Orchestrator
from .memory import ChatMemory
from .personas import PERSONAS, Persona, get_personas_from_db, insert_persona_to_db, delete_persona_from_db
import os
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
from pathlib import Path

load_dotenv()

class ExtraFormatter(logging.Formatter):
    STANDARD_ATTRS = {
        'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
        'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName',
        'created', 'msecs', 'relativeCreated', 'thread', 'threadName',
        'processName', 'process', 'message'
    }

    def format(self, record):
        extra_items = {
            key: value
            for key, value in record.__dict__.items()
            if key not in self.STANDARD_ATTRS and not key.startswith('_')
        }
        record.extra_fields = ''
        if extra_items:
            try:
                record.extra_fields = ' | ' + __import__('json').dumps(extra_items, ensure_ascii=False)
            except Exception:
                record.extra_fields = ' | extra=' + str(extra_items)
        return super().format(record)

handler = logging.StreamHandler()
handler.setFormatter(ExtraFormatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s%(extra_fields)s'))
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers = [handler]
log = logging.getLogger("warRoom")

app = FastAPI()

# rooms: dict of room_id -> { "personas": [Persona, ...], "memory": ChatMemory, "orchestrator": Orchestrator }
rooms: dict = {}

class CreateRoomRequest(BaseModel):
    persona_names: List[str]

class ChatRequest(BaseModel):
    message: str

@app.on_event("startup")
async def startup_event():
    log.info("Starting warRoom FastAPI application")

@app.get("/personas")
async def list_personas():
    """Return all available personas for the selection screen."""
    return [{"name": p.name, "description": p.description.strip()} for p in PERSONAS]

@app.post("/rooms")
async def create_room(request: CreateRoomRequest):
    """Create a new room with the selected personas."""
    if not request.persona_names:
        raise HTTPException(status_code=400, detail="Select at least one persona")

    selected = [p for p in PERSONAS if p.name in request.persona_names]
    if not selected:
        raise HTTPException(status_code=400, detail="No valid personas selected")

    room_id = uuid.uuid4().hex[:8]
    rooms[room_id] = {
        "personas": selected,
        "memory": ChatMemory(),
        "orchestrator": Orchestrator(),
    }
    log.info("Room created", extra={"room_id": room_id, "personas": [p.name for p in selected]})
    return {"room_id": room_id, "personas": [p.name for p in selected]}

@app.post("/rooms/{room_id}/chat")
async def handle_chat(room_id: str, request: ChatRequest):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")

    room = rooms[room_id]
    memory = room["memory"]
    orchestrator = room["orchestrator"]
    persona_list = room["personas"]

    log.info("Received chat request", extra={"room_id": room_id, "user_message": request.message})
    memory.add_message("user", "User", request.message)

    name, response_text = await orchestrator.chat(request.message, memory, persona_list)
    log.info("Chat response ready", extra={"room_id": room_id, "speaker": name})

    memory.add_message("assistant", name, response_text)

    return {"speaker": name, "content": response_text}

@app.post("/rooms/{room_id}/continue")
async def handle_continue(room_id: str):
    """Let the personas continue talking to each other without user input."""
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")

    room = rooms[room_id]
    memory = room["memory"]
    orchestrator = room["orchestrator"]
    persona_list = room["personas"]

    if len(persona_list) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 personas for auto-chat")

    name, response_text = await orchestrator.continue_chat(memory, persona_list)
    log.info("Auto-chat response", extra={"room_id": room_id, "speaker": name})

    memory.add_message("assistant", name, response_text)

    return {"speaker": name, "content": response_text}

class CreatePersonaRequest(BaseModel):
    name: str
    short_description: str
    traits: str
    cognitive_style: str
    social_behavior: str
    representative_quote: str
    interests: str

@app.post("/personas")
async def create_persona(request: CreatePersonaRequest):
    """Create a new custom persona and store it in the DB."""
    name = request.name.strip()
    short_desc = request.short_description.strip()
    traits = request.traits.strip()
    cognitive = request.cognitive_style.strip()
    social = request.social_behavior.strip()
    quote = request.representative_quote.strip()
    interests = request.interests.strip()

    if not all([name, short_desc, traits, cognitive, social, quote, interests]):
        raise HTTPException(status_code=400, detail="All fields are required")

    # Check for duplicate name
    for p in PERSONAS:
        if p.name.lower() == name.lower():
            raise HTTPException(status_code=409, detail=f"Persona '{name}' already exists")

    # Build description (only description, prefix/suffix will be added at runtime)
    description = f"{short_desc}Traits: {traits}Cognitive Style: {cognitive}Social Behavior: {social}Interests: {interests}The \"Representative Quote\": \"{quote}\""

    try:
        insert_persona_to_db(name, description)
    except Exception as e:
        log.exception("Failed to insert persona into DB")
        raise HTTPException(status_code=500, detail="Database error")

    # Reload in-memory list
    PERSONAS.clear()
    PERSONAS.extend(get_personas_from_db())
    log.info("Persona created", extra={"persona_name": name})

    return {"name": name, "description": description}

@app.delete("/personas/{persona_name}")
async def remove_persona(persona_name: str):
    """Delete a custom persona from the DB."""
    found = any(p.name.lower() == persona_name.lower() for p in PERSONAS)
    if not found:
        raise HTTPException(status_code=404, detail="Persona not found")

    try:
        delete_persona_from_db(persona_name)
    except Exception as e:
        log.exception("Failed to delete persona from DB")
        raise HTTPException(status_code=500, detail="Database error")

    PERSONAS.clear()
    PERSONAS.extend(get_personas_from_db())
    log.info("Persona deleted", extra={"persona_name": persona_name})

    return {"deleted": persona_name}

BASE_DIR = Path(__file__).resolve().parent.parent
app.mount("/", StaticFiles(directory=BASE_DIR / "frontend", html=True), name="frontend")


"""
prefix: This is a conversation between multiple personas. You are playing the role of

short description: 

Cognitive Style:

Traits:

Social Behavior:

Representative Quote:

sufix: Always respond in the style of your character and never reveal that you are an AI. Always make your answers short (one to three sentences). Always answer in English.
"""