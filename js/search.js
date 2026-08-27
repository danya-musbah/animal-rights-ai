/* =============================================================================
   search.js — Animal Rights AI
   Dedicated semantic/hybrid search page: query box, filters, ranked results.
   ============================================================================= */

const Search = (() => {
  let filtersPopulated = false;

  function init() {
    document.getElementById("search-form").addEventListener("submit", (e) => {
      e.preventDefault();
      runSearch();
    });
    populateFiltersFromKnowledge();
  }

  async function populateFiltersFromKnowledge() {
    if (filtersPopulated) return;
    // Reuse whatever Knowledge.js already loaded (or trigger a load) so the
    // Search page's filters stay consistent with the Knowledge Base explorer.
    if (!Knowledge.isLoaded) await Knowledge.loadDocs();
    const docs = Knowledge.docs;
    const countrySel = document.getElementById("search-filter-country");
    const typeSel = document.getElementById("search-filter-type");
    [...new Set(docs.map((d) => d.country).filter(Boolean))].sort().forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c;
      opt.textContent = Utils.titleCase(c);
      countrySel.appendChild(opt);
    });
    [...new Set(docs.map((d) => d.document_type).filter(Boolean))].sort().forEach((t) => {
      const opt = document.createElement("option");
      opt.value = t;
      opt.textContent = Utils.titleCase(t);
      typeSel.appendChild(opt);
    });
    filtersPopulated = true;
  }

  async function runSearch() {
    const query = document.getElementById("search-input").value.trim();
    const resultsEl = document.getElementById("search-results");
    if (!query) return;

    resultsEl.innerHTML = `<div class="skeleton" style="height:90px;margin-bottom:12px;"></div><div class="skeleton" style="height:90px;margin-bottom:12px;"></div><div class="skeleton" style="height:90px;"></div>`;

    const country = document.getElementById("search-filter-country").value;
    const documentType = document.getElementById("search-filter-type").value;

    try {
      const result = await Api.searchKnowledgeBase({ query, country, documentType, topK: 10 });
      renderResults(result.results, query);
    } catch (err) {
      resultsEl.innerHTML = `<div class="empty-state"><h3>Search failed</h3><p>${Utils.escapeHtml(err.message)}</p></div>`;
    }
  }

  function renderResults(results, query) {
    const el = document.getElementById("search-results");
    if (!results || !results.length) {
      el.innerHTML = `<div class="empty-state"><h3>No relevant evidence was found in the current knowledge base.</h3><p>Try a broader query, or check the Knowledge Base page to see what's currently covered.</p></div>`;
      return;
    }
    el.innerHTML = results
      .map(
        (r, i) => `
      <article class="search-result-item">
        <div class="search-result-rank">#${i + 1} · similarity ${r.similarity.toFixed(2)}</div>
        <div class="search-result-title">${Utils.escapeHtml(r.document_title)}</div>
        <div class="doc-meta-row" style="margin-bottom:8px;">
          ${r.document_type ? `<span>${Utils.escapeHtml(Utils.titleCase(r.document_type))}</span>` : ""}
          ${r.jurisdiction ? `<span>${Utils.escapeHtml(r.jurisdiction)}</span>` : ""}
          ${r.page ? `<span>p. ${r.page}</span>` : ""}
        </div>
        <p class="search-result-excerpt">"${Utils.escapeHtml(r.excerpt)}"</p>
        <div class="search-result-footer">
          ${r.source_url ? `<a href="${Utils.escapeHtml(r.source_url)}" target="_blank" rel="noopener">Open source ↗</a>` : "<span></span>"}
          <button class="btn btn-ghost btn-sm ask-about-btn" data-doc="${Utils.escapeHtml(r.document_title)}">Ask about this →</button>
        </div>
      </article>`
      )
      .join("");

    el.querySelectorAll(".ask-about-btn").forEach((btn) => {
      btn.addEventListener("click", () => Chat.askAbout(btn.dataset.doc));
    });
  }

  return { init };
})();
