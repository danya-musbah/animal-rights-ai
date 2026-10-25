/* Renders the local Feather icon set, including icons added by dynamic views. */
(() => {
  if (!window.feather) {
    console.error("The local Feather icon library could not be loaded.");
    return;
  }

  const renderIcons = () => window.feather.replace({ class: "ui-icon" });

  renderIcons();
  new MutationObserver((mutations) => {
    const addedIcons = mutations.some((mutation) =>
      Array.from(mutation.addedNodes).some(
        (node) =>
          node.nodeType === Node.ELEMENT_NODE &&
          (node.matches("[data-feather]") || node.querySelector("[data-feather]"))
      )
    );
    if (addedIcons) renderIcons();
  }).observe(document.body, { childList: true, subtree: true });
})();
