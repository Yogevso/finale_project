import { defineConfig, devices } from '@playwright/test';

// Allow running on either port 3000 or 3001
const baseURL = process.env.BASE_URL || 'http://localhost:3000';

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
  // WebServer config disabled - servers must be started manually before running tests
  // webServer: [
  //   {
  //     command: 'cd ../backend && .\\venv\\Scripts\\Activate.ps1 && python -m uvicorn app.main:app --port 8000',
  //     url: 'http://localhost:8000/health',
  //     reuseExistingServer: true,
  //     timeout: 120000,
  //   },
  //   {
  //     command: 'npm run dev',
  //     url: 'http://localhost:3000',
  //     reuseExistingServer: true,
  //     timeout: 120000,
  //   },
  // ],
});
