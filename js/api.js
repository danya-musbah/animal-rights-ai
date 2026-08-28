/* =============================================================================
   api.js — Animal Rights AI
   Single, centralised layer for all communication with the FastAPI backend.
   No other file should call fetch() directly against the backend — this keeps
   endpoint URLs, error handling, and request shaping in one place.
   ============================================================================= */

const Api = (() => {
  const LOCAL_API_BASE = "http://localhost:8000/api";

  function isLocalDevelopment() {
    return window.location.protocol === "file:" || ["localhost", "127.0.0.1", "[::1]"].includes(window.location.hostname);
  }

  function isLocalApiUrl(url) {
    try {
      return ["localhost", "127.0.0.1", "[::1]"].includes(new URL(url).hostname);
    } catch {
      return false;
    }
  }

  function getBaseUrl() {
    const configured = localStorage.getItem("ara_api_base")?.trim();
    if (configured && (isLocalDevelopment() || !isLocalApiUrl(configured))) return configured;
    return isLocalDevelopment() ? LOCAL_API_BASE : "";
  }

  function setBaseUrl(url) {
    localStorage.setItem("ara_api_base", url);
  }

  async function request(path, options = {}) {
    const base = getBaseUrl();
    if (!base) {
      throw new ApiError(
        "No production API is configured. Open Settings and enter the public FastAPI API base URL.",
        0
      );
    }
    let response;
    try {
      response = await fetch(`${base}${path}`, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options,
      });
    } catch (networkErr) {
      throw new ApiError(
        "Could not reach the Animal Rights AI backend. Is it running? Check Settings for the API base URL.",
        0,
        networkErr
      );
    }

    if (!response.ok) {
      let detail = `Request failed (${response.status})`;
      try {
        const body = await response.json();
        detail = body.detail || detail;
      } catch {
        /* ignore parse errors */
      }
      throw new ApiError(detail, response.status);
    }

    if (response.status === 204) return null;
    return response.json();
  }

  class ApiError extends Error {
    constructor(message, status, cause) {
      super(message);
      this.status = status;
      this.cause = cause;
    }
  }

  // ---- Health ----
  function getHealth() {
    return request("/health");
  }

  // ---- Chat ----
  function sendMessage({ message, conversationId, country, debug, forceJurisdictionSkip }) {
    return request("/chat", {
      method: "POST",
      body: JSON.stringify({
        message,
        conversation_id: conversationId || null,
        country: country || null,
        debug: !!debug,
        force_jurisdiction_skip: !!forceJurisdictionSkip,
      }),
    });
  }

  // ---- Search ----
  function searchKnowledgeBase({ query, country, documentType, topK }) {
    return request("/search", {
      method: "POST",
      body: JSON.stringify({
        query,
        country: country || null,
        document_type: documentType || null,
        top_k: topK || 10,
      }),
    });
  }

  // ---- Documents ----
  function getDocuments(filters = {}) {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => v && params.set(k, v));
    const qs = params.toString();
    return request(`/documents${qs ? `?${qs}` : ""}`);
  }

  function getDocument(id) {
    return request(`/documents/${encodeURIComponent(id)}`);
  }

  function uploadDocument(file) {
    const base = getBaseUrl();
    if (!base) {
      return Promise.reject(
        new ApiError("No production API is configured. Open Settings and enter the public FastAPI API base URL.", 0)
      );
    }
    const formData = new FormData();
    formData.append("file", file);
    return fetch(`${base}/documents/ingest`, { method: "POST", body: formData }).then(async (r) => {
      if (!r.ok) {
        const body = await r.json().catch(() => ({}));
        throw new ApiError(body.detail || "Upload failed", r.status);
      }
      return r.json();
    });
  }

  // ---- Conversations ----
  function getConversations() {
    return request("/conversations");
  }

  function createConversation(title = "New conversation") {
    return request("/conversations", { method: "POST", body: JSON.stringify({ title }) });
  }

  function getConversation(id) {
    return request(`/conversations/${encodeURIComponent(id)}`);
  }

  function renameConversation(id, title) {
    return request(`/conversations/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    });
  }

  function deleteConversation(id) {
    return request(`/conversations/${encodeURIComponent(id)}`, { method: "DELETE" });
  }

  // ---- Feedback ----
  function submitFeedback({ messageId, rating, comment }) {
    return request("/feedback", {
      method: "POST",
      body: JSON.stringify({ message_id: messageId, rating, comment: comment || null }),
    });
  }

  // ---- Analytics ----
  function getAnalytics() {
    return request("/analytics");
  }

  return {
    getBaseUrl,
    setBaseUrl,
    ApiError,
    getHealth,
    sendMessage,
    searchKnowledgeBase,
    getDocuments,
    getDocument,
    uploadDocument,
    getConversations,
    createConversation,
    getConversation,
    renameConversation,
    deleteConversation,
    submitFeedback,
    getAnalytics,
  };
})();
