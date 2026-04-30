/* ===== State ===== */
let roomId = null;
let autoRunning = false;
const selected = new Set();

/* ===== DOM refs ===== */
const lobby = document.getElementById("lobby");
const roomEl = document.getElementById("room");
const personaGrid = document.getElementById("persona-grid");
const createBtn = document.getElementById("create-room-btn");
const roomSubtitle = document.getElementById("room-subtitle");
const chat = document.getElementById("chat");
const form = document.getElementById("chat-form");
const input = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const stopBtn = document.getElementById("stop-btn");

/* ===== 1. Lobby: Load & select personas ===== */

async function loadPersonas() {
  const res = await fetch("/personas");
  const personas = await res.json();

  personas.forEach((p) => {
    const card = document.createElement("div");
    card.classList.add("persona-card");
    card.dataset.name = p.name;

    card.innerHTML = `
      <div class="persona-name">${p.name}</div>
      <div class="persona-desc">${p.description}</div>
    `;

    card.addEventListener("click", () => {
      if (selected.has(p.name)) {
        selected.delete(p.name);
        card.classList.remove("selected");
      } else {
        selected.add(p.name);
        card.classList.add("selected");
      }
      createBtn.disabled = selected.size === 0;
    });

    personaGrid.appendChild(card);
  });
}

loadPersonas();

/* ===== 2. Create room ===== */

createBtn.addEventListener("click", async () => {
  createBtn.disabled = true;
  createBtn.textContent = "Creating…";

  try {
    const res = await fetch("/rooms", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ persona_names: [...selected] }),
    });

    if (!res.ok) throw new Error(`Server error ${res.status}`);

    const data = await res.json();
    roomId = data.room_id;

    // Switch to chat screen
    roomSubtitle.textContent = data.personas.join(" · ");
    lobby.style.display = "none";
    roomEl.style.display = "flex";
    input.focus();
  } catch (err) {
    console.error(err);
    createBtn.textContent = "Create Room";
    createBtn.disabled = false;
  }
});

/* ===== 3. Chat ===== */

function addMessage(role, speaker, text) {
  const el = document.createElement("div");
  el.classList.add("message", role);

  if (role === "assistant") {
    const tag = document.createElement("div");
    tag.classList.add("speaker-tag", `speaker-${speaker.replace(/\s+/g, "-")}`);
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
  el.innerHTML = 'Typing<span class="dots"></span>';
  chat.appendChild(el);
  chat.scrollTop = chat.scrollHeight;
}

function hideThinking() {
  const el = document.getElementById("thinking");
  if (el) el.remove();
}

/* ===== 4. Auto-chat loop ===== */

async function startAutoChat() {
  autoRunning = true;
  stopBtn.style.display = "";
  sendBtn.disabled = true;

  while (autoRunning && roomId) {
    showThinking();

    try {
      const res = await fetch(`/rooms/${roomId}/continue`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      if (!autoRunning) break; // user stopped while waiting

      if (!res.ok) throw new Error(`Server error ${res.status}`);

      const data = await res.json();
      hideThinking();
      addMessage("assistant", data.speaker, data.content);
    } catch (err) {
      hideThinking();
      if (autoRunning) {
        addMessage("assistant", "System", "Auto-chat hit an error. Stopping.");
        console.error(err);
      }
      break;
    }

    // Small pause between turns so the user can read
    await new Promise((r) => setTimeout(r, 1500));
  }

  stopAutoChat();
}

function stopAutoChat() {
  autoRunning = false;
  hideThinking();
  stopBtn.style.display = "none";
  sendBtn.disabled = false;
  input.focus();
}

stopBtn.addEventListener("click", stopAutoChat);

/* ===== 3. Chat (user message) ===== */

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text || !roomId) return;

  // If auto-chat is running, stop it first
  if (autoRunning) stopAutoChat();

  addMessage("user", "You", text);
  input.value = "";
  sendBtn.disabled = true;
  showThinking();

  try {
    const res = await fetch(`/rooms/${roomId}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });

    if (!res.ok) throw new Error(`Server error ${res.status}`);

    const data = await res.json();
    hideThinking();
    addMessage("assistant", data.speaker, data.content);

    // Kick off the auto-chat loop after the first response
    let personaCount = 0;
    document.getElementById("room-subtitle").textContent.split("·").forEach(() => personaCount++);
    if ( personaCount > 1 ) {
      console.log('Starting auto-chat loop...');
      startAutoChat();
    } else {
      sendBtn.disabled = false;
    }
  } catch (err) {
    hideThinking();
    addMessage("assistant", "System", "Something went wrong. Check the console.");
    console.error(err);
    sendBtn.disabled = false;
    input.focus();
  }
});
