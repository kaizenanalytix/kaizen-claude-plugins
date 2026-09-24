# Error-path implementation patterns

Concrete Playwright patterns for the scenarios listed in
`playwright-test-design`'s `references/error-scenario-checklist.md`.

## Invalid input / empty required fields

```typescript
test('rejects an invalid email', async ({ page }) => {
  const loginPage = new LoginPage(page);
  await page.goto('/login');
  await page.getByLabel('Email').fill('not-an-email');
  await page.getByRole('button', { name: 'Log in' }).click();

  await expect(page.getByText('Enter a valid email address')).toBeVisible();
});
```

## HTTP 401 / 403 (auth / permission failures)

```typescript
test('unauthenticated request is rejected', async ({ request }) => {
  const response = await request.get('/api/orders/123');
  expect(response.status()).toBe(401);
});

test('customer cannot access admin-only endpoint', async ({ request }) => {
  // request context loaded with a customer-role storageState
  const response = await request.get('/api/admin/reports');
  expect(response.status()).toBe(403);
});
```

## HTTP 404 / 409 / 500

```typescript
test('cancelling an already-cancelled order returns 409', async ({ request }) => {
  const response = await request.post(`/api/orders/${cancelledOrderId}/cancel`);
  expect(response.status()).toBe(409);
});
```

## Network failure

```typescript
test('shows an error when the order API is unreachable', async ({ page }) => {
  await page.route('**/api/orders', (route) => route.abort());
  await page.getByRole('button', { name: 'Place Order' }).click();
  await expect(page.getByText('Something went wrong. Please try again.')).toBeVisible();
});
```

## Slow response

```typescript
test('shows a loading state while the order request is in flight', async ({ page }) => {
  await page.route('**/api/orders', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 3000));
    await route.continue();
  });
  await page.getByRole('button', { name: 'Place Order' }).click();
  await expect(page.getByText('Placing your order...')).toBeVisible();
});
```

## Duplicate submission

```typescript
test('double-clicking submit does not create two orders', async ({ page, request }) => {
  const button = page.getByRole('button', { name: 'Place Order' });
  await Promise.all([button.click(), button.click()]);

  await expect(page.getByText('Order confirmed')).toBeVisible();
  const response = await request.get('/api/orders?customerId=me');
  expect((await response.json()).orders).toHaveLength(1);
});
```

## Expired authentication

```typescript
test('an expired session redirects to login', async ({ page, context }) => {
  await context.addCookies([{ name: 'session', value: 'expired-token', url: baseURL }]);
  await page.goto('/dashboard');
  await expect(page).toHaveURL('/login');
});
```

---
_Last reviewed: 2026-08-07_
