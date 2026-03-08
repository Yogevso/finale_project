import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.BASE_URL || 'http://127.0.0.1:3100';
process.env.BASE_URL = baseURL;
const backendUrl = process.env.E2E_BACKEND_URL || 'http://127.0.0.1:8010';
const isWindows = process.platform === 'win32';
const skipWebServer = process.env.PW_SKIP_WEBSERVER === '1';
const backendCommand = isWindows
  ? 'cmd /c "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\\scripts\\start_e2e_backend.ps1"'
  : 'node ./scripts/start-e2e-backend.mjs';
const backendCwd = isWindows ? '../backend' : '.';
const frontendCommand = isWindows
  ? 'cmd /c npm run dev -- --host 127.0.0.1 --port 3100'
  : 'npm run dev -- --host 127.0.0.1 --port 3100';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false, // Run tests sequentially for stability
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [
    ['html', { open: 'never' }],
    ['list']
  ],
  timeout: 30000,
  expect: {
    timeout: 10000,
  },
  use: {
    baseURL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: skipWebServer
    ? undefined
    : [
        {
          command: backendCommand,
          url: `${backendUrl}/health`,
          reuseExistingServer: false,
          timeout: 180000,
          cwd: backendCwd,
        },
        {
          command: frontendCommand,
          url: `${baseURL}/login`,
          reuseExistingServer: false,
          timeout: 180000,
          env: {
            ...process.env,
            VITE_API_PROXY_TARGET: backendUrl,
          },
        },
      ],
});
