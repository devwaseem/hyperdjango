import { defineConfig } from "@playwright/test";

const djangoPort = 8000;
const vitePort = 5174;
const viteDevUrl = `http://127.0.0.1:${vitePort}/`;

export default defineConfig({
  testDir: "./tests/browser",
  // The development Vite server lazily transforms the example entries. Running
  // every fresh browser context at once can make startup itself flaky, so keep
  // this library-contract suite deterministic in local runs and CI.
  fullyParallel: false,
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: `http://127.0.0.1:${djangoPort}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${vitePort} --strictPort`,
      port: vitePort,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: `../.venv/bin/python manage.py runserver 127.0.0.1:${djangoPort} --noreload`,
      env: { HYPER_VITE_DEV_SERVER_URL: viteDevUrl },
      port: djangoPort,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
