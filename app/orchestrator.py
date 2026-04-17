import asyncio
import ollama
import re
from .personas import PERSONAS

class Orchestrator:
    def __init__(self):
        # You can specify the local models you want to use here
        self.model_fast = 'qwen2.5:3b'  # Lightweight model for scoring
        self.model_smart = 'qwen2.5:3b' # More capable model for final responses
        self.client = ollama.AsyncClient()

    def get_direct_mention(self, message, personas): 
        for p in personas: 
            # Checks if "@Scientist" is in the text 
            if re.search(rf"\b@{p.name}\b", message, re.IGNORECASE): 
              return p
            return None
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
            # Remove the incorrect line: response = await self.model_fast.generate_content_async(prompt)
            # Instead, use the client directly:
            response = await self.client.generate(model=self.model_fast, prompt=prompt)
            score = int(re.search(r'\d+', response['response']).group())
            return score
        except:
            return 1  # Default to low interest on error

    async def chat(self, user_input, memory):
        context = memory.get_full_context()
        
        # 1. Direct Mention Check
        winner = self.get_direct_mention(user_input, PERSONAS)
        if winner is None:  # Note: Use 'is None' instead of '== None' for better practice
            # 2. Competitive Scoring (Parallel)
            tasks = [self.get_score(p, user_input, context) for p in PERSONAS]
            scores = await asyncio.gather(*tasks)
            
            # Find the index of the highest score
            winner_index = scores.index(max(scores))
            winner = PERSONAS[winner_index]

        # 3. Final Generation
        full_prompt = f"System: {winner.system_instructions}\nHistory: {context}\nUser: {user_input}"
        # Remove the incorrect line: response = await self.model_smart.generate_content_async(full_prompt)
        # Instead, use the client directly:
        response = await self.client.generate(model=self.model_smart, prompt=full_prompt)
        
        return winner.name, response['response']