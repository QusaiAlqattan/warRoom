import asyncio
import json
import logging
import ollama
import re
from .personas import PERSONAS

log = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self):
        # Using local Ollama models
        self.model_fast = 'qwen2.5:3b'  # The "Moderator" (Manager)
        self.model_smart = 'qwen2.5:3b' # The "Speaker" (Persona)
        self.client = ollama.AsyncClient()
        log.info("Orchestrator initialized in Moderator Mode", 
                 extra={"moderator_model": self.model_fast, "persona_model": self.model_smart})

    def get_direct_mention(self, message, personas): 
        for p in personas: 
            # Checks if "@Name" is in the text 
            pattern = rf"(?<!\w)@{re.escape(p.name)}\b"
            if re.search(pattern, message, re.IGNORECASE):
                log.info("Direct mention detected", extra={"persona": p.name})
                return p
        return None

    async def decide_speaker(self, user_input, context):
        """
        A single call to decide which persona should speak next.
        """
        # Create a list of persona descriptions for the moderator to review
        persona_list = "\n".join([f"- {p.name}: {p.description}" for p in PERSONAS])
        
        moderator_prompt = f"""
        You are a conversation moderator. We have a group chat with:
        {persona_list}

        CHAT HISTORY:
        {context}

        NEW USER MESSAGE:
        "{user_input}"

        TASK:
        Based on the history and the new message, decide who should speak next. 
        - Pick the person with the most relevant expertise.
        - If the user is asking a general question, pick who would have the most interesting take.
        - Only provide the NAME of the persona.

        RESPONSE FORMAT (JSON ONLY):
        {{
        "reasoning": "1 sentence explanation of why this person should continue or why we are switching",
        "winner": "NAME",
        "confidence": 1-10
        }}
        """

        try:
            response = await self.client.generate(model=self.model_fast, prompt=moderator_prompt)
            response_json = json.loads(response['response'])
            chosen_name = response_json['winner']
            log.info("Moderator made a decision", extra={"reasoning": response_json['reasoning'], "winner": chosen_name, "confidence": response_json['confidence']})
            
            # Match the text response back to our Persona object
            for p in PERSONAS:
                if p.name.lower() in chosen_name.lower():
                    log.info("Moderator selected speaker", extra={"winner": p.name})
                    return p
            
            # Fallback if the moderator hallucinates a name
            log.warning("Moderator gave invalid name, falling back to first persona")
            return PERSONAS[0]
            
        except Exception as exc:
            log.exception("Moderator decision failed", exc_info=exc)
            return PERSONAS[0]

    async def chat(self, user_input, memory):
        context = memory.get_full_context()
        log.info("Starting chat flow", extra={"user_input": user_input})
        
        # 1. PRIORITY: Direct Mention Check (@Name)
        winner = self.get_direct_mention(user_input, PERSONAS)
        
        # 2. MODERATION: If no one was mentioned, let the Moderator decide
        if winner is None:
            winner = await self.decide_speaker(user_input, context)
        
        # 3. GENERATION: The chosen persona speaks
        # We include the persona's identity in the system prompt
        full_prompt = f"Identity: {winner.system_instructions}\n\nHistory:\n{context}\n\nUser: {user_input}\n{winner.name}:"
        
        try:
            response = await self.client.generate(model=self.model_smart, prompt=full_prompt)
            log.info("Persona responded", extra={"speaker": winner.name})
            return winner.name, response['response']
        except Exception as exc:
            log.exception("Error generating final response", exc_info=exc)
            return winner.name, "I'm having trouble thinking of what to say right now."