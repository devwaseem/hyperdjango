import { expect, test } from "@playwright/test";
import { waitForAlpine } from "./helpers.js";

test.beforeEach(async ({ page }) => {
  await page.goto("/sse-demo");
  await waitForAlpine(page);
});

test("an interrupted SSE action reconnects and resumes after the last event", async ({ page }) => {
  const requests = [];
  page.on("request", (request) => {
    if (request.headers()["x-hyper-action"] === "retry_demo") {
      requests.push(request.headers());
    }
  });

  await page.evaluate(() => {
    window.__sseRetries = [];
    window.addEventListener("hyper:requestRetry", (event) => {
      window.__sseRetries.push(event.detail);
    });
    window.action("retry_demo", {}, { key: "retry-e2e" });
  });

  await expect(page.locator("[data-retry-first]")).toHaveCount(1);
  await expect(page.locator("[data-retry-resumed]")).toHaveText("Stream resumed.", {
    timeout: 10_000,
  });
  await expect.poll(() => requests.length).toBe(2);

  expect(requests[0]["last-event-id"]).toBeUndefined();
  expect(requests[1]["last-event-id"]).toMatch(/:1$/);
  expect(await page.evaluate(() => window.__sseRetries.length)).toBe(1);
});

test("retry false opts out of automatic SSE reconnects", async ({ page }) => {
  let requestCount = 0;
  page.on("request", (request) => {
    if (request.headers()["x-hyper-action"] === "retry_demo") {
      requestCount += 1;
    }
  });

  await page.evaluate(() => {
    window.__sseRetries = [];
    window.__retryOptOutResult = "pending";
    window.addEventListener("hyper:requestRetry", () => window.__sseRetries.push(true));
    window.action("retry_demo", {}, { key: "retry-opt-out-e2e", retry: false })
      .then(() => { window.__retryOptOutResult = "resolved"; })
      .catch(() => { window.__retryOptOutResult = "rejected"; });
  });

  await expect(page.locator("[data-retry-first]")).toHaveCount(1);
  await expect.poll(() => page.evaluate(() => window.__retryOptOutResult)).toBe("rejected");
  await page.waitForTimeout(1_200);

  expect(requestCount).toBe(1);
  expect(await page.evaluate(() => window.__sseRetries)).toEqual([]);
  await expect(page.locator("[data-retry-resumed]")).toHaveCount(0);
});

test("SSE actions accept CRLF-framed events", async ({ page }) => {
  await page.route("**/__sse_crlf_fixture", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: [
        "event: patch_html\r\n",
        "id: crlf-fixture:1\r\n",
        'data: {"content":"<div data-crlf-event>CRLF event parsed.</div>","target":"#stream-log","swap":"inner"}\r\n',
        "\r\n",
        "event: end\r\n",
        "id: crlf-fixture:2\r\n",
        "data: {}\r\n",
        "\r\n",
      ].join(""),
    });
  });

  await page.evaluate(() => window.action("crlf_fixture", {}, {
    url: "/__sse_crlf_fixture",
    key: "crlf-e2e",
  }));

  await expect(page.locator("[data-crlf-event]")).toHaveText("CRLF event parsed.");
});
