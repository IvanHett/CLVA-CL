const messages = document.getElementById("messages");
const form = document.getElementById("ask-form");
const input = document.getElementById("query");
const sendButton = document.getElementById("send");
const modeSelect = document.getElementById("mode");
const suggestions = document.getElementById("suggestions");

const STAGE_LABELS = {
  exact: "Exact match",
  keyword: "Keyword match",
  classifier: "Intent classifier",
  retrieval: "Semantic retrieval",
  fallback: "No match",
};

function timeNow() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function addMessage(sender, text, details) {
  const row = document.createElement("div");
  row.className = `message ${sender}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = sender === "user" ? "You" : "CL";

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  const body = document.createElement("div");
  body.className = "text";
  body.textContent = text;

  const meta = document.createElement("div");
  meta.className = "meta";
  const time = document.createElement("span");
  time.textContent = timeNow();
  meta.append(time);

  // Show how the answer was reached, so users can judge how far to trust it.
  if (details) {
    if (!details.matched) row.classList.add("fallback");
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = STAGE_LABELS[details.stage] || details.stage;
    const timing = document.createElement("span");
    timing.textContent = `${details.response_time_ms} ms`;
    meta.append(badge, timing);
  }

  bubble.append(body, meta);
  row.append(avatar, bubble);
  messages.append(row);
  messages.scrollTop = messages.scrollHeight;
  return row;
}

async function ask(query) {
  addMessage("user", query);
  sendButton.disabled = true;
  const typing = addMessage("bot", "CLVA is typing...");
  typing.classList.add("typing");

  try {
    const response = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, mode: modeSelect.value }),
    });
    const data = await response.json();
    typing.remove();
    if (response.ok) {
      addMessage("bot", data.answer, data);
    } else {
      addMessage("bot", data.error || "Something went wrong. Please try again.");
    }
  } catch (error) {
    typing.remove();
    addMessage("bot", "I couldn't reach the server. Please check it is running and try again.");
  } finally {
    sendButton.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const query = input.value.trim();
  if (!query || sendButton.disabled) return;
  input.value = "";
  ask(query);
});

suggestions.addEventListener("click", (event) => {
  if (event.target.tagName === "BUTTON" && !sendButton.disabled) {
    ask(event.target.textContent);
  }
});

addMessage(
  "bot",
  "Hello! I'm CLVA, the Course Leader Virtual Assistant for BSc (Hons) Computer Science at the University of Wolverhampton. Ask me about deadlines, submissions, extensions, modules, timetables or university support."
);
input.focus();
