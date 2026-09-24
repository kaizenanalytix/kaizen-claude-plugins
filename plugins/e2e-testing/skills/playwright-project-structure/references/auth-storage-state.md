# Per-role auth storage state

## Why

Re-running the UI login flow at the start of every test is slow (every
test pays the cost of the login page rendering, the API round-trip, the
redirect) and it silently makes every unrelated test dependent on the login
flow continuing to work exactly as it does today. Playwright's
`storageState` lets a test start already authenticated, by reusing cookies
and local storage captured from a real login performed once.

## Setup: one saved state per role

```typescript
// e2e/auth/auth.setup.ts
import { test as setup } from '@playwright/test';

const roles = [
  { role: 'admin', email: 'admin@example.com', password: 'admin-pass' },
  { role: 'manager', email: 'manager@example.com', password: 'manager-pass' },
  { role: 'employee', email: 'employee@example.com', password: 'employee-pass' },
  { role: 'customer', email: 'customer@example.com', password: 'customer-pass' },
] as const;

for (const { role, email, password } of roles) {
  setup(`authenticate as ${role}`, async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('Email').fill(email);
    await page.getByLabel('Password').fill(password);
    await page.getByRole('button', { name: 'Log in' }).click();
    await page.waitForURL('/dashboard');

    await page.context().storageState({ path: `playwright/.auth/${role}.json` });
  });
}
```

## Wiring in `playwright.config.ts`

```typescript
projects: [
  { name: 'setup', testMatch: /auth\.setup\.ts/ },
  {
    name: 'customer-flows',
    use: { storageState: 'playwright/.auth/customer.json' },
    dependencies: ['setup'],
    testMatch: /tests\/specs\/customer\/.*\.spec\.ts/,
  },
  {
    name: 'admin-flows',
    use: { storageState: 'playwright/.auth/admin.json' },
    dependencies: ['setup'],
    testMatch: /tests\/specs\/admin\/.*\.spec\.ts/,
  },
  // ...one project per role that has its own spec directory
],
```

Every test in `customer-flows` starts already logged in as the seeded
customer — no test needs to call `LoginPage.login()` unless the test is
specifically about login/logout/session-expiry itself, which belongs in
`e2e/auth/` and intentionally does not use a stored state.

## When to regenerate

Regenerate (i.e. re-run the `setup` project) whenever the auth flow itself
changes shape — a new required field on login, a session cookie rename, a
new MFA step. If role-scoped tests suddenly start failing at the first
authenticated action rather than at the specific thing they're testing,
a stale stored state is the first thing to check.

---
_Last reviewed: 2026-08-07_
