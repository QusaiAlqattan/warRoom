const form = document.getElementById("persona-form");
const nameInput = document.getElementById("p-name");
const shortDescInput = document.getElementById("p-short-desc");
const traitsInput = document.getElementById("p-traits");
const cognitiveInput = document.getElementById("p-cognitive");
const socialInput = document.getElementById("p-social");
const quoteInput = document.getElementById("p-quote");
const interestsInput = document.getElementById("p-interests");
const saveBtn = document.getElementById("save-btn");
const status = document.getElementById("form-status");
const listEl = document.getElementById("existing-personas");

/* ===== Load existing personas ===== */

async function loadExisting() {
  listEl.innerHTML = "";
  try {
    const res = await fetch("/personas");
    const personas = await res.json();

    if (personas.length === 0) {
      listEl.innerHTML = '<p class="empty-msg">No personas yet.</p>';
      return;
    }

    personas.forEach((p) => {
      const card = document.createElement("div");
      card.classList.add("persona-card", "existing-card");

      card.innerHTML = `
        <div class="card-header">
          <span class="persona-name">${p.name}</span>
          <button class="delete-btn" data-name="${p.name}" title="Delete">✕</button>
        </div>
        <div class="persona-desc">${p.description}</div>
      `;

      card.querySelector(".delete-btn").addEventListener("click", async (e) => {
        e.stopPropagation();
        if (!confirm(`Delete persona "${p.name}"?`)) return;
        await deletePersona(p.name);
      });

      listEl.appendChild(card);
    });
  } catch (err) {
    listEl.innerHTML = '<p class="empty-msg">Failed to load personas.</p>';
    console.error(err);
  }
}

loadExisting();

/* ===== Create persona ===== */

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  status.textContent = "";
  saveBtn.disabled = true;
  saveBtn.textContent = "Saving…";

  const payload = {
    name: nameInput.value.trim(),
    short_description: shortDescInput.value.trim(),
    traits: traitsInput.value.trim(),
    cognitive_style: cognitiveInput.value.trim(),
    social_behavior: socialInput.value.trim(),
    representative_quote: quoteInput.value.trim(),
    interests: interestsInput.value.trim(),
  };

  try {
    const res = await fetch("/personas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || `Error ${res.status}`);
    }

    status.textContent = `✓ "${name}" created!`;
    status.className = "form-status success";
    form.reset();
    loadExisting();
  } catch (err) {
    status.textContent = `✗ ${err.message}`;
    status.className = "form-status error";
    console.error(err);
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = "Save Persona";
  }
});

/* ===== Delete persona ===== */

async function deletePersona(name) {
  try {
    const res = await fetch(`/personas/${encodeURIComponent(name)}`, {
      method: "DELETE",
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || `Error ${res.status}`);
    }

    loadExisting();
  } catch (err) {
    alert(`Failed to delete: ${err.message}`);
    console.error(err);
  }
}
