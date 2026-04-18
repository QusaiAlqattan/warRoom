import asyncio
import logging
import ollama
import re
from .personas import PERSONAS

log = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self):
        # You can specify the local models you want to use here
        self.model_fast = 'qwen2.5:3b'  # Lightweight model for scoring
        self.model_smart = 'qwen2.5:3b' # More capable model for final responses
        self.client = ollama.AsyncClient()
        log.info("Orchestrator initialized", extra={"model_fast": self.model_fast, "model_smart": self.model_smart})

    def get_direct_mention(self, message, personas): 
        log.info("Checking direct mentions", extra={"search_text": message})
        for p in personas: 
            # Checks if "@Scientist" is in the text 
            pattern = rf"(?<!\w)@{re.escape(p.name)}\b"
            if re.search(pattern, message, re.IGNORECASE):
                log.info("Direct mention matched persona", extra={"persona": p.name})
                return p
        log.info("No direct mention matched")
        return None

    async def get_score(self, persona, user_input, context):
        """Asks a persona to rate their interest in the topic."""
        prompt = f"""
        Context: {context}
        New Message: {user_input}
        
        As the persona '{persona.name}', how relevant is your expertise to this message?
        Rate from 1 to 10. Respond with ONLY the number.
        """
        try:
            response = await self.client.generate(model=self.model_fast, prompt=prompt)
            score = int(re.search(r'\d+', response['response']).group())
            log.info("Persona score calculated", extra={"persona": persona.name, "score": score})
            return score
        except Exception as exc:
            log.exception("Error calculating persona score", exc_info=exc, extra={"persona": persona.name})
            return 1  # Default to low interest on error

    async def chat(self, user_input, memory):
        context = memory.get_full_context()
        log.info("Starting chat flow", extra={"user_input": user_input, "context_length": len(context)})
        
        # 1. Direct Mention Check
        winner = self.get_direct_mention(user_input, PERSONAS)
        if winner is None:
            # 2. Competitive Scoring (Parallel)
            tasks = [self.get_score(p, user_input, context) for p in PERSONAS]
            scores = await asyncio.gather(*tasks)
            log.info("All persona scores returned", extra={"scores": scores})
            
            # Find the index of the highest score
            winner_index = scores.index(max(scores))
            winner = PERSONAS[winner_index]
            log.info("Winner selected by scoring", extra={"winner": winner.name, "score": scores[winner_index]})
        else:
            log.info("Winner selected by direct mention", extra={"winner": winner.name})

        # 3. Final Generation
        full_prompt = f"System: {winner.system_instructions}\nHistory: {context}\nUser: {user_input}"
        log.info("Sending prompt to model", extra={"winner": winner.name})
        try:
            response = await self.client.generate(model=self.model_smart, prompt=full_prompt)
            log.info("Model returned response", extra={"response_length": len(response.get('response', ''))})
            return winner.name, response['response']
        except Exception as exc:
            log.exception("Error generating final response", exc_info=exc, extra={"winner": winner.name})
            return winner.name, "Sorry, I could not generate a response right now."
