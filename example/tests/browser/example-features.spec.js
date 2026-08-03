import { expect, test } from "@playwright/test";
import { waitForAlpine } from "./helpers.js";

test("todos support append, transitions, outer replacement, delete, and dependent partial updates", async ({ page }) => {
  await page.goto("/todos");
  await waitForAlpine(page);

  const input = page.locator("#todo-input");
  await input.fill("Browser todo");
  await page.getByRole("button", { name: "Add" }).click();
  const todo = page.locator("#todo-list li", { hasText: "Browser todo" });
  await expect(todo).toBeVisible();
  await expect(input).toHaveValue("");
  await expect(page.locator("#todo-stats")).toContainText("1 total");

  await todo.getByRole("checkbox").check();
  await expect(todo.getByRole("checkbox")).toBeChecked();
  await expect(page.locator("#todo-stats")).toContainText("1 completed");

  await todo.getByRole("button", { name: "Delete" }).click();
  await expect(todo).toHaveCount(0);
  await expect(page.locator("#todo-stats")).toContainText("0 total");
  await expect(page.locator("#todo-empty")).toContainText("No todos yet. Add one above.");
});

test("profile action form validates on the server, focuses the first invalid field, and saves valid data", async ({ page }) => {
  await page.goto("/profile");
  await waitForAlpine(page);

  await page.evaluate(() => window.action("save_profile", {}, {
    form: document.querySelector("#profile-panel form"),
    method: "POST",
    key: "profile-save",
  }));
  await expect(page.locator("#profile-panel")).toContainText("This field is required.");
  await expect(page.locator("#profile-panel input[name=email]")).toBeFocused();

  await page.locator("#profile-panel input[name=email]").fill("browser@example.com");
  await page.locator("#profile-panel input[name=name]").fill("Browser User");
  await page.locator("#profile-panel").getByRole("button", { name: "Save" }).click();
  await expect(page.locator("#profile-panel")).toContainText("Profile saved for Browser User.");
});

test("typeahead replaces stale requests, updates the URL, and scopes its loading indicator", async ({ page }) => {
  await page.goto("/search");
  await waitForAlpine(page);
  await page.evaluate(() => {
    window.__searchEvents = [];
    for (const name of ["hyper:requestReplaced", "hyper:requestAborted"]) {
      window.addEventListener(name, (event) => window.__searchEvents.push({ name, key: event.detail.key }));
    }
  });

  const search = page.getByPlaceholder("Search...");
  await search.fill("ja");
  await page.waitForTimeout(350);
  await search.fill("ali");
  await expect(page.getByText("Searching...")).toBeVisible();
  await expect(page.locator("#results")).toContainText("Alice", { timeout: 6_000 });
  await expect(page).toHaveURL(/\/search\?q=ali$/);
  await expect(page.getByText("Searching...")).toBeHidden();

  const events = await page.evaluate(() => window.__searchEvents);
  expect(events).toEqual(expect.arrayContaining([
    expect.objectContaining({ name: "hyper:requestReplaced", key: "live-search" }),
    expect.objectContaining({ name: "hyper:requestAborted", key: "live-search" }),
  ]));
});

test("signals update local and global Alpine state", async ({ page }) => {
  await page.goto("/signals");
  await waitForAlpine(page);
  await expect(page.getByText("Local count:")).toHaveText("Local count: 0");
  await expect(page.getByText("Global count:")).toHaveText("Global count: 0");

  await page.getByRole("button", { name: "Increment local + global" }).click();
  await expect(page.getByText("Local count:")).toHaveText("Local count: 1");
  await expect(page.getByText("Global count:")).toHaveText("Global count: 1");

  await page.getByRole("button", { name: "Reset global" }).click();
  await expect(page.getByText("Global count:")).toHaveText("Global count: 0");
});

test("a standalone partial loads its JavaScript module and manages focus", async ({ page }) => {
  await page.goto("/modal-demo");
  await waitForAlpine(page);

  await page.getByRole("button", { name: "Open modal partial" }).click();
  const modal = page.locator("[data-demo-modal-root]");
  await expect(modal).toBeVisible();
  await expect(modal.getByRole("button", { name: "Close modal" })).toBeFocused();

  await page.keyboard.press("Escape");
  await expect(modal).toHaveCount(0);
});

test("both Alpine and window.action upload paths send files and surface completion", async ({ page }) => {
  await page.goto("/upload-progress");
  await waitForAlpine(page);

  const alpine = page.locator("#upload-form-alpine input[type=file]");
  await alpine.setInputFiles({ name: "alpine.txt", mimeType: "text/plain", buffer: Buffer.from("alpine upload") });
  await page.getByRole("button", { name: "Upload with Alpine" }).click();
  await expect(page.locator("#upload-result-alpine")).toContainText("alpine.txt");
  await expect(page.locator("#upload-status-alpine")).toHaveText("Status: done | 100%");

  const windowUpload = page.locator("#window-upload-form input[type=file]");
  await windowUpload.setInputFiles({ name: "window.txt", mimeType: "text/plain", buffer: Buffer.from("window upload") });
  await page.getByRole("button", { name: "Upload with window.action" }).click();
  await expect(page.locator("#upload-result-window")).toContainText("window.txt");
  await expect(page.locator("#window-upload-status")).toHaveText("Status: done | 100%");
});

test("an async action streams incremental SSE updates through one request", async ({ page }) => {
  test.setTimeout(15_000);
  await page.goto("/sse-demo");
  await waitForAlpine(page);
  await page.evaluate(() => {
    window.__streamEvents = [];
    window.addEventListener("hyper:streamEvent", (event) => window.__streamEvents.push(event.detail.event));
  });

  await page.getByRole("button", { name: "Start SSE demo" }).click();
  await expect(page.locator("#stream-log")).toContainText("Step 1 finished. Progress is now 20%.", { timeout: 4_000 });
  await expect(page.locator("#stream-log")).toContainText("Step 5 finished. Progress is now 100%.", { timeout: 8_000 });
  await expect(page.getByText("Phase:")).toHaveText("Phase: Complete");
  await expect(page.getByText("Progress:")).toContainText("100%");

  const events = await page.evaluate(() => window.__streamEvents);
  expect(events).toContain("patch_signals");
  expect(events).toContain("patch_html");
  expect(events).toContain("toast");
});

test("action exceptions reach the browser request-error contract", async ({ page }) => {
  await page.goto("/error-demo");
  await waitForAlpine(page);
  await page.getByRole("button", { name: "Trigger 403 action" }).click();
  await expect(page.locator("#error-result")).toContainText("Forbidden action");
  await expect(page.locator("#error-result")).toContainText("Only staff can perform this action.");
});

test("async page handlers render GET and POST responses through normal browser form submission", async ({ page }) => {
  await page.goto("/async-handlers");
  await expect(page.getByText("Last handler method:")).toHaveText("Last handler method: GET");

  await page.getByRole("textbox", { name: "Name" }).fill("Async Browser");
  await page.getByRole("button", { name: "Save with async post()" }).click();
  await expect(page.getByText("Last handler method:")).toHaveText("Last handler method: POST");
  await expect(page.getByText("Saved value:")).toHaveText("Saved value: Async Browser");
});
