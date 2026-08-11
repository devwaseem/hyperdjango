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

test("SwitchAction hands a non-retried command to a retryable watcher", async ({ page }) => {
  const requests = [];
  const switches = [];
  page.on("request", (request) => {
    const action = request.headers()["x-hyper-action"];
    if (["start_package_build", "watch_package_build"].includes(action)) {
      requests.push({ action, headers: request.headers(), method: request.method() });
    }
  });
  await page.evaluate(() => {
    window.__switchLoadingStates = [];
    window.addEventListener("hyper:actionSwitch", (event) => {
      window.__actionSwitch = event.detail;
      window.__switchLoadingStates.push({
        phase: "switch",
        disabled: document.querySelector('[hyper-loading-disable="package-build"]').disabled,
      });
    });
    window.addEventListener("hyper:beforeRequest", (event) => {
      if (event.detail.action === "watch_package_build") {
        window.__switchLoadingStates.push({
          phase: "destination",
          disabled: document.querySelector('[hyper-loading-disable="package-build"]').disabled,
        });
      }
    });
  });

  await page.getByRole("button", { name: "Build package" }).click();
  await expect(page.locator("[data-build-first]")).toHaveCount(1);
  await expect(page.locator("[data-build-resumed]")).toHaveText("Watcher resumed.", {
    timeout: 10_000,
  });
  await expect.poll(() => requests.length).toBe(3);
  switches.push(await page.evaluate(() => window.__actionSwitch));

  expect(requests.map((item) => item.action)).toEqual([
    "start_package_build",
    "watch_package_build",
    "watch_package_build",
  ]);
  expect(requests[0].method).toBe("POST");
  expect(requests[1].method).toBe("GET");
  expect(requests[0].headers["last-event-id"]).toBeUndefined();
  expect(requests[1].headers["last-event-id"]).toBeUndefined();
  expect(requests[2].headers["last-event-id"]).toMatch(/:1$/);
  expect(requests[0].headers["x-hyper-request-id"]).not.toBe(
    requests[1].headers["x-hyper-request-id"],
  );
  expect(requests[1].headers["x-hyper-request-id"]).toBe(
    requests[2].headers["x-hyper-request-id"],
  );
  expect(requests[1].headers["x-hyper-switch-depth"]).toBe("1");
  expect(await page.locator("[data-build-resumed]").getAttribute("data-mutation-count")).toBe("1");
  expect(switches[0]).toMatchObject({
    originalAction: "start_package_build",
    destinationAction: "watch_package_build",
    retry: true,
    depth: 1,
  });
  expect(await page.evaluate(() => window.__switchLoadingStates)).toEqual([
    { phase: "switch", disabled: true },
    { phase: "destination", disabled: true },
  ]);
  await expect(page.getByRole("button", { name: "Build package" })).toBeEnabled();
});

test("plain JavaScript action validates switches and starts a clean follow-up", async ({ page }) => {
  const headers = [];
  await page.route("**/__plain_switch", async (route) => {
    headers.push(route.request().headers());
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: 'event: switch_action\nid: command:1\ndata: {"name":"query","data":{"job_id":"7"},"method":"POST","url":"/__plain_switch_destination","retry":false}\n\n',
    });
  });
  await page.route("**/__plain_switch_destination", async (route) => {
    headers.push(route.request().headers());
    expect(route.request().method()).toBe("POST");
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: 'event: end\nid: query:1\ndata: {}\n\n',
    });
  });

  await page.evaluate(() => window.action("command", {}, {
    url: "/__plain_switch",
    method: "POST",
    retry: false,
    key: "plain-switch",
  }));

  expect(headers).toHaveLength(2);
  expect(headers[0]["x-hyper-request-id"]).not.toBe(headers[1]["x-hyper-request-id"]);
  expect(headers[1]["last-event-id"]).toBeUndefined();
  expect(JSON.parse(headers[1]["x-hyper-data"])).toEqual({ job_id: "7" });
});

test("an external replacement aborts the complete switched workflow", async ({ page }) => {
  await page.route("**/__abort_switch", async (route) => {
    const action = route.request().headers()["x-hyper-action"];
    if (action === "command") {
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: 'event: switch_action\ndata: {"name":"watch","method":"GET","retry":false}\n\n',
      });
      return;
    }
    if (action === "replacement") {
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: 'event: end\ndata: {}\n\n',
      });
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 2_000));
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: 'event: end\ndata: {}\n\n',
    });
  });

  const result = await page.evaluate(async () => {
    let destinationStarted;
    const started = new Promise((resolve) => { destinationStarted = resolve; });
    window.addEventListener("hyper:beforeRequest", (event) => {
      if (event.detail.action === "watch") destinationStarted();
    });
    const workflow = window.action("command", {}, {
      url: "/__abort_switch",
      retry: false,
      key: "replace-chain",
    });
    await started;
    const replacement = window.action("replacement", {}, {
      url: "/__abort_switch",
      retry: false,
      key: "replace-chain",
    });
    const [workflowResult] = await Promise.all([workflow, replacement]);
    return { aborted: workflowResult.aborted, blocked: workflowResult.blocked };
  });
  expect(result).toEqual({ aborted: true, blocked: false });
});

test("malformed switches and switch loops fail without retrying", async ({ page }) => {
  let malformedRequests = 0;
  await page.route("**/__malformed_switch", async (route) => {
    malformedRequests += 1;
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: 'event: switch_action\ndata: {"name":"","method":"DELETE"}\n\n',
    });
  });
  const malformed = await page.evaluate(() => window.action("bad", {}, {
    url: "/__malformed_switch",
    retry: true,
  }).then(() => "resolved", (error) => error.name));
  expect(malformed).toBe("SwitchActionError");
  expect(malformedRequests).toBe(1);

  let loopRequests = 0;
  await page.route("**/__switch_loop", async (route) => {
    loopRequests += 1;
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: 'event: switch_action\ndata: {"name":"loop","method":"GET","retry":false}\n\n',
    });
  });
  const loop = await page.evaluate(() => window.action("loop", {}, {
    url: "/__switch_loop",
    retry: false,
    key: "loop",
  }).then(() => "resolved", (error) => error.name));
  expect(loop).toBe("SwitchActionError");
  expect(loopRequests).toBe(5);
});
