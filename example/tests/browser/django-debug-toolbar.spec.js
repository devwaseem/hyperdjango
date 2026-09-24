import { expect, test } from "@playwright/test";

const toolbarBridgePath = "/static/hyperdjango/hyper-debug-toolbar.js";

async function loadToolbarBridge(page) {
  await page.addScriptTag({ url: toolbarBridgePath });
}

async function prepareToolbar(page, { visible, hidden = !visible }) {
  await page.goto("/runtime-fixtures/");
  await loadToolbarBridge(page);
  await page.evaluate(
    ({ visible: shouldBeVisible, hidden: initiallyHidden }) => {
      localStorage.setItem("djdt.show", String(shouldBeVisible));
      document.getElementById("djDebug")?.remove();
      const toolbar = document.createElement("div");
      toolbar.id = "djDebug";
      toolbar.hidden = initiallyHidden;
      document.body.append(toolbar);

      window.__showToolbarCalls = 0;
      window.djdt = {
        show_toolbar() {
          window.__showToolbarCalls += 1;
          document.getElementById("djDebug").hidden = false;
        },
      };
    },
    { visible, hidden },
  );
}

async function toolbarState(page) {
  return page.evaluate(() => ({
    hidden: document.getElementById("djDebug").hidden,
    showToolbarCalls: window.__showToolbarCalls,
  }));
}

test("disabled integration neither renders nor requests the toolbar bridge", async ({ page }) => {
  const bridgeRequests = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname === toolbarBridgePath) {
      bridgeRequests.push(request.url());
    }
  });

  await page.goto("/runtime-fixtures/");

  await expect(
    page.locator('script[src$="hyperdjango/hyper-debug-toolbar.js"]'),
  ).toHaveCount(0);
  expect(bridgeRequests).toEqual([]);
});

test("body append preserves an explicitly hidden Django Debug Toolbar", async ({ page }) => {
  await prepareToolbar(page, { visible: false });

  await page.evaluate(() => {
    window.dispatchEvent(
      new CustomEvent("hyper:settle:end", {
        detail: { target: "body", swap: "append" },
      }),
    );
  });

  expect(await toolbarState(page)).toEqual({
    hidden: true,
    showToolbarCalls: 0,
  });
});

test("body prepend leaves a visible Django Debug Toolbar visible", async ({ page }) => {
  await prepareToolbar(page, { visible: true });

  await page.evaluate(() => {
    window.dispatchEvent(
      new CustomEvent("hyper:settle:end", {
        detail: { target: document.body, swap: "prepend" },
      }),
    );
  });

  expect(await toolbarState(page)).toEqual({
    hidden: false,
    showToolbarCalls: 0,
  });
});

test("full body replacement preserves a previously hidden Django Debug Toolbar", async ({ page }) => {
  await prepareToolbar(page, { visible: false });

  await page.evaluate(() => {
    window.dispatchEvent(
      new CustomEvent("hyper:settle:end", {
        detail: { target: document.body, swap: "inner" },
      }),
    );
  });

  expect(await toolbarState(page)).toEqual({
    hidden: true,
    showToolbarCalls: 0,
  });
});

test("full body replacement restores a previously visible Django Debug Toolbar", async ({ page }) => {
  await prepareToolbar(page, { visible: true, hidden: true });

  await page.evaluate(() => {
    window.dispatchEvent(
      new CustomEvent("hyper:settle:end", {
        detail: { target: "body", swap: "inner" },
      }),
    );
  });

  expect(await toolbarState(page)).toEqual({
    hidden: false,
    showToolbarCalls: 1,
  });
});

test("streamed Hyper responses still refresh the HyperDjango panel", async ({ page }) => {
  await page.goto("/runtime-fixtures/");
  await loadToolbarBridge(page);
  await page.evaluate(() => {
    document.getElementById("djDebug")?.remove();
    const toolbar = document.createElement("div");
    toolbar.id = "djDebug";
    toolbar.dataset.renderPanelUrl = "/__debug__/render-panel/";
    toolbar.innerHTML = `
      <div id="HyperDjangoPanel">
        <div class="djDebugPanelContent">
          <div class="djdt-scroll">stale</div>
        </div>
      </div>
    `;
    document.body.append(toolbar);
    window.__panelRenderEvents = 0;
    toolbar.addEventListener("djdt.panel.render", () => {
      window.__panelRenderEvents += 1;
    });
    window.__panelFetch = null;
    window.fetch = async (input, init) => {
      window.__panelFetch = {
        url: String(input),
        requestedWith: init.headers["X-Requested-With"],
      };
      return {
        ok: true,
        async json() {
          return { content: "<strong>refreshed</strong>" };
        },
      };
    };

    const headers = new Headers({
      "content-type": "text/event-stream",
      "djdt-request-id": "request-123",
    });
    window.dispatchEvent(
      new CustomEvent("hyper:afterRequest", {
        detail: { response: { headers } },
      }),
    );
  });

  await expect
    .poll(() =>
      page.locator("#HyperDjangoPanel .djdt-scroll").innerHTML(),
    )
    .toBe("<strong>refreshed</strong>");
  expect(
    await page.evaluate(() => ({
      fetch: window.__panelFetch,
      requestId: document.getElementById("djDebug").dataset.requestId,
      renderEvents: window.__panelRenderEvents,
    })),
  ).toEqual({
    fetch: {
      url: "http://127.0.0.1:8765/__debug__/render-panel/?request_id=request-123&panel_id=HyperDjangoPanel",
      requestedWith: "XMLHttpRequest",
    },
    requestId: "request-123",
    renderEvents: 1,
  });
});
