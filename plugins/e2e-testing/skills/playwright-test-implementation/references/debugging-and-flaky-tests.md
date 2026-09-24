# Debugging and flaky tests

## Policy: flaky tests are defects, not noise

A test that sometimes passes and sometimes fails against unchanged code and
unchanged behavior is a defect — either in the test or in the application
it's testing. Never respond to flakiness by adding a large fixed wait or by
re-running until it goes green; both hide the defect instead of fixing it.

## What to collect on failure

- **Trace** (Playwright Trace Viewer) — the full timeline of actions,
  network requests, and DOM snapshots leading to the failure.
- **Screenshot / video** — what was actually on screen at the moment of
  failure.
- **Network details** — the actual request/response for any API call
  involved, to rule out a backend issue vs. a frontend issue.
- **Console logs** — client-side errors that didn't surface as a Playwright
  assertion failure but explain the symptom.

These are already wired into `playwright.config.ts` by
`playwright-project-structure` (`trace: 'on-first-retry'`,
`screenshot`/`video: 'on-failure'`).

## Root-cause categories, in likely order

1. **Timing** — an assertion ran before the app finished an async action.
   Fix: assert on the actual resulting state (`toBeVisible`, `toHaveText`)
   instead of adding a wait; if a genuine race exists in the app itself,
   that's an application bug, not a test problem to work around.
2. **Bad selector** — a locator matches zero or multiple elements
   depending on unrelated page state. Fix: use a locator from the priority
   list (`getByRole` > `getByLabel` > ...) that uniquely identifies the
   intended element regardless of surrounding content.
3. **Shared test data** — two tests mutate the same record concurrently.
   Fix: generate unique per-test data (`assets/test-data-factory.ts`);
   don't rely on a shared static fixture for anything a test creates or
   modifies.
4. **Race conditions in the app** — a real bug where the UI updates before
   the backend call it depends on has actually completed. Fix: this is an
   application defect the test correctly caught — file it as one, don't
   "fix" the test to tolerate it.
5. **Environment instability** — a shared test environment or database is
   under load or was left in a bad state by an unrelated process. Fix:
   isolate test data/environment per run, or move that suite to run against
   a dedicated, resettable instance.

## What not to do

- Don't add `page.waitForTimeout(...)` to "fix" a race — it either makes
  the test slow without fixing the underlying timing bug, or isn't reliably
  long enough and the flake returns later.
- Don't retry a failing test in a loop until it passes — that discards the
  evidence needed to find the actual cause.
- Don't quietly skip or delete a flaky test — mark it, but keep investigating
  it; a suppressed flaky test is a coverage gap wearing a green checkmark.

---
_Last reviewed: 2026-08-07_
