/* =============================================================================
   utils.js — Animal Rights AI
   Small, dependency-free helper functions shared across modules.
   ============================================================================= */

const Utils = (() => {
  function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function debounce(fn, wait = 300) {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), wait);
    };
  }

  function toast(message, kind = "info") {
    const root = document.getElementById("toast-root");
    if (!root) return;
    const el = document.createElement("div");
    el.className = "toast";
    el.textContent = message;
    root.appendChild(el);
    setTimeout(() => {
      el.style.opacity = "0";
      el.style.transition = "opacity 0.25s ease";
      setTimeout(() => el.remove(), 260);
    }, 3200);
  }

  function titleCase(str) {
    if (!str) return "";
    return str
      .replace(/_/g, " ")
      .split(" ")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");
  }

  function formatDate(dateStr) {
    if (!dateStr) return "Undated";
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
    } catch {
      return dateStr;
    }
  }

  function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => toast("Copied to clipboard"));
    } else {
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
      toast("Copied to clipboard");
    }
  }

  // Converts the structured "Answer / Key points / Sources" markdown-ish text
  // from the LLM into safe HTML, turning [n] into clickable citation markers.
  function renderAnswerMarkdown(text) {
    if (!text) return "";
    const lines = text.split("\n");
    let html = "";
    let inList = false;

    const closeList = () => {
      if (inList) {
        html += "</ul>";
        inList = false;
      }
    };

    for (let raw of lines) {
      const line = raw.trim();
      if (!line) {
        closeList();
        continue;
      }
      if (/^(answer|key points|sources|confidence.*)$/i.test(line)) {
        closeList();
        html += `<h4>${escapeHtml(line)}</h4>`;
        continue;
      }
      if (/^[-•]\s+/.test(line)) {
        if (!inList) {
          html += "<ul>";
          inList = true;
        }
        html += `<li>${linkifyCitations(escapeHtml(line.replace(/^[-•]\s+/, "")))}</li>`;
        continue;
      }
      closeList();
      html += `<p>${linkifyCitations(escapeHtml(line))}</p>`;
    }
    closeList();
    return html;
  }

  function linkifyCitations(escapedText) {
    return escapedText.replace(/\[(\d{1,2})\]/g, (m, n) => {
      return `<span class="cite-marker" data-citation="${n}" role="button" tabindex="0" title="Jump to source ${n}">${n}</span>`;
    });
  }

  function debounceAsync(fn, wait = 300) {
    let t;
    return (...args) =>
      new Promise((resolve) => {
        clearTimeout(t);
        t = setTimeout(() => resolve(fn(...args)), wait);
      });
  }

  return {
    escapeHtml,
    debounce,
    toast,
    titleCase,
    formatDate,
    copyToClipboard,
    renderAnswerMarkdown,
    linkifyCitations,
  };
})();
