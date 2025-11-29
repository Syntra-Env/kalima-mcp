import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: 'tests/e2e',
  timeout: 60_000,
  retries: 0,
  use: {
    baseURL: 'http://127.0.0.1:4173',
    trace: 'on-first-retry',
  },
  webServer: {
    command: 'npx http-server desktop/web -p 4173 -c-1',
    port: 4173,
    reuseExistingServer: true,
    timeout: 30_000,
  },
});
