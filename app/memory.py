class ChatMemory:
    def __init__(self):
        self.history = []

    def add_message(self, role, name, content):
        self.history.append({"role": role, "name": name, "content": content})

    def get_full_context(self):
        # Format history for the LLM
        return "\n".join([f"{m['name']}: {m['content']}" for m in self.history])

    def get_recent_context(self, limit=10):
        return self.history[-limit:]