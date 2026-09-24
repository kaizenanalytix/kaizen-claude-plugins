# Combining API and UI calls

## The rule

Use the API directly for any part of a test that isn't the behavior under
test. Reserve the UI for the specific action being verified. This keeps
tests fast and focused, and stops a slow or brittle setup flow from making
every test that depends on it flaky.

## Worked example: testing order cancellation

The behavior under test is "a customer can cancel an order from the UI and
see it reflected." Creating the order in the first place is not part of
that — so don't drive the full checkout UI flow just to get an order to
cancel.

```typescript
import { test, expect } from '../fixtures/fixtures';

test('customer can cancel an order', async ({ page, api }) => {
  // Setup via the backend API directly — not under test, so skip the UI
  // flow entirely. `api` (not `request`) is bound to the backend's own
  // origin — see references/multi-service-setup.md.
  const createResponse = await api.post('/api/orders', {
    data: { productId: 'widget-1', quantity: 1 },
  });
  const { id: orderId } = await createResponse.json();

  // Execute via UI — this is the actual behavior under test.
  await page.goto(`/orders/${orderId}`);
  await page.getByRole('button', { name: 'Cancel Order' }).click();
  await page.getByRole('button', { name: 'Confirm' }).click();

  // Verify via UI...
  await expect(page.getByText('Order cancelled')).toBeVisible();

  // ...and via the backend API, confirming the actual persisted state changed.
  const verifyResponse = await api.get(`/api/orders/${orderId}`);
  expect((await verifyResponse.json()).status).toBe('cancelled');
});
```

## When *not* to shortcut through the API

If the thing under test is the checkout flow itself, don't shortcut it —
that's the behavior the test exists to verify. The rule is about setup and
verification steps that surround the behavior under test, not about the
behavior itself.

---
_Last reviewed: 2026-08-07_
