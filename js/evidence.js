/* =============================================================================
   evidence.js — Animal Rights AI
   Renders the evidence panel (citations + retrieval scores + excerpts) and
   the optional Retrieval Debug Mode trace. Also handles click-to-highlight
   linking between inline [n] citation markers in the chat and evidence cards.
   ============================================================================= */

const Evidence = (() => {
  const scrollEl = () => document.getElementById("evidence-scroll");
  const debugEl = () => document.getElementById("debug-panel");

  const DOC_TYPE_ICON = {
    legislation: "⚖️",
    regulation: "📜",
    government_guidance: "🏛️",
    scientific_research: "🔬",
    academic_paper: "📖",
    organization_report: "🗂️",
    organization_policy: "🗂️",
    international_standard: "🌍",
    policy: "📋",
    educational_material: "🎓",
    other: "📄",
  };

  function render(citations, demoMode) {
    const el = scrollEl();
    if (!citations || citations.length === 0) {
      el.innerHTML = `
        <div class="empty-state">
          <span class="paw-mark"><svg width="34" height="34" viewBox="0 0 100 100"><circle class="node" cx="50" cy="58" r="15"/><circle class="node" cx="28" cy="38" r="8"/><circle class="node" cx="50" cy="28" r="8"/><circle class="node" cx="72" cy="38" r="8"/></svg></span>
          <h3>${demoMode ? "Demo mode" : "No relevant evidence was found"}</h3>
          <p>${
            demoMode
              ? "Connect Supabase and configure an LLM provider to enable full RAG functionality."
              : "The current knowledge base did not contain sufficient evidence for this question."
          }</p>
        </div>`;
      return;
    }

    el.innerHTML = citations
      .map((c) => {
        const scorePct = Math.max(2, Math.min(100, Math.round((c.relevance_score || 0) * 100)));
        const metaBits = [];
        if (c.document_type) metaBits.push(`<span>${DOC_TYPE_ICON[c.document_type] || "📄"} ${Utils.titleCase(c.document_type)}</span>`);
        if (c.jurisdiction) metaBits.push(`<span>${Utils.escapeHtml(c.jurisdiction)}</span>`);
        if (c.section) metaBits.push(`<span>§ ${Utils.escapeHtml(c.section)}</span>`);
        if (c.page) metaBits.push(`<span>p. ${c.page}</span>`);

        return `
          <article class="evidence-card" id="evidence-card-${c.citation_index}" data-citation="${c.citation_index}">
            <div class="evidence-card-top">
              <span class="evidence-index">${c.citation_index}</span>
              <span class="evidence-title">${Utils.escapeHtml(c.document_title || "Untitled source")}</span>
            </div>
            <div class="evidence-meta">${metaBits.join("")}</div>
            <p class="evidence-excerpt">"${Utils.escapeHtml(truncate(c.excerpt, 220))}"</p>
            <div class="evidence-score-row">
              <div class="relevance-bar-track"><div class="relevance-bar-fill" style="width:${scorePct}%"></div></div>
              <span class="relevance-score-label">${(c.relevance_score || 0).toFixed(2)}</span>
            </div>
            ${
              c.source_url
                ? `<a class="evidence-open-link" href="${Utils.escapeHtml(c.source_url)}" target="_blank" rel="noopener">Open official source ↗</a>`
                : ""
            }
          </article>`;
      })
      .join("");
  }

  function truncate(str, n) {
    if (!str) return "";
    return str.length > n ? str.slice(0, n).trim() + "…" : str;
  }

  function highlight(index) {
    document.querySelectorAll(".evidence-card.highlight").forEach((c) => c.classList.remove("highlight"));
    const card = document.getElementById(`evidence-card-${index}`);
    if (card) {
      card.classList.add("highlight");
      card.scrollIntoView({ behavior: "smooth", block: "center" });
      // On mobile, ensure the drawer is open so the highlight is visible
      const panel = document.getElementById("evidence-panel");
      if (window.innerWidth <= 1024) panel.classList.add("open");
    }
  }

  function renderDebugTrace(trace) {
    const el = debugEl();
    if (!trace) {
      el.style.display = "none";
      el.innerHTML = "";
      return;
    }
    el.style.display = "block";

    let html = `<h4>🐾 Retrieval Debug Trace (${trace.latency_ms || "?"} ms)</h4>`;
    (trace.stages || []).forEach((stage) => {
      html += `<h4>${Utils.escapeHtml(stage.stage)}</h4>`;
      html += `<div class="debug-json">${Utils.escapeHtml(JSON.stringify(stage.data, null, 2))}</div>`;
    });
    el.innerHTML = html;
  }

  function attachClickHandlers(container) {
    container.addEventListener("click", (e) => {
      const marker = e.target.closest(".cite-marker");
      if (marker) {
        const idx = marker.getAttribute("data-citation");
        highlight(idx);
        document.querySelectorAll(`.cite-marker[data-citation="${idx}"]`).forEach((m) => {
          m.classList.add("flash");
          setTimeout(() => m.classList.remove("flash"), 500);
        });
      }
    });
  }

  return { render, highlight, renderDebugTrace, attachClickHandlers };
})();
