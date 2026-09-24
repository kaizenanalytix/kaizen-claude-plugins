// Copy into the frontend repo's root as playwright.config.ts and adjust
// baseURL, roles, and spec paths to match the project. testDir is set
// explicitly to './e2e' rather than left at Playwright's default -- see
// references/multi-service-setup.md for the full convention this file
// implements (dual base URLs, webServer, staging-only CI).
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? 'github' : 'html',

  use: {
    // WARNING: this suite creates/mutates real data (verifying a UI action
    // actually persisted, not just that it looked successful -- see
    // playwright-test-design/playwright-test-implementation). Point this at
    // staging or a dedicated, regularly-reset test environment ONLY. Never
    // production. See references/multi-service-setup.md.
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  // Only start services locally. In CI, baseURL above and E2E_API_BASE_URL
  // (see fixtures.ts) point at a deployed staging environment instead --
  // nothing needs to be built from source in a CI job. See
  // references/multi-service-setup.md for the full convention, including why
  // production is never a valid target for either URL.
  webServer: process.env.CI
    ? undefined
    : [
        // Frontend: this repo's own dev server, no `cwd` override needed.
        {
          command: 'npm run dev',
          url: process.env.E2E_BASE_URL ?? 'http://localhost:3000',
          reuseExistingServer: true,
        },
        // Backend: a SEPARATE repo, checked out as a sibling directory.
        // Adjust the relative path and start command to the real backend repo.
        {
          command: 'uvicorn main:app --port 8000',
          cwd: '../../backend/<backend-project-name>',
          url: process.env.E2E_API_BASE_URL ?? 'http://localhost:8000',
          reuseExistingServer: true,
        },
      ],

  projects: [
    { name: 'setup', testMatch: /auth\.setup\.ts/ },

    // Smoke: the critical-path subset, run on all three engines every PR.
    {
      name: 'smoke-chromium',
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['setup'],
      grep: /@smoke/,
    },
    {
      name: 'smoke-firefox',
      use: { ...devices['Desktop Firefox'] },
      dependencies: ['setup'],
      grep: /@smoke/,
    },
    {
      name: 'smoke-webkit',
      use: { ...devices['Desktop Safari'] },
      dependencies: ['setup'],
      grep: /@smoke/,
    },

    // Full regression: primary engine only, per-role storage state.
    // Add one project per role that has its own spec directory.
    {
      name: 'customer-flows',
      use: { ...devices['Desktop Chrome'], storageState: 'playwright/.auth/customer.json' },
      dependencies: ['setup'],
      testMatch: /tests\/specs\/customer\/.*\.spec\.ts/,
    },
    {
      name: 'admin-flows',
      use: { ...devices['Desktop Chrome'], storageState: 'playwright/.auth/admin.json' },
      dependencies: ['setup'],
      testMatch: /tests\/specs\/admin\/.*\.spec\.ts/,
    },

    // Auth flow itself — no stored state, drives real login/logout/expiry.
    {
      name: 'auth-flows',
      use: { ...devices['Desktop Chrome'] },
      testMatch: /tests\/auth\/.*\.spec\.ts/,
    },

    // Responsive: @responsive-tagged specs only, run at real breakpoints on
    // both rendering engines that actually differ in the wild (Chrome/
    // Android, Safari/iOS). Not the whole suite duplicated per device —
    // see references/responsive-breakpoints.md for which specs belong here.
    {
      name: 'responsive-mobile-chrome',
      use: { ...devices['Pixel 5'], storageState: 'playwright/.auth/customer.json' },
      dependencies: ['setup'],
      grep: /@responsive/,
    },
    {
      name: 'responsive-mobile-safari',
      use: { ...devices['iPhone 13'], storageState: 'playwright/.auth/customer.json' },
      dependencies: ['setup'],
      grep: /@responsive/,
    },
    {
      name: 'responsive-tablet',
      use: { ...devices['iPad Mini'], storageState: 'playwright/.auth/customer.json' },
      dependencies: ['setup'],
      grep: /@responsive/,
    },
    {
      name: 'responsive-desktop',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1280, height: 800 },
        storageState: 'playwright/.auth/customer.json',
      },
      dependencies: ['setup'],
      grep: /@responsive/,
    },
  ],
});
