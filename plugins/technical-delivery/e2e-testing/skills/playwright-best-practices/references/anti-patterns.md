# Playwright anti-patterns: bad vs. good

One before/after pair per rule from `SKILL.md`. Use these as copyable
templates when writing a review.

## 1. Locator strategy — brittle CSS selector

```typescript
// Bad: tied to markup/class structure, breaks on any styling refactor
await page.locator('.btn.btn-primary.submit-btn').click();

// Good: resilient to markup changes, mirrors how a user finds the button
await page.getByRole('button', { name: 'Submit' }).click();
```

## 2. Fixed wait instead of state-based waiting

```typescript
// Bad: guesses how long the request takes; slow when it's fast, flaky when it's slower
await page.getByRole('button', { name: 'Place Order' }).click();
await page.waitForTimeout(3000);
await expect(page.getByText('Order confirmed')).toBeVisible();

// Good: waits exactly as long as needed, no guessing
await page.getByRole('button', { name: 'Place Order' }).click();
await expect(page.getByText('Order confirmed')).toBeVisible();
```

## 3. Missing business-result assertion

```typescript
// Bad: only checks the UI said it worked
test('creating an order', async ({ page }) => {
  await page.getByRole('button', { name: 'Place Order' }).click();
  await expect(page.getByText('Order confirmed')).toBeVisible();
});

// Good: also confirms the order actually persisted
test('creating an order', async ({ page, request }) => {
  await page.getByRole('button', { name: 'Place Order' }).click();
  await expect(page.getByText('Order confirmed')).toBeVisible();

  const orderId = await page.getByTestId('order-id').innerText();
  const response = await request.get(`/api/orders/${orderId}`);
  expect(response.status()).toBe(200);
});
```

## 4. Test independence violation

```typescript
// Bad: test B assumes test A already ran and created this order
test('order appears in list', async ({ page }) => { /* creates order-123 */ });
test('order can be cancelled', async ({ page }) => {
  await page.goto('/orders/order-123'); // depends on the previous test
  await page.getByRole('button', { name: 'Cancel Order' }).click();
});

// Good: each test creates its own data
test('order can be cancelled', async ({ page, request }) => {
  const { id } = await createOrderViaApi(request);
  await page.goto(`/orders/${id}`);
  await page.getByRole('button', { name: 'Cancel Order' }).click();
});
```

## 5. Assertion leaking into a page object

```typescript
// Bad: page object decides what the test is checking
class LoginPage {
  async loginAndExpectSuccess(email: string, password: string) {
    await this.fillAndSubmit(email, password);
    await expect(this.page).toHaveURL('/dashboard'); // hidden assertion
  }
}

// Good: page object performs the action; spec owns the assertion
class LoginPage {
  async login(email: string, password: string) {
    await this.fillAndSubmit(email, password);
  }
}

test('valid login redirects to dashboard', async ({ page }) => {
  await new LoginPage(page).login('user@example.com', 'pass');
  await expect(page).toHaveURL('/dashboard');
});
```

## 6. Over-mocking a suite labeled "e2e"

```typescript
// Bad: every request mocked — not testing the real backend at all
test('checkout flow', async ({ page }) => {
  await page.route('**/api/cart', (r) => r.fulfill({ json: mockCart }));
  await page.route('**/api/checkout', (r) => r.fulfill({ json: mockOrder }));
  await page.route('**/api/payment', (r) => r.fulfill({ json: mockPayment }));
  // ...drives the UI against entirely fake responses
});

// Good: real backend throughout; mock only the one thing being isolated
// (e.g. simulating a payment-provider outage)
test('checkout shows an error when payment provider is down', async ({ page }) => {
  await page.route('**/api/payment', (route) => route.abort());
  // ...cart and checkout hit the real backend; only payment is faked
});
```

## 7. Happy-path-only suite

```typescript
// Bad: the only scenario in the whole file
test('user can log in', async ({ page }) => { /* valid credentials only */ });

// Good: happy path plus the applicable error scenarios
test('user can log in', async ({ page }) => { /* valid credentials */ });
test('invalid password shows an error', async ({ page }) => { /* ... */ });
test('locked account is rejected', async ({ page }) => { /* ... */ });
test('expired session redirects to login', async ({ page }) => { /* ... */ });
```

## 8. Re-logging in via the UI on every test

```typescript
// Bad: every test pays the cost of a full UI login
test.beforeEach(async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill('customer@example.com');
  await page.getByLabel('Password').fill('password');
  await page.getByRole('button', { name: 'Log in' }).click();
});

// Good: project-level storageState reuse (playwright.config.ts), no
// per-test login needed at all
export default defineConfig({
  projects: [
    {
      name: 'customer-flows',
      use: { storageState: 'playwright/.auth/customer.json' },
      dependencies: ['setup'],
    },
  ],
});
```

## 9. Suppressing a flaky test instead of fixing it

```typescript
// Bad: papers over the symptom
test('order total updates when quantity changes', async ({ page }) => {
  await page.getByLabel('Quantity').fill('2');
  await page.waitForTimeout(1000); // "fixes" the flake by guessing longer
  await expect(page.getByTestId('total')).toHaveText('$20.00');
});

// Good: root-cause it — wait for the actual state, or fix the app if the
// total genuinely updates asynchronously with no observable loading state
test('order total updates when quantity changes', async ({ page }) => {
  await page.getByLabel('Quantity').fill('2');
  await expect(page.getByTestId('total')).toHaveText('$20.00');
});
```
