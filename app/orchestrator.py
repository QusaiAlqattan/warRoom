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

    async def decide_speaker(self, user_input, context, personas):
        """
        A single call to decide which persona should speak next.
        """
        # Create a list of persona descriptions for the moderator to review
        persona_list = "\n".join([f"- {p.name}: {p.description}" for p in personas])
        
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
            for p in personas:
                if p.name.lower() in chosen_name.lower():
                    log.info("Moderator selected speaker", extra={"winner": p.name})
                    return p
            
            # Fallback if the moderator hallucinates a name
            log.warning("Moderator gave invalid name, falling back to first persona")
            return personas[0]
            
        except Exception as exc:
            log.exception("Moderator decision failed", exc_info=exc)
            return personas[0]

    async def decide_next_speaker(self, context, personas, last_speaker_name):
        """
        Decide who speaks next in an autonomous conversation (no new user input).
        Avoids picking the same persona twice in a row.
        """
        persona_list = "\n".join([f"- {p.name}: {p.description}" for p in personas])

        moderator_prompt = f"""
        You are a conversation moderator. We have a group chat with:
        {persona_list}

        CHAT HISTORY:
        {context}

        The last person who spoke was: {last_speaker_name}

        TASK:
        The conversation is flowing naturally between the personas. Decide who should speak next.
        - Do NOT pick {last_speaker_name} again.
        - Pick the person who would most naturally want to respond, disagree, add to, or build on what was just said.

        RESPONSE FORMAT (JSON ONLY):
        {{
        "reasoning": "1 sentence explanation",
        "winner": "NAME",
        "confidence": 1-10
        }}
        """

        try:
            response = await self.client.generate(model=self.model_fast, prompt=moderator_prompt)
            response_json = json.loads(response['response'])
            chosen_name = response_json['winner']
            log.info("Moderator (auto) decision", extra={"reasoning": response_json['reasoning'], "winner": chosen_name})

            for p in personas:
                if p.name.lower() in chosen_name.lower() and p.name != last_speaker_name:
                    return p

            # Fallback: pick anyone who isn't the last speaker
            others = [p for p in personas if p.name != last_speaker_name]
            return others[0] if others else personas[0]

        except Exception as exc:
            log.exception("Moderator (auto) decision failed", exc_info=exc)
            others = [p for p in personas if p.name != last_speaker_name]
            return others[0] if others else personas[0]

    async def continue_chat(self, memory, personas):
        """Generate the next turn in an autonomous persona-to-persona conversation."""
        context = memory.get_full_context()
        last_speaker = memory.get_last_speaker()
        log.info("Continuing autonomous chat", extra={"last_speaker": last_speaker})

        winner = await self.decide_next_speaker(context, personas, last_speaker)

        full_prompt = (
            f"Identity: {winner.system_instructions}\n\n"
            f"History:\n{context}\n\n"
            f"Continue the conversation naturally. Respond to what was just said. "
            f"You may agree, disagree, ask a question, or build on the topic.\n"
            f"{winner.name}:"
        )

        try:
            response = await self.client.generate(model=self.model_smart, prompt=full_prompt)
            log.info("Persona responded (auto)", extra={"speaker": winner.name})
            return winner.name, response['response']
        except Exception as exc:
            log.exception("Error in autonomous response", exc_info=exc)
            return winner.name, "I'm having trouble thinking of what to say right now."

    async def chat(self, user_input, memory, personas):
        context = memory.get_full_context()
        log.info("Starting chat flow", extra={"user_input": user_input})
        
        # 1. PRIORITY: Direct Mention Check (@Name)
        winner = self.get_direct_mention(user_input, personas)
        
        # 2. MODERATION: If no one was mentioned, let the Moderator decide
        if winner is None:
            winner = await self.decide_speaker(user_input, context, personas)
        
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