---
name: playwright-test-implementation
description: >
  Writes robust Playwright tests that verify a genuine business result across
  the full stack, not just a UI-visible success state — covering locator
  strategy, auto-waiting assertions, unique per-test data, combining API
  calls with UI actions, network inspection/mocking boundaries, and
  root-causing flaky failures instead of adding fixed waits. Use when the
  user says things like "write e2e tests for X", "write a Playwright test",
  "test the checkout flow end-to-end", "this test is flaky", or "how do I
  mock/inspect a network request in this test".
---

# Playwright Test Implementation

## 1. Confirm scope was designed and confirmed, then confirm the stack

Before writing any test code, check whether a scenario list for this
workflow has already been designed and confirmed by the user via
`playwright-test-design`. If the user jumps straight to "just write e2e
tests for X" without that step, don't skip it — designing scope is a
business-judgment call made by reading the code, and it can miss a flow or
misjudge priority; writing code straight from an unconfirmed guess risks
building the wrong coverage. Hand off to `playwright-test-design` first,
get the scenario list confirmed, then come back here.

Once scope is confirmed: check for `@playwright/test` and an existing
`playwright.config.ts`. If there's no project structure yet (no
`e2e/pages/`, no auth setup project), hand off to
`playwright-project-structure` first rather than writing a spec into an ad
hoc layout.

Arriving here is itself a required step, not a formality already satisfied
by the first two. Reading `playwright-test-design`'s confirmed scenario
list and `playwright-project-structure`'s scaffolded layout tells an agent
*what* to test and *where* the code goes — it does not, by itself, apply
this skill's own checklist: locator priority, a real business-result
assertion instead of a UI-only check, error-path coverage, waiting
strategy, and the run-and-triage step at the end of this file (step 11
below). An agent that feels it already has "enough context" after the
first two skills and hand-writes spec files directly, skipping the steps
below, tends to reproduce exactly the gaps this skill's checklist exists to
catch — a test technique that quietly breaks the very thing it's meant to
verify (`references/triage-failures.md`'s `page.goto()` example is a
concrete case of this) is far easier to ship when the chain gets cut short
here. Work through the actual steps below every time, even when the first
two skills' output looks complete enough to code from directly.

## 2. Assert the real business result, not just the UI

Restate the chain from `playwright-test-design`: User Action → Frontend →
API → Backend → DB → API Response → Frontend Result. A test that only
checks a success toast appeared hasn't verified anything actually happened.
Combine a page assertion with a direct API call to confirm the underlying
state:

```typescript
import { test, expect } from '../fixtures/fixtures';

test('creating an order persists it', async ({ page, api }) => {
  await page.getByRole('button', { name: 'Place Order' }).click();
  await expect(page.getByText('Order confirmed')).toBeVisible();

  const orderId = await page.getByTestId('order-id').innerText();
  const response = await api.get(`/api/orders/${orderId}`);
  expect(response.status()).toBe(200);
  expect((await response.json()).status).toBe('created');
});
```

The UI assertion confirms the user saw the right thing; the API call
confirms the order actually exists and is retrievable — the UI alone can't
prove that. `api`, not Playwright's built-in `request` fixture, is bound to
the backend's own origin — a relative path on `request` would resolve
against the frontend's origin instead, which is not necessarily the same
service (see `playwright-project-structure`'s
`references/multi-service-setup.md`).

## 3. Locator strategy

Prefer, in order: `getByRole` > `getByLabel` > `getByPlaceholder` >
`getByText` > `getByTestId`. Avoid CSS/XPath selectors tied to DOM structure
or class names — they break on any markup refactor unrelated to the
behavior being tested. Reach for `getByTestId` only when none of the
higher-priority locators can uniquely or semantically identify the element.

## 4. Waiting and assertions

Never `page.waitForTimeout(...)` unless there is truly no reasonable
alternative — it makes tests both slow (always waits the full duration) and
flaky (not always long enough). Use Playwright's auto-waiting assertions
instead, which wait for the actual state:

```typescript
await expect(locator).toBeVisible();
await expect(page).toHaveURL('/dashboard');
await expect(locator).toHaveText('Order confirmed');
```

Every test needs a meaningful assertion of the expected business result —
"no exception was thrown" is not a passing test, it's an untested one.

## 5. Test data and independence

Generate unique data for any test that creates a record — email, username,
order reference — so tests can run concurrently and repeatedly without
colliding on shared state. Use `assets/test-data-factory.ts` as the
starting pattern. Every test performs its own Setup → Execute → Verify →
Cleanup; never write a test that depends on another test having already
created data it needs.

## 6. Combine API and UI calls

Use API calls to set up or verify state that isn't itself under test,
instead of repeating an expensive UI flow. Example: testing order
cancellation — use the API to create the order (setup, not under test), the
UI to open and cancel it (the actual behavior under test), and the API (or
UI) to verify the cancelled status. Use the `api` fixture from
`playwright-project-structure`'s `assets/fixtures.ts` for these calls, not
Playwright's built-in `request` — see `assets/api-client.ts` for a thin
request wrapper built on it and `references/api-ui-combination.md` for the
worked example and the general rule for when to reach for this.

## 7. Network inspection and mocking policy

Inspect requests when it's useful to confirm the right endpoint, method,
payload, or error handling was used. Mock only when appropriate for the
specific thing being isolated — a true end-to-end test should not mock
everything; if most of a suite's requests are mocked, most of it isn't
actually testing the real integration anymore.

## 8. Error-path coverage

For each applicable row in `playwright-test-design`'s
`references/error-scenario-checklist.md`, implement the corresponding
Playwright pattern — `route.abort()` for network failure, a delayed
`route.fulfill()` for a slow response, a cleared/corrupted storageState for
expired auth, a second concurrent submit for duplicate-request handling.
See `references/error-path-patterns.md` for the concrete code per scenario.

## 9. Browser coverage in test authoring

Project/browser config lives in `playwright-project-structure`. Here: tag
the small critical-path subset with `@smoke` in the test title so it runs
on Chromium/Firefox/WebKit on every PR; leave broader regression on the
primary engine unless the project's CI budget allows more.

## 9a. Responsive/viewport coverage

Tag a spec `@responsive` — so it runs against
`playwright-project-structure`'s `responsive-*` projects (mobile Chrome,
mobile Safari, tablet, desktop) — only when the UI genuinely behaves
differently across breakpoints, per
`playwright-project-structure`'s `references/responsive-breakpoints.md`.
For a one-off check that doesn't need its own CI project, assert directly
against a specific viewport instead:

```typescript
test('mobile nav collapses into a hamburger menu', { tag: '@responsive' }, async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/dashboard');

  await expect(page.getByRole('button', { name: 'Menu' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Primary' })).toBeHidden();

  await page.getByRole('button', { name: 'Menu' }).click();
  await expect(page.getByRole('navigation', { name: 'Primary' })).toBeVisible();
});
```

For touch-specific interactions (swipe, long-press) that only exist on the
mobile/tablet projects, use `page.touchscreen` or the locator's `.tap()`
instead of `.click()` — but only where the app actually has touch-specific
behavior; a component with no touch-only interaction doesn't need a
separate tap-based test alongside its click-based one. See
`references/responsive-testing.md` for more worked examples (grid-to-list
layout switches, conditionally-rendered content by viewport).

## 10. Debugging and flaky tests

On failure, use the trace/screenshot/video artifacts already wired into
config (Playwright Trace Viewer, network details, console logs) to find the
root cause — timing, a bad selector, shared test data, a race condition, or
environment instability. Fix the actual cause; do not add a large fixed
wait or just re-run until it passes. A flaky test is a defect in the
automation or the application, not noise to suppress. See
`references/debugging-and-flaky-tests.md`.

## 11. Run the suite before reporting anything done

A spec file that has been written or edited but never executed hasn't been
verified — it's been guessed at. Every step above this one produces
well-targeted code; none of it proves that code actually passes against the
real app. That proof only exists once the suite has been run. "I wrote the
tests" and "I verified the tests" are two different claims — never report a
test-writing task complete on the strength of the first alone, and never
treat running the suite as something to do only if the user separately
asks for it later.

**Install what's missing, then run it.** If `@playwright/test` or its
browser binaries aren't present yet, installing them is inherent to
finishing this task, not a separate action that needs a permission check of
its own:

```bash
npm install -D @playwright/test   # only if it isn't already a dependency
npx playwright install            # fetches missing browser binaries
```

**Then verify the target before anything runs against it.** This is the
same check `playwright-project-structure` performs at scaffold time,
repeated here because it's the last chance to catch a target that changed
since — an env file edited, a URL swapped, staging pointed somewhere new:

- First, determine whether a real backend exists for this project at all.
  Some frontends resolve every request through an in-process mock
  (`fakeBaseQuery`, MSW, or similar) with no real network call and nothing
  a run could put at risk — if so, say that explicitly and skip the rest of
  this check.
- If a real backend does exist, actively confirm the configured target
  (`E2E_BASE_URL` / `E2E_API_BASE_URL`, or this project's equivalents) is a
  genuine test/dev/staging environment — not by pattern-matching the URL
  string, but by reading the env file, deployment config, or `webServer`
  block that actually defines it, and confirming it resolves to something
  under this project's own control.
- If there's any doubt at all, stop and ask the user to explicitly confirm
  the target before running anything. Never assume an env var is safe by
  default just because it looks like one — see
  `playwright-project-structure`'s `references/multi-service-setup.md` for
  what's actually at stake.

**Then run it:**

```bash
npx playwright test                            # full suite
npx playwright test --project=smoke-chromium   # one project
npx playwright test --grep @smoke              # a tagged subset
npx playwright test -g "some test name"        # one test
```

Green, on its own, still isn't the end of the task — every failure needs to
be triaged before anything gets reported. See the next step.

## 11a. Triage every failure — never guess in either direction

A failing test is a disagreement between what the test expected and what
the app actually did. Before touching either side, trace the failure back
to the app's own source code — the component, the handler, the comment
explaining why it works the way it does — and sort it into exactly one of
three outcomes. Read `references/triage-failures.md` for the full decision
procedure and three worked examples (a `history.replace` case, a
`page.goto()` case, and an accessibility-regression case) that all start
from the same kind of failing assertion and land on three different
answers:

1. **Intentional, and the test's assumption was wrong.** The code (a
   comment, a doc, or an unambiguous design decision) shows the behavior is
   deliberate, and the test assumed something else. Fix the test, re-run.
2. **Clearly not intentional.** The behavior contradicts the code's own
   stated intent, or is an obvious defect — broken keyboard access, data
   loss, a security hole. Flag it to the user as a real application
   finding. Never loosen, delete, or skip an assertion just to force a
   pass — that's not fixing the failure, it's hiding it.
3. **Genuinely ambiguous.** The code doesn't make clear whether this was
   intended. Do not guess in either direction: don't fix the app, and don't
   adjust the test's expectation. Collect it and move on to the next
   failure.

**"I can't tell, so I'll just make it pass" is never an option.** Forcing a
pass on an ambiguous failure permanently launders a possible real bug into
"expected behavior" — every future run of that test then falsely confirms
the app is fine, and the one signal that would have caught it is gone.

Once every failure in the run has been sorted, present all of the
**ambiguous** ones together in a single end-of-run report — batched at the
end, not interrupting per failure. For each one, include:

- The scenario/test name.
- What the test expected.
- What the app actually did, with concrete evidence — the actual error
  output, plus the relevant snippet of app code.
- A direct question: "Which is correct — should I update the test, or is
  this an app defect?"

Wait for the user's answer before resolving those specific cases. "Done"
for this skill means: green, plus any real findings clearly labeled as
such, plus this end-of-run question for anything ambiguous — never a
silent guess in either direction, and never "written but unrun."

---
_Last reviewed: 2026-08-17_
