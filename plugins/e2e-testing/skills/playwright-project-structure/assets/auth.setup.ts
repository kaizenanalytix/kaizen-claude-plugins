// Copy into e2e/auth/auth.setup.ts and adjust roles/credentials to match
// the project. Runs once per role via the "setup" project in
// playwright.config.ts; every other project depends on it and reuses the
// saved storageState instead of re-running this login flow per test.
import { test as setup } from '@playwright/test';
import { LoginPage } from '../pages/login-page';

const roles = [
  { role: 'admin', email: 'admin@example.com', password: 'admin-pass' },
  { role: 'manager', email: 'manager@example.com', password: 'manager-pass' },
  { role: 'employee', email: 'employee@example.com', password: 'employee-pass' },
  { role: 'customer', email: 'customer@example.com', password: 'customer-pass' },
] as const;

for (const { role, email, password } of roles) {
  setup(`authenticate as ${role}`, async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.login(email, password);
    await page.waitForURL('/dashboard');

    await page.context().storageState({ path: `playwright/.auth/${role}.json` });
  });
}
