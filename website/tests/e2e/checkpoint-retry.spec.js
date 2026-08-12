import { expect, test } from "@playwright/test";

test("website demonstrates a GET resuming from a named checkpoint", async ({ page }) => {
  const requests = [];
  page.on("request", (request) => {
    if (request.headers()["x-hyper-action"] !== "stream_checkpoint_report") {
      return;
    }
    requests.push({
      method: request.method(),
      requestId: request.headers()["x-hyper-request-id"],
      lastEventId: request.headers()["last-event-id"],
    });
  });

  await page.goto("/", { waitUntil: "networkidle" });
  const demo = page.locator("[data-checkpoint-retry-demo]");
  const button = demo.getByRole("button", { name: "Run interrupted stream" });

  await button.click();
  await expect(demo.locator('[data-checkpoint-stage="complete"]')).toBeVisible();
  await expect(button).toBeEnabled();

  await expect(demo.locator('[data-checkpoint-stage="catalog"]')).toHaveCount(1);
  await expect(demo.locator('[data-checkpoint-stage="pricing"]')).toHaveCount(1);
  await expect(demo.locator('[data-checkpoint-stage="complete"]')).toHaveCount(1);
  await expect.poll(() => requests.length).toBe(2);

  expect(requests.map(({ method }) => method)).toEqual(["GET", "GET"]);
  expect(requests[0].requestId).toBe(requests[1].requestId);
  expect(requests[0].lastEventId).toBeUndefined();
  expect(requests[1].lastEventId).toMatch(
    /:checkpoint:catalog-loaded$/,
  );
});
