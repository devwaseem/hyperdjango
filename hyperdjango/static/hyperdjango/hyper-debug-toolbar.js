(function () {
  if (window.__hyperDebugToolbarInstalled) {
    return;
  }
  window.__hyperDebugToolbarInstalled = true;
  let streamRefreshSequence = 0;

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

  async function refreshHyperPanel(response, sequence) {
    const contentType = response.headers.get("content-type") || "";
    const requestId = response.headers.get("djdt-request-id");
    if (!contentType.includes("text/event-stream") || !requestId) {
      return;
    }

    const toolbar = document.getElementById("djDebug");
    const renderPanelUrl = toolbar && toolbar.dataset.renderPanelUrl;
    if (!toolbar || !renderPanelUrl || sequence !== streamRefreshSequence) {
      return;
    }

    const url = new URL(renderPanelUrl, window.location.href);
    url.searchParams.set("request_id", requestId);
    url.searchParams.set("panel_id", "HyperDjangoPanel");

    try {
      const panelResponse = await window.fetch(url, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      if (!panelResponse.ok || sequence !== streamRefreshSequence) {
        return;
      }
      const data = await panelResponse.json();
      const currentToolbar = document.getElementById("djDebug");
      const panel = document.getElementById("HyperDjangoPanel");
      const content = panel && panel.querySelector(".djDebugPanelContent .djdt-scroll");
      if (!currentToolbar || !content || sequence !== streamRefreshSequence) {
        return;
      }
      currentToolbar.dataset.requestId = requestId;
      content.innerHTML = data.content;
      currentToolbar.dispatchEvent(
        new CustomEvent("djdt.panel.render", {
          detail: { panelId: "HyperDjangoPanel" },
        }),
      );
    } catch (error) {
      console.debug("HyperDjango panel refresh failed", error);
    }
  }

  window.addEventListener("hyper:afterRequest", (event) => {
    const response = event.detail && event.detail.response;
    if (!response || !response.headers) {
      return;
    }
    streamRefreshSequence += 1;
    const sequence = streamRefreshSequence;
    window.setTimeout(() => refreshHyperPanel(response, sequence), 250);
  });
})();
