/* =============================================================================
   app.js — Animal Rights AI
   View routing (SPA-style section switching), landing page topic grid,
   RAG Pipeline visualization page, Analytics page, and app bootstrap.
   ============================================================================= */

const App = (() => {
  const VIEWS = ["landing", "chat", "knowledge", "search", "pipeline", "analytics", "settings"];

  const LANDING_TOPICS = [
    { emoji: "⚖️", title: "Legislation", desc: "UK, US, and EU statutes and regulations", nav: "knowledge" },
    { emoji: "🐄", title: "Farm Animals", desc: "Transport, housing, and slaughter standards", nav: "knowledge" },
    { emoji: "🐕", title: "Companion Animals", desc: "Welfare needs, tethering, shelters", nav: "knowledge" },
    { emoji: "🐘", title: "Wildlife & Endangered Species", desc: "CITES, the ESA, and conservation law", nav: "knowledge" },
    { emoji: "🧪", title: "Laboratory Animals", desc: "The Three Rs and testing regulation", nav: "knowledge" },
    { emoji: "🧠", title: "Scientific Research", desc: "Sentience science and welfare evidence", nav: "knowledge" },
    { emoji: "🌍", title: "International Standards", desc: "WOAH, treaties, and cross-border rules", nav: "knowledge" },
    { emoji: "🗂️", title: "Organizations", desc: "RSPCA, HSUS, PETA, WWF, and more", nav: "knowledge" },
  ];

  const PIPELINE_STEPS = [
    { icon: "💬", title: "User Question", desc: "A natural-language question enters the system, optionally with prior conversation context and a jurisdiction filter." },
    { icon: "🧭", title: "Query Analysis & Understanding", desc: "The question is analyzed to extract intent, animal(s), topic(s), country/jurisdiction, and a document-type hint. If it's a legal question with no jurisdiction, the pipeline pauses to ask for one instead of guessing.", tags: ["intent", "jurisdiction", "topic extraction"] },
    { icon: "🔎", title: "Hybrid Retrieval", desc: "Semantic (vector/pgvector) search and PostgreSQL full-text keyword search run in parallel against document_chunks, each returning a top-K candidate list.", tags: ["semantic search", "keyword search", "pgvector", "PostgreSQL FTS"] },
    { icon: "🔀", title: "Fusion (Reciprocal Rank Fusion)", desc: "The two ranked candidate lists are merged and de-duplicated using Reciprocal Rank Fusion, producing a single fused candidate pool.", tags: ["RRF", "deduplication"] },
    { icon: "🎯", title: "Reranking", desc: "The fused pool is reranked — via a dedicated API reranker if configured, or a transparent heuristic combining fused score and lexical overlap otherwise — down to the final top 5–8 chunks.", tags: ["cross-encoder (optional)", "heuristic fallback"] },
    { icon: "🚦", title: "Relevance Thresholding", desc: "If the top reranked score falls below a configurable minimum, the pipeline stops and reports insufficient evidence rather than forcing a generation.", tags: ["hallucination protection"] },
    { icon: "📦", title: "Context Construction", desc: "The surviving chunks are formatted into a numbered evidence block with source, jurisdiction, section, and page metadata attached to each entry." },
    { icon: "🐾", title: "Grounded LLM Generation", desc: "The LLM receives a strict system prompt requiring it to answer only from the provided evidence, cite every claim, identify jurisdiction, and distinguish law from science from ethics." },
    { icon: "🔖", title: "Citation Mapping", desc: "[n] markers in the answer are mapped back to the exact retrieved chunks — never fabricated, never pointing outside the retrieved set." },
    { icon: "✅", title: "Answer + Citations + Evidence", desc: "The final structured response — answer, answer-type badge, confidence, and evidence panel — is returned to the user." },
  ];

  function init() {
    bindNav();
    Chat.init();
    Knowledge.init();
    Search.init();
    Settings.init();
    renderLandingTopics();
    renderPipelineFlow();
    bindPipelineDemo();
    loadAnalytics();
  }

  function bindNav() {
    document.querySelectorAll("[data-nav]").forEach((el) => {
      el.addEventListener("click", (e) => {
        e.preventDefault();
        navigate(el.getAttribute("data-nav"));
      });
    });
    document.getElementById("mobile-menu-btn").addEventListener("click", () => {
      const links = document.querySelector(".nav-links");
      const isOpen = links.style.display === "flex";
      links.style.display = isOpen ? "none" : "flex";
      links.style.position = "fixed";
      links.style.top = "var(--nav-height)";
      links.style.left = "0";
      links.style.right = "0";
      links.style.flexDirection = "column";
      links.style.background = "var(--bg-elevated)";
      links.style.padding = "10px";
      links.style.borderBottom = "1px solid var(--border)";
      links.style.zIndex = "39";
    });
  }

  function navigate(viewName) {
    if (!VIEWS.includes(viewName)) return;
    VIEWS.forEach((v) => {
      const el = document.getElementById(`view-${v}`);
      if (el) el.classList.toggle("active", v === viewName);
    });
    document.querySelectorAll(".nav-link").forEach((el) => {
      el.classList.toggle("active", el.getAttribute("data-nav") === viewName);
    });
    window.scrollTo({ top: 0 });

    if (viewName === "analytics") loadAnalytics();
  }

  function renderLandingTopics() {
    const grid = document.getElementById("landing-topic-grid");
    grid.innerHTML = LANDING_TOPICS.map(
      (t) => `
      <button class="topic-card" data-nav="${t.nav}">
        <div class="emoji">${t.emoji}</div>
        <div class="title">${t.title}</div>
        <div class="desc">${t.desc}</div>
      </button>`
    ).join("");
    grid.querySelectorAll("[data-nav]").forEach((el) => {
      el.addEventListener("click", () => navigate(el.getAttribute("data-nav")));
    });
  }

  function renderPipelineFlow() {
    const el = document.getElementById("pipeline-flow");
    el.innerHTML = PIPELINE_STEPS.map(
      (s, i) => `
      <div class="pipeline-step">
        <div class="pipeline-step-marker">
          <div class="pipeline-dot">${s.icon}</div>
          ${i < PIPELINE_STEPS.length - 1 ? '<div class="pipeline-line"></div>' : ""}
        </div>
        <div class="pipeline-content">
          <h3>${i + 1}. ${s.title}</h3>
          <p>${s.desc}</p>
          ${s.tags ? `<div class="pipeline-tag-row">${s.tags.map((t) => `<span class="badge badge-educational">${t}</span>`).join("")}</div>` : ""}
        </div>
      </div>`
    ).join("");
  }

  function bindPipelineDemo() {
    document.getElementById("pipeline-demo-run").addEventListener("click", async () => {
      const input = document.getElementById("pipeline-demo-input");
      const output = document.getElementById("pipeline-demo-output");
      const question = input.value.trim();
      if (!question) return;

      output.innerHTML = `<div class="skeleton" style="height:120px;"></div>`;
      try {
        const result = await Api.sendMessage({ message: question, debug: true });
        let html = `<div style="margin-bottom:14px;">
          <span class="badge badge-${result.answer_type}">${Utils.titleCase(result.answer_type)}</span>
          <span class="badge badge-educational badge-confidence-${result.confidence}">● ${Utils.titleCase(result.confidence)} confidence</span>
        </div>`;
        html += `<div class="msg-content" style="margin-bottom:16px;">${Utils.renderAnswerMarkdown(result.answer)}</div>`;

        if (result.debug_trace) {
          html += `<div class="debug-panel" style="display:block;border-top:none;padding:0;">`;
          (result.debug_trace.stages || []).forEach((stage) => {
            html += `<h4>${Utils.escapeHtml(stage.stage)}</h4><div class="debug-json">${Utils.escapeHtml(JSON.stringify(stage.data, null, 2))}</div>`;
          });
          html += `</div>`;
        }
        output.innerHTML = html;
      } catch (err) {
        output.innerHTML = `<div class="empty-state"><h3>Could not run the pipeline</h3><p>${Utils.escapeHtml(err.message)}</p></div>`;
      }
    });
  }

  async function loadAnalytics() {
    const grid = document.getElementById("analytics-grid");
    const topicsEl = document.getElementById("analytics-topics");
    const countriesEl = document.getElementById("analytics-countries");
    grid.innerHTML = `<div class="skeleton" style="height:90px;"></div><div class="skeleton" style="height:90px;"></div><div class="skeleton" style="height:90px;"></div>`;
    try {
      const a = await Api.getAnalytics();
      grid.innerHTML = `
        <div class="analytics-card"><div class="num">${a.total_documents}</div><div class="lbl">Documents</div></div>
        <div class="analytics-card"><div class="num">${a.total_chunks}</div><div class="lbl">Chunks</div></div>
        <div class="analytics-card"><div class="num">${a.total_conversations}</div><div class="lbl">Conversations</div></div>
        <div class="analytics-card"><div class="num">${a.total_messages}</div><div class="lbl">Questions asked</div></div>
        <div class="analytics-card positive"><div class="num">${a.positive_feedback}</div><div class="lbl">👍 Positive feedback</div></div>
        <div class="analytics-card negative"><div class="num">${a.negative_feedback}</div><div class="lbl">👎 Negative feedback</div></div>
      `;
      topicsEl.innerHTML = renderBarList(a.top_topics, "topic");
      countriesEl.innerHTML = renderBarList(a.top_countries, "country");

      if (a.source && a.source.includes("demo")) {
        Utils.toast("Analytics shown from the local manifest (demo mode) — connect Supabase for live usage stats.");
      }
    } catch (err) {
      grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1;"><h3>Could not load analytics</h3><p>${Utils.escapeHtml(err.message)}</p></div>`;
    }
  }

  function renderBarList(items, key) {
    if (!items || !items.length) return `<p style="color:var(--text-muted);font-size:13px;">No data yet.</p>`;
    const max = Math.max(...items.map((i) => i.count));
    return items
      .map(
        (i) => `
      <div class="bar-row">
        <span class="bar-label">${Utils.titleCase(i[key])}</span>
        <div class="bar-track"><div class="bar-fill" style="width:${Math.round((i.count / max) * 100)}%"></div></div>
        <span class="bar-count">${i.count}</span>
      </div>`
      )
      .join("");
  }

  return { init, navigate };
})();

document.addEventListener("DOMContentLoaded", App.init);
