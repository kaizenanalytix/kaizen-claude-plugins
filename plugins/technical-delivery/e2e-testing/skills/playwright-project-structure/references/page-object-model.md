# Page Object Model

## The rule: interactions in the page object, assertions in the spec

A page object is a thin wrapper over a page (or a major reusable region of
one) that exposes what a user could do or observe — never what the test is
checking. The spec file owns every `expect(...)`.

**Good:**

```typescript
// e2e/pages/login-page.ts
export class LoginPage {
  constructor(private page: Page) {}

  async login(email: string, password: string) {
    await this.page.getByLabel('Email').fill(email);
    await this.page.getByLabel('Password').fill(password);
    await this.page.getByRole('button', { name: 'Log in' }).click();
  }
}

// e2e/specs/login.spec.ts
test('valid customer login', async ({ page }) => {
  const loginPage = new LoginPage(page);
  await loginPage.login('customer@example.com', 'password123');

  await expect(page).toHaveURL('/dashboard');
  await expect(page.getByText('customer@example.com')).toBeVisible();
});
```

**Bad — assertions leak into the page object:**

```typescript
export class LoginPage {
  async loginAndExpectSuccess(email: string, password: string) {
    // ...fill fields, click...
    await expect(this.page).toHaveURL('/dashboard'); // ← belongs in the spec
  }
}
```

This is bad because it hides what's actually being verified from the
person reading the spec file, and it forces every caller into the same
assertion even when a different test wants to check a *different* outcome
of the same login action (e.g. a locked-account test wants to assert an
error message instead).

## Keep page objects narrow

One page object per page or per genuinely reusable region (e.g. a shared
`NavBar` component used across many pages can be its own small page object,
composed into the page-level ones). Don't let a `CheckoutPage` grow methods
for `ProductSearchPage` concerns just because a checkout flow happens to
pass through the product list — compose two page objects in the spec
instead of merging their responsibilities into one.

## Base page object

Give every page object a shared base class (`assets/pages/base-page.ts`)
holding the constructor and any truly universal helpers (e.g. a `goto()`
that navigates and waits for the page to be ready). Don't put page-specific
logic in the base class.

---
_Last reviewed: 2026-08-07_
