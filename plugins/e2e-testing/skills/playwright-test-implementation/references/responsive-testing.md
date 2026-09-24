# Responsive testing patterns

Worked examples for the behavioral differences that actually earn a
`@responsive` tag (see `playwright-project-structure`'s
`references/responsive-breakpoints.md` for what qualifies).

## Layout switch: grid → single column

```typescript
test('product grid becomes a single column on mobile', { tag: '@responsive' }, async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/products');

  const grid = page.getByTestId('product-grid');
  await expect(grid).toHaveCSS('grid-template-columns', /^[0-9.]+px$/); // one column
});

test('product grid shows multiple columns on desktop', { tag: '@responsive' }, async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto('/products');

  const grid = page.getByTestId('product-grid');
  const columnValue = await grid.evaluate((el) => getComputedStyle(el).gridTemplateColumns);
  expect(columnValue.split(' ').length).toBeGreaterThan(1);
});
```

Prefer asserting the *effect* of the layout change (element visible/hidden,
column count, an element's bounding box) over asserting a specific CSS
property value verbatim — the latter breaks on any unrelated styling
refactor, the same reason CSS-selector locators are avoided.

## Conditionally-rendered content by viewport

```typescript
test('sidebar becomes a bottom sheet on mobile', { tag: '@responsive' }, async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/dashboard');

  await expect(page.getByRole('complementary', { name: 'Filters' })).toBeHidden();
  await page.getByRole('button', { name: 'Filters' }).click();
  await expect(page.getByRole('dialog', { name: 'Filters' })).toBeVisible();
});
```

## Touch-specific interaction

Only write this alongside the click-based version when the app genuinely
has touch-only behavior (e.g. swipe-to-dismiss) — not as a blanket
duplicate of every desktop test:

```typescript
test('swiping a notification dismisses it on mobile', { tag: '@responsive' }, async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/notifications');

  const notification = page.getByTestId('notification-1');
  const box = await notification.boundingBox();
  await page.touchscreen.tap(box.x + box.width / 2, box.y + box.height / 2);
  // drag gesture via multiple touchscreen calls, or page.locator(...).hover()
  // fallback for engines without full touch-gesture support
  await expect(notification).toBeHidden();
});
```

## Ad hoc check vs. a CI-running tagged project

Use `page.setViewportSize(...)` directly inside a test (as above) for a
one-off assertion. Use the `responsive-*` projects in
`playwright.config.ts` (via the `@responsive` tag) when the check should
run automatically in CI on every relevant PR — the tag is what connects a
spec to those projects; a spec with no tag never runs against them, no
matter what viewport size it happens to set manually.

---
_Last reviewed: 2026-08-07_
