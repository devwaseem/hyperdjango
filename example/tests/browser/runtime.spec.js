import { expect, test } from "@playwright/test";
import { waitForAlpine } from "./helpers.js";

test("applies an action signal through the Alpine bridge", async ({ page }) => {
  await page.goto("/");
  await waitForAlpine(page);

  await expect(page.getByText("Live value:")).toHaveText("Live value: 0");
  await page.getByRole("button", { name: "Increment" }).click();
  await expect(page.getByText("Live value:")).toHaveText("Live value: 1");
});

test("swaps server-rendered partials after an action", async ({ page }) => {
  await page.goto("/");
  await waitForAlpine(page);

  await page.getByRole("button", { name: "Edit" }).click();
  const textInput = page.getByRole("textbox", { name: "Text" });
  await expect(textInput).toBeVisible();
  await textInput.fill("Saved from a browser test.");
  await page.getByRole("button", { name: "Save" }).click();

  await expect(page.locator("main")).toContainText("Saved from a browser test.");
  await expect(page.getByText("Saved.")).toBeVisible();
});

test("restores fresh server-rendered state with morphs after Back and Forward", async ({ page }) => {
  await page.goto("/history-demo/");
  await waitForAlpine(page);

  const state = page.locator("#history-state");
  await expect(state).toHaveAttribute("data-step", "home");
  await expect(page.locator("#history-script-status")).toHaveText("Body script ran 1 time(s).");

  await page.getByRole("button", { name: "Push alpha" }).click();
  await expect(page).toHaveURL(/\/history-demo\/\?step=alpha$/);
  await expect(state).toHaveAttribute("data-step", "alpha");

  await page.getByRole("button", { name: "Push beta" }).click();
  await expect(page).toHaveURL(/\/history-demo\/\?step=beta$/);
  await expect(state).toHaveAttribute("data-step", "beta");

  await page.evaluate(() => {
    window.__historyFetches = [];
    window.__historyStateNode = document.querySelector("#history-state");
    const originalFetch = window.fetch.bind(window);
    window.fetch = (input, init = {}) => {
      const url = new URL(typeof input === "string" ? input : input.url, window.location.href);
      if (url.pathname === "/history-demo/" && !init.headers?.["X-Hyper-Action"]) {
        window.__historyFetches.push({ url: `${url.pathname}${url.search}`, cache: init.cache });
      }
      return originalFetch(input, init);
    };
  });

  await page.goBack();
  await expect(page).toHaveURL(/\/history-demo\/\?step=alpha$/);
  await expect(state).toHaveAttribute("data-step", "alpha");
  await expect(page.locator("#history-script-status")).toHaveText("Body script ran 2 time(s).");
  await expect.poll(() => page.evaluate(() => window.__historyFetches)).toEqual([
    { url: "/history-demo/?step=alpha", cache: "no-store" },
  ]);
  await expect.poll(() => page.evaluate(
    () => window.__historyStateNode === document.querySelector("#history-state"),
  )).toBe(true);

  await page.evaluate(() => {
    window.__historyFetches = [];
  });
  await page.goForward();
  await expect(page).toHaveURL(/\/history-demo\/\?step=beta$/);
  await expect(state).toHaveAttribute("data-step", "beta");
  await expect(page.locator("#history-script-status")).toHaveText("Body script ran 3 time(s).");
  await expect.poll(() => page.evaluate(() => window.__historyFetches)).toEqual([
    { url: "/history-demo/?step=beta", cache: "no-store" },
  ]);
  await expect.poll(() => page.evaluate(
    () => window.__historyStateNode === document.querySelector("#history-state"),
  )).toBe(true);
});

test("keeps a named transition target in place across repeated inner swaps", async ({ page }) => {
  await page.goto("/");
  await waitForAlpine(page);

  const tip = page.locator("#tip-card");
  await expect(tip).toContainText("Tip 1");
  await page.getByRole("button", { name: "Next tip" }).click();
  await expect(tip).toContainText("Tip 2");
  await page.getByRole("button", { name: "Next tip" }).click();
  await expect(tip).toContainText("Tip 3");
});
