import { expect, test } from "@playwright/test";
import { waitForAlpine } from "./helpers.js";

async function captureRuntimeEvents(page, names) {
  await page.evaluate((eventNames) => {
    window.__hyperRuntimeEvents = [];
    for (const name of eventNames) {
      window.addEventListener(name, (event) => {
        window.__hyperRuntimeEvents.push({
          name,
          action: event.detail?.action ?? null,
          key: event.detail?.key ?? null,
          status: event.detail?.status ?? null,
          detail: event.detail ?? null,
        });
      });
    }
  }, names);
}

test("applies every typed action item through one Actions response", async ({ page }) => {
  await page.goto("/runtime-fixtures/");
  await waitForAlpine(page);
  await captureRuntimeEvents(page, ["hyper:toast"]);
  await page.evaluate(() => {
    window.__fixtureEvent = null;
    document.querySelector("#event-target").addEventListener("runtime-fixture:event", (event) => {
      window.__fixtureEvent = event.detail;
    });
  });

  await page.getByRole("button", { name: "Apply typed items" }).click();

  await expect(page).toHaveURL(/\/runtime-fixtures\/\?state=updated$/);
  await expect(page.locator("#append-target")).toHaveText("prependedexistingappended");
  await expect(page.locator("#swap-neighbors")).toHaveText("beforemarkerafter");
  await expect(page.locator("#outer-target")).toHaveText("outer replacement");
  await expect(page.locator("#inner-target")).toHaveText("inner replacement");
  await expect(page.locator("#none-target")).toHaveText("none original");
  await expect(page.locator("[data-fixture=ignored]")).toHaveCount(0);
  await expect(page.locator("#delete-target")).toHaveCount(0);
  await expect.poll(() => page.evaluate(() => window.__fixtureEvent)).toEqual({ message: "delivered" });

  const events = await page.evaluate(() => window.__hyperRuntimeEvents);
  expect(events).toContainEqual(expect.objectContaining({
    name: "hyper:toast",
    detail: { type: "success", title: "Fixture complete", message: "Every typed action item was applied." },
  }));
});

test("patches local and global Alpine signals and honors explicit focus and lifecycle delays", async ({ page }) => {
  await page.goto("/runtime-fixtures/");
  await waitForAlpine(page);
  await captureRuntimeEvents(page, ["hyper:swap:start", "hyper:swap:end", "hyper:settle:end", "hyper:transition:start", "hyper:transition:end"]);

  await page.getByRole("button", { name: "Patch signals" }).click();
  await expect(page.locator("#fixture-local")).toHaveText("1");
  await expect(page.locator("#fixture-message")).toHaveText("patched");
  await expect(page.locator("#fixture-global")).toHaveText("global");

  await page.getByRole("button", { name: "Swap and focus" }).click();
  await expect(page.locator("#fixture-focused")).toBeFocused();

  const events = await page.evaluate(() => window.__hyperRuntimeEvents);
  expect(events).toEqual(expect.arrayContaining([
    expect.objectContaining({ name: "hyper:swap:start", action: "focus_after_swap" }),
    expect.objectContaining({ name: "hyper:swap:end", action: "focus_after_swap" }),
    expect.objectContaining({ name: "hyper:settle:end", action: "focus_after_swap" }),
  ]));
});

test("scopes loading and disable state by form action, key, target, and delay", async ({ page }) => {
  await page.goto("/runtime-fixtures/");
  await waitForAlpine(page);
  await captureRuntimeEvents(page, [
    "hyper:form:beforeSubmit",
    "hyper:form:success",
    "hyper:beforeRequest",
    "hyper:requestSuccess",
    "hyper:afterRequest",
    "hyper:request:start",
    "hyper:request:end",
  ]);

  const hiddenIndicators = [
    "#loading-global",
    "#loading-key",
    "#loading-key-attribute",
    "#loading-action",
    "#loading-delayed",
  ];
  for (const selector of hiddenIndicators) {
    await expect(page.locator(selector)).toBeHidden();
  }

  await page.getByRole("button", { name: "Start loading fixture" }).click();

  await expect(page.locator("html")).toHaveAttribute("aria-busy", "true");
  await expect(page.locator("body")).toHaveAttribute("aria-busy", "true");
  await expect(page.locator("#loading-delayed")).toBeVisible();
  for (const selector of hiddenIndicators.slice(0, 4)) {
    await expect(page.locator(selector)).toBeVisible();
  }
  await expect(page.locator("#loading-class")).toHaveClass(/is-busy/);
  await expect(page.locator("#loading-remove-class")).not.toHaveClass(/is-hidden/);
  await expect(page.locator("#loading-submit")).toBeDisabled();
  await expect(page.locator("#loading-secondary")).toBeDisabled();
  await expect(page.locator("#loading-disable-key")).toBeDisabled();
  await expect(page.locator("#loading-disable-raw")).toBeDisabled();
  await expect(page.locator("#loading-target-busy")).toHaveAttribute("aria-busy", "true");

  await expect(page.locator("#loading-result")).toHaveText("finished");
  await expect(page.locator("html")).not.toHaveAttribute("aria-busy", "true");
  for (const selector of hiddenIndicators) {
    await expect(page.locator(selector)).toBeHidden();
  }
  await expect(page.locator("#loading-class")).not.toHaveClass(/is-busy/);
  await expect(page.locator("#loading-remove-class")).toHaveClass(/is-hidden/);
  await expect(page.locator("#loading-submit")).toBeEnabled();
  await expect(page.locator("#loading-secondary")).toBeEnabled();
  await expect(page.locator("#loading-disable-key")).toBeEnabled();
  await expect(page.locator("#loading-disable-raw")).toBeEnabled();
  await expect(page.locator("#loading-target-busy")).not.toHaveAttribute("aria-busy", "true");

  const events = await page.evaluate(() => window.__hyperRuntimeEvents);
  expect(events).toEqual(expect.arrayContaining([
    expect.objectContaining({ name: "hyper:form:beforeSubmit", action: "slow_loading", key: "loading-fixture" }),
    expect.objectContaining({ name: "hyper:form:success", action: "slow_loading", key: "loading-fixture" }),
    expect.objectContaining({ name: "hyper:beforeRequest", action: "slow_loading" }),
    expect.objectContaining({ name: "hyper:requestSuccess", action: "slow_loading", status: 200 }),
    expect.objectContaining({ name: "hyper:afterRequest", action: "slow_loading", key: "loading-fixture", status: 200 }),
  ]));
});

test("uses Alpine options, preserves concurrent sync:none calls, and rejects strict missing targets", async ({ page }) => {
  await page.goto("/runtime-fixtures/");
  await waitForAlpine(page);
  await page.evaluate(() => {
    window.__optionRequest = null;
    window.__blockedRequests = 0;
    window.addEventListener("hyper:beforeRequest", (event) => {
      if (event.detail.action === "alpine_options") {
        window.__optionRequest = { method: event.detail.method, url: event.detail.url };
      }
    });
    window.addEventListener("hyper:requestBlocked", (event) => {
      if (event.detail.key === "block-fixture") {
        window.__blockedRequests += 1;
      }
    });
  });

  await page.getByRole("button", { name: "Run Alpine action options" }).click();
  await expect(page.locator("#before-submit-result")).toHaveText("called");
  await expect(page.locator("[data-fixture=alpine-options]")).toHaveText("from-alpine");
  await expect.poll(() => page.evaluate(() => window.__optionRequest)).toEqual({
    method: "POST",
    url: "/runtime-fixtures/",
  });

  await page.getByRole("button", { name: "Run blocked action" }).click();
  await page.getByRole("button", { name: "Run blocked action" }).click();
  await expect.poll(() => page.evaluate(() => window.__blockedRequests)).toBe(1);
  await expect(page.locator("#loading-result")).toHaveText("finished");

  await page.getByRole("button", { name: "Concurrent one" }).click();
  await page.getByRole("button", { name: "Concurrent two" }).click();
  await expect(page.locator("[data-fixture=concurrent]")).toHaveText(["one", "two"]);

  await page.getByRole("button", { name: "Trigger strict missing target" }).click();
  await expect(page.locator("#strict-result")).toHaveText("Hyper target not found: #fixture-target-does-not-exist");
});

test("performs Redirect and declarative link/form navigation without a document reload", async ({ page }) => {
  await page.goto("/runtime-fixtures/");
  await waitForAlpine(page);

  await page.getByRole("button", { name: "Redirect" }).click();
  await expect(page).toHaveURL(/\/runtime-fixtures\/\?redirected=1$/);
  await expect(page.locator("#fixture-redirected")).toHaveText("Redirected successfully.");

  await page.goto("/runtime-fixtures/");
  await waitForAlpine(page);
  await page.locator("#fixture-hyper-nav").click();
  await expect(page).toHaveURL(/\/about$/);
  await expect(page.getByRole("heading", { name: "About this example" })).toBeVisible();

  await page.goBack();
  await expect(page.getByRole("heading", { name: "Runtime browser fixtures" })).toBeVisible();
  await page.getByRole("button", { name: "Navigate form via hyper-nav" }).click();
  await expect(page).toHaveURL(/\/about\?from=fixture$/);
  await expect(page.getByRole("heading", { name: "About this example" })).toBeVisible();
});
