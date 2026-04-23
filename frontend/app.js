const chat = document.getElementById("chat");
const form = document.getElementById("chat-form");
const input = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");

function addMessage(role, speaker, text) {
  const el = document.createElement("div");
  el.classList.add("message", role);

  if (role === "assistant") {
    const tag = document.createElement("div");
    tag.classList.add("speaker-tag", `speaker-${speaker}`);
    tag.textContent = speaker;
    el.appendChild(tag);
  }

  const body = document.createElement("div");
  body.classList.add("message-text");
  body.textContent = text;
  el.appendChild(body);

  chat.appendChild(el);
  chat.scrollTop = chat.scrollHeight;
}

function showThinking() {
  const el = document.createElement("div");
  el.classList.add("thinking");
  el.id = "thinking";
  el.innerHTML = 'Thinking<span class="dots"></span>';
  chat.appendChild(el);
  chat.scrollTop = chat.scrollHeight;
}

function hideThinking() {
  const el = document.getElementById("thinking");
  if (el) el.remove();
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;

  addMessage("user", "You", text);
  input.value = "";
  sendBtn.disabled = true;
  showThinking();

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });

    if (!res.ok) throw new Error(`Server error ${res.status}`);

    const data = await res.json();
    hideThinking();
    addMessage("assistant", data.speaker, data.content);
  } catch (err) {
    hideThinking();
    addMessage("assistant", "System", "Something went wrong. Check the console.");
    console.error(err);
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
});
