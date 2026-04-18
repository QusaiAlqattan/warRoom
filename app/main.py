import logging
from fastapi import FastAPI
from pydantic import BaseModel
from .orchestrator import Orchestrator
from .memory import ChatMemory
import os
from dotenv import load_dotenv

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

# Initialize global state
memory = ChatMemory()
orchestrator = Orchestrator()

class ChatRequest(BaseModel):
    message: str

@app.on_event("startup")
async def startup_event():
    log.info("Starting warRoom FastAPI application")

@app.post("/chat")
async def handle_chat(request: ChatRequest):
    log.info("Received chat request", extra={"user_message": request.message})
    # 1. Save user message to memory
    memory.add_message("user", "User", request.message)
    
    # 2. Get the winning persona to speak
    name, response_text = await orchestrator.chat(request.message, memory)
    log.info("Chat response ready", extra={"speaker": name})
    
    # 3. Save AI message to memory
    memory.add_message("assistant", name, response_text)
    
    return {
        "speaker": name,
        "content": response_text
    }