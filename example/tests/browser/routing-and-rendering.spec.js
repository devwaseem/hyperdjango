import { expect, test } from "@playwright/test";
import { waitForAlpine } from "./helpers.js";

test("loads the base runtime, Vite assets, and configured view-transition names", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "HyperDjango file routing is live" })).toBeVisible();
  await expect.poll(() => page.evaluate(() => ({
    hyper: typeof window.Hyper?.action,
    alpine: typeof window.Alpine,
    morphdom: typeof window.morphdom,
  }))).toEqual({ hyper: "function", alpine: "object", morphdom: "function" });
  await expect(page.locator("h1")).toHaveCSS("view-transition-name", "page-header");
  await expect(page.locator("nav").first()).toHaveCSS("view-transition-name", "top-nav");
});

test("resolves static, group, nested-layout, and custom Django-view routes", async ({ page }) => {
  const routes = [
    ["/about", "h1", "About this example"],
    ["/pricing", "h1", "Pricing"],
    ["/dashboard", "h2", "Dashboard overview"],
    ["/dashboard/settings", "h2", "Settings"],
    ["/plain-django-view", "h1", "Plain Django View in file route"],
    ["/template-card", "h2", "Template Package Demo"],
  ];

  for (const [url, selector, text] of routes) {
    await page.goto(url);
    await expect(page.locator(selector)).toHaveText(text);
    if (url === "/plain-django-view") {
      await expect(page.locator("main")).toContainText("self.request is available: True");
    }
  }
});

test("passes dynamic, typed, composite, inline-regex, and catch-all route parameters to pages", async ({ page }) => {
  const routes = [
    ["/blog/browser-route", "Browser Route", "Dynamic slug: browser-route"],
    ["/typed/hello-world", "Typed Dynamic Segment", "slug = hello-world"],
    ["/account/reset/abc123-token456", "Password Reset From Key", "uidb36: abc123"],
    ["/regex/release-v42", "Composite Regex Segment", "kind: release"],
    ["/regex-inline/A1b2c3-reset-token-xyz", "Inline Regex Segment", "uidb36: A1b2c3"],
    ["/docs/getting-started/install", "Docs catch-all example", "Captured path: getting-started/install"],
  ];

  for (const [url, heading, evidence] of routes) {
    await page.goto(url);
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
    await expect(page.locator("main")).toContainText(evidence);
  }

  await expect(page.locator("main")).toContainText("getting-started");
  await expect(page.locator("main")).toContainText("install");
});

test("dynamic and nested-layout pages remain interactive after routing", async ({ page }) => {
  await page.goto("/blog/browser-route");
  await waitForAlpine(page);
  await page.getByRole("button", { name: "Bookmark" }).click();
  await expect(page.getByText("Saved:")).toHaveText("Saved: yes");

  await page.goto("/dashboard");
  await waitForAlpine(page);
  await page.getByRole("button", { name: "Pulse" }).click();
  await expect(page.getByText("Pulse count:").locator("..").getByRole("spinbutton")).toHaveValue("1");
});

test("exposes each documented example route from the home-page route inventory", async ({ page }) => {
  await page.goto("/");
  const hrefs = await page.locator("main h2:text('Route coverage') + ul a").evaluateAll(
    (links) => links.map((link) => link.getAttribute("href")),
  );

  expect(hrefs).toEqual([
    "/about",
    "/blog/hello-world",
    "/docs/getting-started/install",
    "/account/reset/abc123-token456",
    "/regex/release-v42",
    "/typed/hello-world",
    "/regex-inline/A1b2c3-reset-token-xyz",
    "/pricing",
    "/dashboard",
    "/dashboard/settings",
    "/todos",
    "/modal-demo",
    "/upload-progress",
    "/history-demo",
    "/sse-demo",
    "/async-handlers",
    "/error-demo",
    "/signals",
    "/template-card",
    "/plain-django-view",
    "/profile",
  ]);
});
