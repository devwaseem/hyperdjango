import { expect } from "@playwright/test";

export async function waitForAlpine(page) {
  await expect
    .poll(
      () => page.evaluate(() => {
        const root = document.querySelector("[x-data]");
        return Boolean(window.Alpine && (!root || root._x_dataStack));
      }),
      { timeout: 20_000 },
    )
    .toBe(true);
}
