/* =============================================================================
   knowledge.js — Animal Rights AI
   Knowledge Base explorer: document grid, filters, stats, detail modal.
   ============================================================================= */

const Knowledge = (() => {
  let allDocs = [];
  let loaded = false;

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

  const ANIMAL_EMOJI = {
    dogs: "🐕", cats: "🐈", farm_animals: "🐄", wildlife: "🐘", reptiles: "🐢",
    birds: "🦅", marine: "🐋", horses: "🐎", primate: "🐒", laboratory_animals: "🧪",
    poultry: "🐓", livestock: "🐄", endangered_species: "🦏", zoo_animals: "🦁", companion_animals: "🐾",
  };

  async function init() {
    bindFilters();
    bindModal();
    await loadDocs();
  }

  async function loadDocs() {
    const grid = document.getElementById("doc-grid");
    grid.innerHTML = `<div class="skeleton" style="height:180px;"></div><div class="skeleton" style="height:180px;"></div><div class="skeleton" style="height:180px;"></div>`;
    try {
      allDocs = await Api.getDocuments();
      loaded = true;
      populateFilterOptions();
      renderStats();
      renderGrid(allDocs);
      updateHeroStat();
    } catch (err) {
      grid.innerHTML = `<div class="empty-state"><h3>Could not load the knowledge base</h3><p>${Utils.escapeHtml(err.message)}</p></div>`;
    }
  }

  function updateHeroStat() {
    const el = document.getElementById("hero-stat-docs");
    if (el) el.textContent = allDocs.length || "—";
  }

  function renderStats() {
    const el = document.getElementById("kb-stats-row");
    const countries = new Set(allDocs.map((d) => d.country).filter(Boolean));
    const types = new Set(allDocs.map((d) => d.document_type).filter(Boolean));
    const synthetic = allDocs.filter((d) => d.is_synthetic).length;
    el.innerHTML = `
      <div class="stat-card"><div class="num">${allDocs.length}</div><div class="lbl">Documents</div></div>
      <div class="stat-card"><div class="num">${countries.size}</div><div class="lbl">Jurisdictions</div></div>
      <div class="stat-card"><div class="num">${types.size}</div><div class="lbl">Document types</div></div>
      <div class="stat-card"><div class="num">${synthetic}</div><div class="lbl">Synthetic (test) docs</div></div>
    `;
  }

  function populateFilterOptions() {
    const countrySel = document.getElementById("kb-filter-country");
    const typeSel = document.getElementById("kb-filter-type");
    const topicSel = document.getElementById("kb-filter-topic");
    const animalSel = document.getElementById("kb-filter-animal");

    fillSelect(countrySel, uniqueSorted(allDocs.map((d) => d.country)), Utils.titleCase);
    fillSelect(typeSel, uniqueSorted(allDocs.map((d) => d.document_type)), Utils.titleCase);
    fillSelect(topicSel, uniqueSorted(allDocs.flatMap((d) => d.topics || [])), Utils.titleCase);
    fillSelect(animalSel, uniqueSorted(allDocs.flatMap((d) => d.animal_categories || [])), Utils.titleCase);
  }

  function uniqueSorted(arr) {
    return [...new Set(arr.filter(Boolean))].sort();
  }

  function fillSelect(selectEl, values, labelFn) {
    const existing = new Set(Array.from(selectEl.options).map((o) => o.value));
    values.forEach((v) => {
      if (!existing.has(v)) {
        const opt = document.createElement("option");
        opt.value = v;
        opt.textContent = labelFn(v);
        selectEl.appendChild(opt);
      }
    });
  }

  function bindFilters() {
    ["kb-filter-country", "kb-filter-type", "kb-filter-topic", "kb-filter-animal"].forEach((id) => {
      document.getElementById(id).addEventListener("change", applyFilters);
    });
    document.getElementById("kb-filter-clear").addEventListener("click", () => {
      ["kb-filter-country", "kb-filter-type", "kb-filter-topic", "kb-filter-animal"].forEach((id) => {
        document.getElementById(id).value = "";
      });
      applyFilters();
    });
  }

  function applyFilters() {
    const country = document.getElementById("kb-filter-country").value;
    const type = document.getElementById("kb-filter-type").value;
    const topic = document.getElementById("kb-filter-topic").value;
    const animal = document.getElementById("kb-filter-animal").value;

    const filtered = allDocs.filter((d) => {
      if (country && d.country !== country) return false;
      if (type && d.document_type !== type) return false;
      if (topic && !(d.topics || []).includes(topic)) return false;
      if (animal && !(d.animal_categories || []).includes(animal)) return false;
      return true;
    });
    renderGrid(filtered);
  }

  function renderGrid(docs) {
    const grid = document.getElementById("doc-grid");
    if (!docs.length) {
      grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1;"><h3>No documents match these filters</h3><p>Try clearing filters or choosing a different combination.</p></div>`;
      return;
    }
    grid.innerHTML = docs
      .map(
        (d) => `
      <button class="doc-card" data-id="${d.id}">
        <div class="doc-card-top">
          <span class="doc-icon">${DOC_TYPE_ICON[d.document_type] || "📄"}</span>
          ${d.is_synthetic ? '<span class="badge badge-synthetic">Synthetic</span>' : ""}
        </div>
        <div class="doc-title">${Utils.escapeHtml(d.title)}</div>
        <div class="doc-desc">${Utils.escapeHtml(truncate(d.description, 120))}</div>
        <div class="doc-meta-row">
          ${d.country ? `<span>🌍 ${Utils.escapeHtml(Utils.titleCase(d.country))}</span>` : ""}
          ${d.document_type ? `<span>${Utils.escapeHtml(Utils.titleCase(d.document_type))}</span>` : ""}
          ${(d.animal_categories || []).slice(0, 2).map((a) => `<span>${ANIMAL_EMOJI[a] || "🐾"} ${Utils.titleCase(a)}</span>`).join("")}
        </div>
        <div class="doc-card-footer">
          <span style="font-size:11.5px;color:var(--text-muted);">${Utils.formatDate(d.publication_date)}</span>
          <span style="font-size:12.5px;color:var(--mint);">View details →</span>
        </div>
      </button>`
      )
      .join("");

    grid.querySelectorAll(".doc-card").forEach((card) => {
      card.addEventListener("click", () => openModal(card.getAttribute("data-id")));
    });
  }

  function truncate(str, n) {
    if (!str) return "No description available.";
    return str.length > n ? str.slice(0, n).trim() + "…" : str;
  }

  function bindModal() {
    document.getElementById("modal-close-btn").addEventListener("click", closeModal);
    document.getElementById("doc-modal").addEventListener("click", (e) => {
      if (e.target.id === "doc-modal") closeModal();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeModal();
    });
  }

  function openModal(docId) {
    const doc = allDocs.find((d) => d.id === docId);
    if (!doc) return;

    document.getElementById("modal-title").textContent = doc.title;
    document.getElementById("modal-desc").textContent = doc.description || "";
    document.getElementById("modal-meta-grid").innerHTML = `
      ${metaField("Document type", Utils.titleCase(doc.document_type))}
      ${metaField("Jurisdiction", doc.jurisdiction || "—")}
      ${metaField("Country", Utils.titleCase(doc.country) || "—")}
      ${metaField("Language", doc.language || "—")}
      ${metaField("Author", doc.author || "—")}
      ${metaField("Organization", doc.organization || "—")}
      ${metaField("Published", Utils.formatDate(doc.publication_date))}
      ${metaField("Synthetic document", doc.is_synthetic ? "Yes — demonstration only" : "No")}
    `;
    document.getElementById("modal-topics").innerHTML = [...(doc.topics || []), ...(doc.animal_categories || [])]
      .map((t) => `<span class="badge badge-educational">${Utils.titleCase(t)}</span>`)
      .join("");

    const link = document.getElementById("modal-source-link");
    if (doc.source_url) {
      link.href = doc.source_url;
      link.style.display = "inline-flex";
    } else {
      link.style.display = "none";
    }

    document.getElementById("modal-ask-btn").onclick = () => {
      closeModal();
      Chat.askAbout(doc.title);
    };

    document.getElementById("doc-modal").classList.add("open");
  }

  function metaField(label, value) {
    return `<div><div class="mk">${label}</div><div class="mv">${Utils.escapeHtml(value || "—")}</div></div>`;
  }

  function closeModal() {
    document.getElementById("doc-modal").classList.remove("open");
  }

  return { init, loadDocs, get docs() { return allDocs; }, get isLoaded() { return loaded; } };
})();
