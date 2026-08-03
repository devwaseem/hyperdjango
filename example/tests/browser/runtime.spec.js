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

test("restores server-rendered state after browser history navigation", async ({ page }) => {
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

  await page.goBack();
  await expect(page).toHaveURL(/\/history-demo\/\?step=alpha$/);
  await expect(state).toHaveAttribute("data-step", "alpha");
  await expect(page.locator("#history-script-status")).toHaveText("Body script ran 2 time(s).");
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
