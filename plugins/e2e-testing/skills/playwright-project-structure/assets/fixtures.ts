// Copy into e2e/fixtures/fixtures.ts. Extends Playwright's base test with a
// SECOND, independently-configured request context bound to the backend's own
// origin -- separate from `page`'s baseURL (the frontend) and from the built-in
// `request` fixture (which also resolves against that same frontend baseURL by
// default). Import `test`/`expect` from THIS file, not '@playwright/test'
// directly, in any spec that calls the backend API for setup/verification.
import { test as base, expect, type APIRequestContext } from '@playwright/test';

// WARNING: this suite creates/mutates real data via direct backend calls (see
// references/multi-service-setup.md). Point E2E_API_BASE_URL at staging or a
// dedicated, regularly-reset test environment ONLY. Never production.
const API_BASE_URL = process.env.E2E_API_BASE_URL ?? 'http://localhost:8000';

export const test = base.extend<{ api: APIRequestContext }>({
  api: async ({ playwright }, use) => {
    const context = await playwright.request.newContext({ baseURL: API_BASE_URL });
    await use(context);
    await context.dispose();
  },
});

export { expect };
