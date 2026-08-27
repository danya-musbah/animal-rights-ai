/* =============================================================================
   chat.js — Animal Rights AI
   Conversation list management, message sending/rendering, loading stages,
   suggested questions, copy/regenerate/feedback actions, error handling.
   ============================================================================= */

const Chat = (() => {
  let currentConversationId = null;
  let conversations = [];
  let lastUserMessage = "";
  let sending = false;

  const SUGGESTED_QUESTIONS = [
    { icon: "⚖️", text: "What is the difference between animal rights and animal welfare?" },
    { icon: "🐄", text: "What legal protections exist for farm animals in the EU?" },
    { icon: "🚚", text: "What are common international standards for animal transport?" },
    { icon: "🧠", text: "What does the scientific literature say about animal sentience?" },
    { icon: "🌍", text: "Compare UK and US animal welfare legislation." },
    { icon: "🧪", text: "What are the main arguments surrounding animal testing?" },
  ];

  const LOADING_STAGES = [
    "Analyzing question…",
    "Searching knowledge base…",
    "Ranking evidence…",
    "Generating grounded answer…",
  ];

  function init() {
    renderSuggestedQuestions();
    bindComposer();
    bindSidebar();
    loadConversations();
    checkStatus();
  }

  function renderSuggestedQuestions() {
    const el = document.getElementById("suggested-questions");
    el.innerHTML = SUGGESTED_QUESTIONS.map(
      (q) => `<button class="suggested-q" type="button"><span class="q-icon">${q.icon}</span>${Utils.escapeHtml(q.text)}</button>`
    ).join("");
    el.querySelectorAll(".suggested-q").forEach((btn, i) => {
      btn.addEventListener("click", () => {
        document.getElementById("composer-input").value = SUGGESTED_QUESTIONS[i].text;
        handleSend();
      });
    });
  }

  function bindComposer() {
    const form = document.getElementById("composer-form");
    const textarea = document.getElementById("composer-input");

    textarea.addEventListener("input", () => {
      textarea.style.height = "auto";
      textarea.style.height = Math.min(textarea.scrollHeight, 160) + "px";
    });
    textarea.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    });
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      handleSend();
    });

    document.getElementById("new-chat-btn").addEventListener("click", startNewConversation);
  }

  function bindSidebar() {
    document.getElementById("sidebar-toggle-btn").addEventListener("click", () => {
      document.getElementById("sidebar").classList.toggle("open");
      document.getElementById("sidebar-scrim").classList.toggle("open");
    });
    document.getElementById("sidebar-scrim").addEventListener("click", () => {
      document.getElementById("sidebar").classList.remove("open");
      document.getElementById("sidebar-scrim").classList.remove("open");
    });
    document.getElementById("evidence-drawer-close").addEventListener("click", () => {
      document.getElementById("evidence-panel").classList.remove("open");
    });
    document.getElementById("evidence-mobile-open").addEventListener("click", () => {
      document.getElementById("evidence-panel").classList.add("open");
    });

    const messagesContainer = document.getElementById("messages-container");
    Evidence.attachClickHandlers(messagesContainer);
  }

  async function checkStatus() {
    const dot = document.getElementById("status-dot");
    const text = document.getElementById("status-text");
    try {
      const health = await Api.getHealth();
      if (health.demo_mode) {
        dot.className = "status-dot demo";
        text.textContent = "Demo mode (configure Supabase + LLM)";
      } else {
        dot.className = "status-dot";
        text.textContent = "Connected";
      }
    } catch {
      dot.className = "status-dot offline";
      text.textContent = "Backend unreachable";
    }
  }

  async function loadConversations() {
    try {
      conversations = await Api.getConversations();
      renderConversationList();
    } catch {
      conversations = [];
      renderConversationList();
    }
  }

  function renderConversationList() {
    const el = document.getElementById("conversation-list");
    if (!conversations.length) {
      el.innerHTML = `<div style="padding:16px 8px;color:var(--text-muted);font-size:12.5px;">No conversations yet. Backend not connected, or you haven't started one.</div>`;
      return;
    }
    el.innerHTML = conversations
      .map(
        (c) => `
      <div class="conversation-item ${c.id === currentConversationId ? "active" : ""}" data-id="${c.id}">
        <span class="title-text">${Utils.escapeHtml(c.title || "New conversation")}</span>
        <span class="conv-actions">
          <button class="rename-btn" title="Rename" aria-label="Rename conversation">✎</button>
          <button class="delete-btn" title="Delete" aria-label="Delete conversation">🗑</button>
        </span>
      </div>`
      )
      .join("");

    el.querySelectorAll(".conversation-item").forEach((item) => {
      const id = item.getAttribute("data-id");
      item.addEventListener("click", (e) => {
        if (e.target.closest(".conv-actions")) return;
        openConversation(id);
      });
      item.querySelector(".rename-btn").addEventListener("click", async (e) => {
        e.stopPropagation();
        const conv = conversations.find((c) => c.id === id);
        const newTitle = prompt("Rename conversation", conv?.title || "");
        if (newTitle && newTitle.trim()) {
          try {
            await Api.renameConversation(id, newTitle.trim());
            loadConversations();
          } catch (err) {
            Utils.toast(err.message);
          }
        }
      });
      item.querySelector(".delete-btn").addEventListener("click", async (e) => {
        e.stopPropagation();
        if (!confirm("Delete this conversation? This cannot be undone.")) return;
        try {
          await Api.deleteConversation(id);
          if (id === currentConversationId) startNewConversation();
          loadConversations();
        } catch (err) {
          Utils.toast(err.message);
        }
      });
    });
  }

  function startNewConversation() {
    currentConversationId = null;
    document.getElementById("messages-container").innerHTML = "";
    document.getElementById("chat-welcome").style.display = "block";
    Evidence.render([], false);
    renderConversationList();
    document.getElementById("sidebar").classList.remove("open");
    document.getElementById("sidebar-scrim").classList.remove("open");
  }

  async function openConversation(id) {
    currentConversationId = id;
    renderConversationList();
    document.getElementById("sidebar").classList.remove("open");
    document.getElementById("sidebar-scrim").classList.remove("open");
    try {
      const conv = await Api.getConversation(id);
      document.getElementById("chat-welcome").style.display = "none";
      const container = document.getElementById("messages-container");
      container.innerHTML = "";
      (conv.messages || []).forEach((m) => {
        appendMessageBubble(m.role, m.content, { answerType: m.answer_type, confidence: m.confidence, messageId: m.id });
      });
      scrollToBottom();
    } catch (err) {
      Utils.toast("Could not load conversation: " + err.message);
    }
  }

  function scrollToBottom() {
    const el = document.getElementById("chat-scroll");
    el.scrollTop = el.scrollHeight;
  }

  async function handleSend(overrideText) {
    if (sending) return;
    const textarea = document.getElementById("composer-input");
    const text = (overrideText || textarea.value).trim();
    if (!text) return;

    sending = true;
    document.getElementById("send-btn").disabled = true;
    document.getElementById("chat-welcome").style.display = "none";
    textarea.value = "";
    textarea.style.height = "auto";
    lastUserMessage = text;

    appendMessageBubble("user", text);
    const loadingId = appendLoadingBubble();
    scrollToBottom();

    const country = document.getElementById("jurisdiction-select").value;
    const debugMode = Settings.isDebugMode();

    try {
      const result = await Api.sendMessage({
        message: text,
        conversationId: currentConversationId,
        country,
        debug: debugMode,
      });

      currentConversationId = result.conversation_id;
      document.getElementById(loadingId).remove();

      if (result.clarification_needed) {
        appendClarificationBubble(result.clarification_needed, result.message_id);
      } else {
        appendMessageBubble("assistant", result.answer, {
          answerType: result.answer_type,
          confidence: result.confidence,
          messageId: result.message_id,
          demoMode: result.demo_mode,
        });
      }

      Evidence.render(result.citations, result.demo_mode);
      Evidence.renderDebugTrace(debugMode ? result.debug_trace : null);
      loadConversations();
    } catch (err) {
      const loadingEl = document.getElementById(loadingId);
      if (loadingEl) loadingEl.remove();
      appendErrorBubble(err.message || "Something went wrong.");
    } finally {
      sending = false;
      document.getElementById("send-btn").disabled = false;
      scrollToBottom();
    }
  }

  function appendLoadingBubble() {
    const container = document.getElementById("messages-container");
    const id = "loading-" + Date.now();
    const wrap = document.createElement("div");
    wrap.id = id;
    wrap.className = "msg assistant";
    wrap.innerHTML = `
      <div class="msg-avatar">🐾</div>
      <div class="msg-body">
        <div class="msg-content">
          <div class="loading-stages">
            ${LOADING_STAGES.map((s, i) => `<div class="loading-stage" data-stage="${i}"><span class="dot"></span>${s}</div>`).join("")}
          </div>
        </div>
      </div>`;
    container.appendChild(wrap);

    let stage = 0;
    const stages = wrap.querySelectorAll(".loading-stage");
    stages[0].classList.add("active");
    const interval = setInterval(() => {
      stages[stage].classList.remove("active");
      stages[stage].classList.add("done");
      stage++;
      if (stage < stages.length) {
        stages[stage].classList.add("active");
      } else {
        clearInterval(interval);
      }
    }, 550);
    wrap.dataset.interval = interval;

    return id;
  }

  function appendMessageBubble(role, content, opts = {}) {
    const container = document.getElementById("messages-container");
    const wrap = document.createElement("div");
    wrap.className = `msg ${role}`;

    const badges = [];
    if (opts.answerType && role === "assistant") {
      badges.push(`<span class="badge badge-${opts.answerType}">${Utils.titleCase(opts.answerType)}</span>`);
    }
    if (opts.confidence && opts.confidence !== "n/a" && role === "assistant") {
      badges.push(`<span class="badge badge-educational badge-confidence-${opts.confidence}">● ${Utils.titleCase(opts.confidence)} confidence</span>`);
    }
    if (opts.demoMode) {
      badges.push(`<span class="badge badge-clarification">Demo mode</span>`);
    }

    const bodyHtml = role === "assistant" ? Utils.renderAnswerMarkdown(content) : `<p>${Utils.escapeHtml(content)}</p>`;

    wrap.innerHTML = `
      <div class="msg-avatar">${role === "user" ? "🧑" : "🐾"}</div>
      <div class="msg-body">
        <div class="msg-role-label">${role === "user" ? "You" : "Animal Rights AI"} ${badges.join(" ")}</div>
        <div class="msg-content">${bodyHtml}</div>
        ${role === "assistant" ? renderMessageActions(opts.messageId) : ""}
      </div>`;

    container.appendChild(wrap);

    if (role === "assistant") bindMessageActions(wrap, content, opts.messageId);
    scrollToBottom();
    return wrap;
  }

  function renderMessageActions(messageId) {
    return `
      <div class="msg-actions">
        <button class="msg-icon-btn copy-btn" title="Copy answer">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
          Copy
        </button>
        <button class="msg-icon-btn regen-btn" title="Regenerate answer">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 4v6h6"/><path d="M3.51 15a9 9 0 102.13-9.36L1 10"/></svg>
          Regenerate
        </button>
        <div class="feedback-buttons">
          <button class="msg-icon-btn feedback-up" data-rating="1" title="Helpful">👍</button>
          <button class="msg-icon-btn feedback-down" data-rating="-1" title="Not helpful">👎</button>
        </div>
      </div>`;
  }

  function bindMessageActions(wrap, content, messageId) {
    const copyBtn = wrap.querySelector(".copy-btn");
    if (copyBtn) copyBtn.addEventListener("click", () => Utils.copyToClipboard(content));

    const regenBtn = wrap.querySelector(".regen-btn");
    if (regenBtn) regenBtn.addEventListener("click", () => handleSend(lastUserMessage));

    wrap.querySelectorAll(".feedback-buttons button").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!messageId) return Utils.toast("Feedback needs a saved backend connection.");
        const rating = parseInt(btn.dataset.rating, 10);
        try {
          await Api.submitFeedback({ messageId, rating });
          wrap.querySelectorAll(".feedback-buttons button").forEach((b) => b.classList.remove("active"));
          btn.classList.add("active");
          Utils.toast(rating > 0 ? "Thanks for the feedback!" : "Thanks — we'll use this to improve retrieval.");
        } catch (err) {
          Utils.toast(err.message);
        }
      });
    });
  }

  function appendErrorBubble(message) {
    const container = document.getElementById("messages-container");
    const wrap = document.createElement("div");
    wrap.className = "msg assistant";
    wrap.innerHTML = `
      <div class="msg-avatar">🐾</div>
      <div class="msg-body">
        <div class="msg-error">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          <span>${Utils.escapeHtml(message)}</span>
        </div>
      </div>`;
    container.appendChild(wrap);
  }

  function appendClarificationBubble(question, messageId) {
    const container = document.getElementById("messages-container");
    const wrap = document.createElement("div");
    wrap.className = "msg assistant";
    const jurisdictions = ["United Kingdom", "United States", "European Union", "International"];
    wrap.innerHTML = `
      <div class="msg-avatar">🐾</div>
      <div class="msg-body">
        <div class="msg-role-label">Animal Rights AI <span class="badge badge-clarification">Clarification needed</span></div>
        <div class="msg-clarification">
          <p style="margin:0;">${Utils.escapeHtml(question)}</p>
          <div class="clarification-chips">
            ${jurisdictions.map((j) => `<button class="clarification-chip" data-j="${j}">${j}</button>`).join("")}
          </div>
        </div>
      </div>`;
    container.appendChild(wrap);
    wrap.querySelectorAll(".clarification-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        document.getElementById("jurisdiction-select").value = chip.dataset.j.toLowerCase();
        handleSend(lastUserMessage);
      });
    });
  }

  function askAbout(documentTitle) {
    App.navigate("chat");
    document.getElementById("composer-input").value = `Tell me about "${documentTitle}" and what it covers.`;
    handleSend();
  }

  return { init, handleSend, startNewConversation, askAbout, checkStatus };
})();
