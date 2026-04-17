from fastapi import FastAPI
from pydantic import BaseModel
from .orchestrator import Orchestrator
from .memory import ChatMemory
import os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

# Initialize global state
memory = ChatMemory()
orchestrator = Orchestrator()

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def handle_chat(request: ChatRequest):
    # 1. Save user message to memory
    memory.add_message("user", "User", request.message)
    
    # 2. Get the winning persona to speak
    name, response_text = await orchestrator.chat(request.message, memory)
    
    # 3. Save AI message to memory
    memory.add_message("assistant", name, response_text)
    
    return {
        "speaker": name,
        "content": response_text
    }