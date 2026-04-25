import logging

log = logging.getLogger(__name__)

class ChatMemory:
    def __init__(self):
        self.history = []
        log.info("ChatMemory initialized")

    def add_message(self, role, person_name, content):
        self.history.append({"role": role, "name": person_name, "content": content})
        log.info("Message added to memory", extra={"role": role, "person_name": person_name, "content": content})

    def get_full_context(self):
        # Format history for the LLM
        context = "\n".join([f"{m['name']}: {m['content']}" for m in self.history])
        log.info("Full context generated", extra={"length": len(self.history)})
        return context

    def get_recent_context(self, limit=10):
        recent = self.history[-limit:]
        log.info("Recent context retrieved", extra={"limit": limit, "count": len(recent)})
        return recent

    def get_last_speaker(self):
        """Return the name of the last assistant who spoke, or None."""
        for m in reversed(self.history):
            if m["role"] == "assistant":
                return m["name"]
        return None