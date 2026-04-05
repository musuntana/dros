import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  reporter: "list",
  use: {
    acceptDownloads: true,
    baseURL: "http://127.0.0.1:3000",
    trace: "on-first-retry",
  },
  webServer: [
    {
      command: ".venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --log-level warning",
      cwd: "..",
      reuseExistingServer: true,
      timeout: 120000,
      url: "http://127.0.0.1:8000/healthz",
    },
    {
      command: "npm run dev -- --hostname 127.0.0.1 --port 3000",
      cwd: ".",
      env: {
        CONTROL_PLANE_BASE_URL: "http://127.0.0.1:8000",
        DROS_AUTH_ACTOR_ID: "00000000-0000-0000-0000-000000000902",
        DROS_AUTH_PROJECT_ROLE: "owner",
        DROS_AUTH_SCOPES:
          "projects:read,projects:write,members:write,datasets:read,datasets:write,workflows:read,workflows:write,artifacts:read,artifacts:write,assertions:read,assertions:write,evidence:read,evidence:write,manuscripts:read,manuscripts:write,reviews:read,reviews:write,exports:read,exports:write,uploads:write,events:read,downloads:read,audit:read",
        DROS_AUTH_TENANT_ID: "00000000-0000-0000-0000-000000000901",
        GATEWAY_BASE_URL: "http://127.0.0.1:8000",
        NEXT_PUBLIC_CONTROL_PLANE_BASE_URL: "http://127.0.0.1:8000",
        NEXT_PUBLIC_GATEWAY_BASE_URL: "http://127.0.0.1:8000",
      },
      reuseExistingServer: true,
      timeout: 120000,
      url: "http://127.0.0.1:3000/projects",
    },
  ],
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "mobile-chromium",
      use: { ...devices["Pixel 7"] },
    },
  ],
});
