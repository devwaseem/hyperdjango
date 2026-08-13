import { expect, test } from "@playwright/test";

const host = (page) => page.locator("hyperdjango-debug-toolbar");
const toolbar = (page) => host(page).locator("#hd-debug-toolbar");
const consolePanel = (page) => toolbar(page).locator(".hdd-console");
const tracePanel = (page) => toolbar(page).locator("[data-slot='panel']");
const tabIds = {
  Overview: "overview",
  Route: "route",
  Action: "action",
  Output: "output",
  Timeline: "timeline",
  Database: "database",
  "Request / Response": "request",
  "Errors / Logs": "exceptions",
};

async function resetServer(request) {
  const history = await request.get("/__hyperdebug__/history/");
  if (history.ok() && (await history.json()).paused) {
    await request.post("/__hyperdebug__/controls/pause/");
  }
  await request.post("/__hyperdebug__/controls/clear/");
}

async function visit(page, path = "/", headers = {}) {
  await page.addInitScript(() => {
    localStorage.removeItem("hyperdjango.debug.open");
    localStorage.removeItem("hyperdjango.debug.tab");
    localStorage.removeItem("hyperdjango.debug.launcherX");
  });
  if (Object.keys(headers).length) await page.setExtraHTTPHeaders(headers);
  await page.goto(path, { waitUntil: "networkidle" });
  await expect(toolbar(page)).toHaveCSS("visibility", "visible");
  await expect(toolbar(page).locator(".hdd-launcher")).toBeVisible();
}

async function openToolbar(page) {
  const button = toolbar(page).getByRole("button", {
    name: /Open HyperDjango debug toolbar/,
  });
  if ((await button.getAttribute("aria-expanded")) !== "true") {
    await button.click();
  }
  await expect(consolePanel(page)).toHaveAttribute("aria-hidden", "false");
  await expect(toolbar(page)).toHaveClass(/is-open/);
}

async function activateTab(page, name) {
  const picker = toolbar(page).locator("[data-slot='tab-select']");
  if (await picker.isVisible()) {
    await picker.selectOption(tabIds[name]);
  } else {
    await toolbar(page).getByRole("tab", { name: new RegExp(`^${name}`) }).click();
  }
  await expect(tracePanel(page)).toHaveAttribute("aria-labelledby", `hdd-tab-${tabIds[name]}`);
}

async function latestHistory(page) {
  return page.evaluate(async () => {
    const response = await fetch("/__hyperdebug__/history/");
    return (await response.json()).records;
  });
}

async function selectTrace(page, predicate, timeout = 10_000) {
  await expect.poll(async () => (await latestHistory(page)).some(predicate), { timeout }).toBe(true);
  const record = (await latestHistory(page)).find(predicate);
  await page.evaluate((id) => window.__hyperdjangoDevtools.select(id), record.id);
  await expect(toolbar(page).locator("[data-slot='header-metrics']")).toContainText(record.id.slice(0, 8));
  return record;
}

test.describe.serial("HyperDjango request inspector", () => {
  test.beforeEach(async ({ request }) => {
    await resetServer(request);
  });

  test("loads independently and supports launcher, drawer, fullscreen, keyboard, and dragging", async ({ page }) => {
    await visit(page);
    await expect(page.getByText("v0.41.1 · Latest release")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Resume what matters" })).toBeVisible();
    await expect(page.getByRole("link", { name: /Open inspector guide/ })).toHaveAttribute("href", "/docs/dev-toolbar");
    const root = toolbar(page);
    await expect(root.locator("[data-slot='launcher-count']")).toHaveText("0");
    await expect(root.locator(".hdd-launcher-copy")).toContainText("HYPERDJANGO");

    await root.getByRole("button", { name: /Open HyperDjango debug toolbar/ }).click();
    await expect(root).toHaveClass(/is-open/);
    const dimensions = await consolePanel(page).evaluate((element) => ({
      height: element.getBoundingClientRect().height,
      viewportHeight: window.innerHeight,
      transition: getComputedStyle(element).transitionDuration,
    }));
    expect(dimensions.height / dimensions.viewportHeight).toBeCloseTo(0.5, 2);
    expect(dimensions.transition).toContain("0.24s");

    const fullscreen = root.locator("[data-slot='fullscreen']");
    await fullscreen.click();
    await expect(fullscreen).toHaveAttribute("aria-pressed", "true");
    await expect.poll(() => consolePanel(page).evaluate((el) => el.getBoundingClientRect().height)).toBeGreaterThan(710);
    await page.keyboard.press("Escape");
    await expect(fullscreen).toHaveAttribute("aria-pressed", "false");

    await root.getByRole("button", { name: "Close HyperDjango debug toolbar" }).click();
    await expect(root).not.toHaveClass(/is-open/);
    await expect.poll(() => consolePanel(page).evaluate((el) => getComputedStyle(el).transform)).not.toBe("none");

    const grip = root.getByRole("button", { name: /Move toolbar horizontally/ });
    await grip.focus();
    await page.keyboard.press("ArrowRight");
    await expect.poll(() => page.evaluate(() => localStorage.getItem("hyperdjango.debug.launcherX"))).toBe("32");
  });

  test("does not flash or move the document when refreshing an open toolbar", async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem("hyperdjango.debug.open", "true");
      localStorage.setItem("hyperdjango.debug.tab", "timeline");
      window.__toolbarVisibleBeforeDOMContentLoaded = false;
      window.__toolbarDrawerTransitionStarts = 0;
      window.__toolbarDOMContentLoaded = false;
      document.addEventListener("DOMContentLoaded", () => {
        window.__toolbarDOMContentLoaded = true;
      }, { once: true });
      const hostObserver = new MutationObserver(() => {
        const toolbarHost = document.querySelector("hyperdjango-debug-toolbar");
        if (!toolbarHost) return;
        const toolbarRoot = toolbarHost.shadowRoot?.querySelector("#hd-debug-toolbar");
        if (!toolbarRoot) return;
        toolbarRoot.querySelector(".hdd-console")?.addEventListener("transitionstart", (event) => {
          if (event.propertyName === "transform") window.__toolbarDrawerTransitionStarts += 1;
        });
        const recordVisibility = () => {
          if (
            !window.__toolbarDOMContentLoaded &&
            getComputedStyle(toolbarRoot).visibility === "visible" &&
            getComputedStyle(toolbarRoot).opacity !== "0"
          ) {
            window.__toolbarVisibleBeforeDOMContentLoaded = true;
          }
        };
        new MutationObserver(recordVisibility).observe(toolbarRoot, {
          attributes: true,
          attributeFilter: ["style"],
        });
        recordVisibility();
        hostObserver.disconnect();
      });
      hostObserver.observe(document, { childList: true, subtree: true });
    });
    await page.goto("/", { waitUntil: "networkidle" });
    await expect(toolbar(page)).toHaveCSS("visibility", "visible");
    await expect(toolbar(page)).toHaveClass(/is-open/);
    expect(await page.evaluate(() => window.__toolbarVisibleBeforeDOMContentLoaded)).toBe(false);
    expect(await page.evaluate(() => window.__toolbarDrawerTransitionStarts)).toBe(0);
    await expect(toolbar(page)).not.toHaveClass(/is-restoring/);
    await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);

    await page.reload({ waitUntil: "networkidle" });
    await expect(toolbar(page)).toHaveClass(/is-open/);
    expect(await page.evaluate(() => window.__toolbarDrawerTransitionStarts)).toBe(0);
    await expect(toolbar(page)).not.toHaveClass(/is-restoring/);
    await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);

    await page.evaluate(() => window.dispatchEvent(new PageTransitionEvent("pagehide")));
    await expect(toolbar(page)).toHaveCSS("visibility", "hidden");
    await expect(toolbar(page)).toHaveCSS("opacity", "0");
    await page.evaluate(() => window.dispatchEvent(new Event("pageshow")));
    await expect(toolbar(page)).toHaveCSS("visibility", "visible");
    await expect(toolbar(page)).toHaveCSS("opacity", "1");
  });

  test("keeps the collapsed launcher position across refreshes", async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.removeItem("hyperdjango.debug.open");
      localStorage.removeItem("hyperdjango.debug.launcherX");
    });
    await page.goto("/", { waitUntil: "networkidle" });
    await expect(toolbar(page)).toHaveCSS("visibility", "visible");

    const launcher = toolbar(page).locator(".hdd-launcher");
    const initial = await launcher.boundingBox();
    expect(initial).not.toBeNull();
    expect(initial.x).toBeCloseTo(8, 0);
    expect(initial.x + initial.width).toBeLessThanOrEqual(
      await page.evaluate(() => window.innerWidth),
    );

    for (let refresh = 0; refresh < 3; refresh += 1) {
      await page.reload({ waitUntil: "networkidle" });
      await expect(toolbar(page)).toHaveCSS("visibility", "visible");
      const current = await toolbar(page).locator(".hdd-launcher").boundingBox();
      expect(current.x).toBeCloseTo(initial.x, 0);
      expect(current.width).toBeCloseTo(initial.width, 0);
    }
  });

  test("navigates the focused views and exposes complete route, request, database, and copy data", async ({ page, context }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
    await context.addCookies([{
      name: "sessionid",
      value: "e2e-missing-session",
      url: "http://127.0.0.1:8765",
    }]);
    const headers = Object.fromEntries(
      Array.from({ length: 15 }, (_, index) => [`X-E2E-${index}`, `value-${index}`]),
    );
    await visit(page, "/?e2e=headers", headers);

    const llmsResponse = await page.request.get("/llms.txt");
    expect(llmsResponse.ok()).toBeTruthy();
    const llms = await llmsResponse.text();
    expect(llms).toContain("## Request Inspector");
    expect(llms).toContain("authoritative enablement switch");
    expect(llms).toContain("## Django Debug Toolbar");
    expect(llms).toContain("## Current Release: 0.41.1");
    for (const path of [
      "/docs/history",
      "/docs/cookbook",
      "/docs/reference/sse-payloads",
      "/docs/examples/example-app",
    ]) {
      expect((await page.request.get(path)).ok()).toBeTruthy();
    }

    await page.locator("#todo-list-demo input:not(:checked)").first().click();
    await selectTrace(page, (record) => record.action === "toggle_todo");
    await openToolbar(page);

    const tabs = toolbar(page).getByRole("tab");
    await expect(tabs).toHaveCount(8);
    await expect(tabs).toHaveText([
      "Overview",
      "Route",
      "Action",
      /Output\d*/,
      /Timeline\d+/,
      /Database\d*/,
      "Request / Response",
      "Errors / Logs",
    ]);
    await expect(tracePanel(page)).toContainText("Diagnostics");
    await expect(tracePanel(page)).toContainText("HEALTHY");

    await activateTab(page, "Route");
    await expect(tracePanel(page)).toContainText("routes/index");
    await expect(tracePanel(page)).not.toContainText("/Users/");
    await expect(tracePanel(page).getByRole("link", { name: /OPEN/ }).first()).toHaveAttribute("href", /^vscode:\/\/file/);

    await activateTab(page, "Request / Response");
    for (let index = 0; index < 15; index += 1) {
      await expect(tracePanel(page)).toContainText(`X-E2E-${index}`);
    }
    await expect(tracePanel(page)).not.toContainText(/more keys/i);

    await activateTab(page, "Overview");
    const copyPath = tracePanel(page).getByRole("button", { name: "Copy request path" }).first();
    await copyPath.click();
    await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe("/");

    await activateTab(page, "Database");
    await expect(tracePanel(page)).toContainText("Database queries");
    const disclosure = tracePanel(page).locator(".hdd-query-disclosure").first();
    await disclosure.locator("summary").click();
    await expect(disclosure).toHaveAttribute("open", "");
    const sqlCopy = disclosure.getByRole("button", { name: "Copy SQL", exact: true });
    await sqlCopy.click();
    await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toContain("django_session");

    await activateTab(page, "Errors / Logs");
    await expect(tracePanel(page)).toContainText("Exceptions");
    await expect(tracePanel(page)).toContainText("Request-scoped server logs");
  });

  test("captures a real Hyper action, rendered output, DOM changes, exact locate targets, copy, replay, and pin controls", async ({ page, context }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
    await visit(page);
    const checkbox = page.locator("#todo-list-demo input:not(:checked)").first();
    const todoId = await checkbox.evaluate((element) => element.closest("li").id);
    // The action replaces the checkbox itself. A plain click avoids `check()`
    // retrying against the next unchecked item after that replacement.
    await checkbox.click();
    const actionRecord = await selectTrace(page, (record) => record.action === "toggle_todo");
    await openToolbar(page);

    await expect(toolbar(page).locator("[data-slot='header-metrics']")).toContainText("toggle_todo");
    await activateTab(page, "Action");
    await expect(tracePanel(page)).toContainText("toggle_todo");
    await expect(tracePanel(page)).toContainText(todoId.replace("todo-", ""));

    await activateTab(page, "Output");
    await expect(tracePanel(page)).toContainText("Action results and SSE");
    await expect(tracePanel(page)).toContainText(`#${todoId}`);
    await expect(tracePanel(page)).toContainText("Template operations");
    await expect(tracePanel(page)).toContainText("ACTUAL DOM OUTCOME");
    await expect(toolbar(page).getByRole("tab", { name: "Rendering" })).toHaveCount(0);
    const diffColumns = await tracePanel(page).locator(".hdd-diff-grid").first().evaluate(
      (element) => getComputedStyle(element).gridTemplateColumns.split(" ").length,
    );
    expect(diffColumns).toBe(1);

    const copySelector = tracePanel(page).locator(`[data-action='copy'][data-copy-value='#${todoId}']`).first();
    await copySelector.click();
    await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe(`#${todoId}`);

    const locate = tracePanel(page).locator(`[data-action='highlight-dom'][data-dom-selector='#${todoId}']`).first();
    await locate.click();
    await expect(toolbar(page)).not.toHaveClass(/is-open/);
    const marker = page.locator("[data-hyperdjango-dom-highlight]");
    await expect(marker).toBeVisible();
    const [targetBox, markerBox] = await Promise.all([page.locator(`#${todoId}`).boundingBox(), marker.boundingBox()]);
    expect(markerBox.x).toBeLessThanOrEqual(targetBox.x);
    expect(markerBox.y).toBeLessThanOrEqual(targetBox.y);
    expect(markerBox.x + markerBox.width).toBeGreaterThanOrEqual(targetBox.x + targetBox.width);

    await openToolbar(page);
    const pin = toolbar(page).locator(`[data-pin-request-id='${actionRecord.id}']`);
    await pin.click();
    await expect(pin).toHaveClass(/is-active/);
    await page.evaluate(() => window.Hyper.action(
      "increment_signal_demo",
      { count: 0 },
      { method: "POST" },
    ));
    await selectTrace(page, (record) => record.action === "increment_signal_demo");
    await expect.poll(async () => (await latestHistory(page)).length).toBe(2);
    await page.reload({ waitUntil: "networkidle" });
    await expect.poll(async () => await latestHistory(page)).toEqual([
      expect.objectContaining({ id: actionRecord.id, pinned: true }),
    ]);
    await openToolbar(page);
    const unpin = toolbar(page).locator(`[data-pin-request-id='${actionRecord.id}']`);
    await expect(unpin).toBeVisible();
    await expect(unpin).toHaveClass(/is-active/);
    await unpin.click();

    await page.evaluate((id) => window.__hyperdjangoDevtools.select(id), actionRecord.id);
    await activateTab(page, "Action");
    page.once("dialog", async (dialog) => {
      expect(dialog.message()).toContain("mutating request");
      await dialog.accept();
    });
    await tracePanel(page).getByRole("button", { name: "REPLAY ACTION" }).click();
    await expect.poll(async () => (
      await latestHistory(page)
    ).filter((record) => record.action === "toggle_todo").length).toBeGreaterThan(1);
  });

  test("keeps the selected trace when a newer trace arrives", async ({ page }) => {
    await visit(page);
    await page.evaluate(() => window.Hyper.action(
      "increment_signal_demo",
      { count: 0 },
      { method: "POST" },
    ));
    const selected = await selectTrace(
      page,
      (record) => record.action === "increment_signal_demo",
    );
    await openToolbar(page);

    await page.evaluate(() => window.Hyper.action(
      "increment_signal_demo",
      { count: 1 },
      { method: "POST" },
    ));
    await expect.poll(async () => (
      await latestHistory(page)
    ).filter((record) => record.action === "increment_signal_demo").length).toBe(2);
    await expect(toolbar(page).locator(".hdd-history-entry")).toHaveCount(2);

    await expect(toolbar(page).locator("[data-slot='header-metrics']")).toContainText(
      selected.id.slice(0, 8),
    );
    await expect(
      toolbar(page).locator(`[data-request-id='${selected.id}']`),
    ).toHaveClass(/is-active/);
  });

  test("renders a captured HyperDjango exception with traceback details", async ({ page }) => {
    await visit(page);
    await page.evaluate(async () => {
      try {
        await window.Hyper.action("__e2e_missing_action__", {}, { method: "POST" });
      } catch {
        // The inspector should retain the failed request even though the caller handles it.
      }
    });
    await selectTrace(page, (record) => record.status >= 400 || record.exceptions > 0);
    await openToolbar(page);
    await activateTab(page, "Errors / Logs");
    await expect(tracePanel(page)).toContainText(/Exception 1/i);
    await expect(tracePanel(page)).toContainText(/missing|unknown|not found/i);
    await expect(tracePanel(page)).toContainText("Traceback frames");
  });

  test("refuses ambiguous DOM selectors instead of highlighting the wrong element", async ({ page }) => {
    await visit(page);
    await page.locator("#todo-list-demo input:not(:checked)").first().click();
    await selectTrace(page, (record) => record.action === "toggle_todo");
    await openToolbar(page);
    const id = (await latestHistory(page))[0].id;
    await page.evaluate(async (requestId) => {
      const duplicates = document.createElement("div");
      duplicates.innerHTML = '<span class="e2e-duplicate">A</span><span class="e2e-duplicate">B</span>';
      document.body.appendChild(duplicates);
      await fetch(`/__hyperdebug__/requests/${requestId}/client/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          events: [{
            kind: "DOM swap",
            target: ".e2e-duplicate",
            target_selector: ".e2e-duplicate",
            swap: "inner",
            target_existed_before: true,
            target_existed_after: true,
          }],
          summary: { swaps: 1 },
        }),
      });
      await window.__hyperdjangoDevtools.select(requestId);
    }, id);
    await activateTab(page, "Output");
    const locate = tracePanel(page).locator("[data-action='highlight-dom'][data-dom-selector='.e2e-duplicate']").first();
    await locate.click();
    await expect(locate).toHaveAttribute("aria-label", /2 DOM elements match/);
    await expect(toolbar(page)).toHaveClass(/is-open/);
    await expect(page.locator("[data-hyperdjango-dom-highlight]")).toHaveCount(0);
  });

  test("follows a live SSE trace through completion and shows content and pacing", async ({ page }) => {
    await visit(page);
    const composer = page.locator(".agent-chat-composer");
    await composer.locator("input").fill("E2E stream content");
    await composer.getByRole("button", { name: "Send" }).click();

    await expect(page.locator("#agent-thread-demo")).toContainText("E2E stream content");
    await selectTrace(
      page,
      (record) => record.action === "run_agent_stream" && record.stream_status === "completed",
      35_000,
    );
    await openToolbar(page);

    await activateTab(page, "Output");
    await expect(tracePanel(page)).toContainText(/completed/i);
    await expect(tracePanel(page)).not.toContainText(/SSE \/ PENDING/i);
    await expect(tracePanel(page)).toContainText("E2E stream content");
    await expect(tracePanel(page)).toContainText("append");

    await activateTab(page, "Timeline");
    await expect(tracePanel(page)).toContainText("Execution waterfall");
    await expect(tracePanel(page)).toContainText("SSE item waterfall");
    await expect(tracePanel(page)).toContainText(/time to first event/i);
    await expect(tracePanel(page)).toContainText(/stream iteration/i);
    await expect(tracePanel(page)).toContainText(/completed/i);
  });

  test("pause, filters, search, and clear controls update the request tape", async ({ page }) => {
    await visit(page);
    await openToolbar(page);
    const root = toolbar(page);
    const initialCount = Number(await root.locator("[data-slot='history-count']").textContent());

    const pause = root.locator("[data-action='pause']");
    await pause.click();
    await expect(pause).toHaveText("RESUME");
    await page.evaluate(() => fetch("/?paused-request=1"));
    await root.getByRole("button", { name: "Refresh request history" }).click();
    await expect(root.locator("[data-slot='history-count']")).toHaveText(String(initialCount));
    await pause.click();
    await expect(pause).toHaveText("PAUSE");

    await root.locator("[data-slot='filter']").selectOption("action");
    await expect(root.locator(".hdd-history-entry")).toHaveCount(0);
    await root.locator("[data-slot='filter']").selectOption("all");
    await root.locator("[data-slot='search']").fill("does-not-match");
    await expect(root.locator("[data-slot='history']")).toContainText("NO REQUESTS MATCH");
    await root.locator("[data-slot='search']").fill("");

    await root.getByRole("button", { name: "CLEAR" }).click();
    await expect(root.locator("[data-slot='history-count']")).toHaveText("0");
    await expect(tracePanel(page)).toContainText("SELECT A REQUEST");
  });

  test("uses a compact picker and bounded, scrollable content on portrait and landscape screens", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await visit(page);
    await page.evaluate(() => window.Hyper.action(
      "increment_signal_demo",
      { count: 0 },
      { method: "POST" },
    ));
    await selectTrace(page, (record) => record.action === "increment_signal_demo");
    await openToolbar(page);

    const picker = toolbar(page).locator("[data-slot='tab-select']");
    await expect(picker).toBeVisible();
    await expect(toolbar(page).locator("[data-slot='tabs']")).toBeHidden();
    await picker.selectOption("route");
    await expect(tracePanel(page)).toContainText("Selected request dispatch");

    const portrait = await consolePanel(page).evaluate((element) => ({
      height: element.getBoundingClientRect().height,
      width: element.getBoundingClientRect().width,
      viewport: [window.innerWidth, window.innerHeight],
      scrollWidth: element.scrollWidth,
      historyHeight: element.querySelector(".hdd-history").getBoundingClientRect().height,
    }));
    expect(portrait.height / portrait.viewport[1]).toBeGreaterThan(0.75);
    expect(portrait.height / portrait.viewport[1]).toBeLessThan(0.8);
    expect(portrait.width).toBe(portrait.viewport[0]);
    expect(portrait.scrollWidth).toBeLessThanOrEqual(portrait.viewport[0]);
    expect(portrait.historyHeight).toBeLessThan(150);

    await page.setViewportSize({ width: 844, height: 390 });
    const landscapeHeight = await consolePanel(page).evaluate(
      (element) => element.getBoundingClientRect().height / window.innerHeight,
    );
    expect(landscapeHeight).toBeGreaterThan(0.82);
    expect(landscapeHeight).toBeLessThan(0.88);
  });
});
