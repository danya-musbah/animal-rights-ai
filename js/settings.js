/* =============================================================================
   settings.js — Animal Rights AI
   Retrieval Debug Mode toggle, API base URL configuration, document upload,
   backend status recheck.
   ============================================================================= */

const Settings = (() => {
  let debugMode = false;

  function init() {
    debugMode = localStorage.getItem("ara_debug_mode") === "true";
    updateToggleUI();

    const toggle = document.getElementById("toggle-debug-mode");
    toggle.addEventListener("click", () => setDebugMode(!debugMode));
    toggle.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        setDebugMode(!debugMode);
      }
    });

    const apiInput = document.getElementById("api-base-input");
    apiInput.value = Api.getBaseUrl();
    apiInput.addEventListener("change", () => {
      Api.setBaseUrl(apiInput.value.trim());
      Utils.toast("API base URL updated.");
      recheckStatus();
    });

    document.getElementById("settings-recheck-btn").addEventListener("click", recheckStatus);
    document.getElementById("upload-btn").addEventListener("click", handleUpload);

    recheckStatus();
  }

  function setDebugMode(value) {
    debugMode = value;
    localStorage.setItem("ara_debug_mode", String(value));
    updateToggleUI();
    Utils.toast(value ? "Retrieval Debug Mode enabled." : "Retrieval Debug Mode disabled.");
  }

  function updateToggleUI() {
    const toggle = document.getElementById("toggle-debug-mode");
    toggle.classList.toggle("on", debugMode);
    toggle.setAttribute("aria-checked", String(debugMode));
  }

  async function recheckStatus() {
    const desc = document.getElementById("settings-status-desc");
    desc.textContent = "Checking…";
    try {
      const health = await Api.getHealth();
      const bits = [];
      bits.push(health.demo_mode ? "Demo mode" : "Fully connected");
      bits.push(`Supabase: ${health.supabase_reachable ? "reachable" : "unreachable"}`);
      bits.push(`LLM: ${health.llm_configured ? "configured" : "not configured"}`);
      bits.push(`Embeddings: ${health.embeddings_configured ? "configured" : "not configured"}`);
      bits.push(`Reranker: ${health.reranker}`);
      desc.textContent = bits.join(" · ");
    } catch (err) {
      desc.textContent = "Unreachable — " + err.message;
    }
    Chat.checkStatus();
  }

  async function handleUpload() {
    const input = document.getElementById("upload-input");
    const statusEl = document.getElementById("upload-status");
    if (!input.files || !input.files[0]) {
      statusEl.textContent = "Choose a file first.";
      return;
    }
    statusEl.textContent = "Uploading and ingesting…";
    try {
      const result = await Api.uploadDocument(input.files[0]);
      statusEl.textContent = `Done — status: ${result.status} (document id: ${result.document_id})`;
      Utils.toast("Document ingested.");
      Knowledge.loadDocs();
    } catch (err) {
      statusEl.textContent = "Upload failed: " + err.message;
    }
  }

  return { init, isDebugMode: () => debugMode };
})();
