import { expect, test } from "@playwright/test";

test("website demonstrates a command-to-query SwitchAction handoff", async ({ page }) => {
  const requests = [];
  await page.addInitScript(() => {
    window.__switchDemoLifecycle = [];
    window.addEventListener("hyper:actionSwitch", (event) => {
      if (event.detail.destinationAction !== "watch_switch_build") return;
      window.__switchDemoLifecycle.push({
        phase: "switch",
        disabled: document.querySelector(
          '[hyper-loading-disable="switch-action-demo"]',
        )?.disabled,
        detail: event.detail,
      });
    });
    window.addEventListener("hyper:beforeRequest", (event) => {
      if (event.detail.action !== "watch_switch_build") return;
      window.__switchDemoLifecycle.push({
        phase: "watcher",
        disabled: document.querySelector(
          '[hyper-loading-disable="switch-action-demo"]',
        )?.disabled,
      });
    });
  });
  page.on("request", (request) => {
    const action = request.headers()["x-hyper-action"];
    if (["start_switch_build", "watch_switch_build"].includes(action)) {
      requests.push({
        action,
        method: request.method(),
        requestId: request.headers()["x-hyper-request-id"],
        lastEventId: request.headers()["last-event-id"],
        switchDepth: request.headers()["x-hyper-switch-depth"],
      });
    }
  });

  await page.goto("/", { waitUntil: "networkidle" });
  const demo = page.locator("[data-switch-action-demo]");
  const button = demo.getByRole("button", { name: "Build package" });

  await button.click();
  await expect(button).toBeDisabled();
  await expect(demo.locator("[data-switch-phase]")).toHaveText("Build complete", {
    timeout: 10_000,
  });
  await expect(button).toBeEnabled();
  await expect(demo.locator("[data-switch-reconnect]")).toHaveText("reconnected");
  await expect(demo.locator("[data-switch-mutations]")).toHaveText("1");
  await expect.poll(() => requests.length).toBe(3);

  expect(requests.map(({ action }) => action)).toEqual([
    "start_switch_build",
    "watch_switch_build",
    "watch_switch_build",
  ]);
  expect(requests.map(({ method }) => method)).toEqual(["POST", "GET", "GET"]);
  expect(requests[0].requestId).not.toBe(requests[1].requestId);
  expect(requests[1].requestId).toBe(requests[2].requestId);
  expect(requests[0].lastEventId).toBeUndefined();
  expect(requests[1].lastEventId).toBeUndefined();
  expect(requests[2].lastEventId).toMatch(/:checkpoint:connected$/);
  expect(requests[0].switchDepth).toBeUndefined();
  expect(requests[1].switchDepth).toBe("1");
  expect(requests[2].switchDepth).toBe("1");
  const lifecycle = await page.evaluate(() => window.__switchDemoLifecycle);
  expect(lifecycle.map(({ phase, disabled }) => ({ phase, disabled }))).toEqual([
    { phase: "switch", disabled: true },
    { phase: "watcher", disabled: true },
  ]);
  expect(lifecycle[0].detail).toMatchObject({
    originalAction: "start_switch_build",
    destinationAction: "watch_switch_build",
    originalRequestId: requests[0].requestId,
    newRequestId: requests[1].requestId,
    method: "GET",
    retry: true,
    depth: 1,
  });
  await expect(demo.locator("[data-switch-original-id]")).not.toHaveText("—");
  await expect(demo.locator("[data-switch-destination-id]")).not.toHaveText("—");
  await expect(demo.locator("[data-switch-original-id]")).not.toHaveText(
    await demo.locator("[data-switch-destination-id]").innerText(),
  );
});
