import { defineConfig } from '@playwright/test';

const npxCmd = process.platform === 'win32' ? 'npx.cmd' : 'npx';

export default defineConfig({
  testDir: 'tests/e2e',
  timeout: 60_000,
  retries: 0,
  use: {
    baseURL: 'http://127.0.0.1:4173',
    trace: 'on-first-retry',
  },
  webServer: {
    command: `${npxCmd} http-server desktop/frontend -p 4173 -c-1 -P http://127.0.0.1:8080`,
    port: 4173,
    reuseExistingServer: true,
    timeout: 60_000,
  },
});
