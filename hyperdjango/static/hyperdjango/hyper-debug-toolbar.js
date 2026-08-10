(function () {
  if (window.__hyperDebugToolbarInstalled) {
    return;
  }
  window.__hyperDebugToolbarInstalled = true;

  function targetsBody(target) {
    if (target === document.body) {
      return true;
    }
    if (typeof target !== "string" || !target) {
      return false;
    }
    try {
      return document.querySelector(target) === document.body;
    } catch {
      return false;
    }
  }

  window.addEventListener("hyper:settle:end", (event) => {
    if (!targetsBody(event.detail && event.detail.target)) {
      return;
    }
    if (
      document.getElementById("djDebug") &&
      window.djdt &&
      typeof window.djdt.show_toolbar === "function"
    ) {
      window.djdt.show_toolbar();
    }
  });
})();
