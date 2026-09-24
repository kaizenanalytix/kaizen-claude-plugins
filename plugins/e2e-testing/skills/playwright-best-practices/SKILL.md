---
name: playwright-best-practices
description: >
  Reviews an existing Playwright test suite against a concrete, opinionated
  checklist — locator strategy, fixed waits, missing business-result
  assertions, test independence, page-object misuse, over-mocking, error-path
  coverage, auth reuse, and flaky-test handling. Use when the user says
  things like "review this e2e test", "is this good Playwright", "e2e best
  practices", "why is this test flaky", or "review my test suite".
---

# Playwright Best Practices

Apply this skill when reviewing an existing Playwright spec, a page object,
or a whole `e2e/` directory, or when asked generally whether some e2e code
is "good." This is a checklist of concrete rules to check against, not a
tutorial — walk the code against each item below and call out violations by
name.

## 1. Locator strategy

Flag any CSS selector, XPath, or class-name-based locator where
`getByRole`, `getByLabel`, `getByPlaceholder`, or `getByText` could
uniquely identify the same element. `getByTestId` is acceptable only when
none of those can — not as a default reach.

## 2. Fixed waits instead of state-based waiting

`page.waitForTimeout(...)` is a smell every time it appears — it's almost
always working around a missing or wrong assertion, not a genuine
unavoidable case. Flag it and replace it with an auto-waiting assertion
(`toBeVisible`, `toHaveURL`, `toHaveText`) that waits for the actual state
the test cares about.

## 3. Missing business-result assertions — the most important thing to catch

A test that only asserts a success toast, a redirect, or "no exception was
thrown" hasn't verified the business result happened. For any test
covering data creation/modification, check whether it also confirms the
change persisted — via a follow-up API call, a page reload, or checking the
data appears somewhere else in the UI — not just that the immediate UI
response looked right.

## 4. Test independence violations

Flag any test that only passes when run after another specific test, or
that reads/mutates data another test created. Each test should be its own
Setup → Execute → Verify → Cleanup unit. A suite that must run in a fixed
order, or that breaks under `--shard`/parallel execution, has this problem.

## 5. Assertions leaking into page objects

A page object method should return data or perform an action — never call
`expect(...)` itself. If a page object has a method like
`loginAndExpectSuccess()`, that's a violation: it hides what's being
verified and forces every caller into the same assertion. Split it into an
interaction method (in the page object) and an assertion (in the spec).

## 6. Over-mocking in a suite calling itself "end-to-end"

If most of a suite's network calls are mocked via `page.route(...)`, it
isn't actually testing the real integration between frontend and backend
anymore — flag this as a mislabeled suite (it's really a frontend
integration test wearing Playwright) rather than genuine e2e coverage.
Mocking is legitimate for a specific, isolated scenario (e.g. simulating a
500 or a network failure) — the issue is universal mocking, not any
mocking at all.

## 7. Error-path coverage

A suite that only contains happy-path scenarios is under-testing. Check
for coverage of at least the applicable items from
`playwright-test-design`'s `references/error-scenario-checklist.md` —
invalid input, permission failures, expired auth, duplicate submission,
network/slow-response handling — for any workflow important enough to have
e2e coverage in the first place.

## 8. Auth reuse

Flag any suite where most specs drive a full UI login at the start of the
test, instead of reusing a saved `storageState` per role
(`playwright-project-structure`'s `references/auth-storage-state.md`).
Repeated UI login both slows the suite down and makes every unrelated test
fragile to login-flow changes. The exception is `e2e/auth/` specs, which
are specifically testing login/logout/session-expiry and should drive the
real flow.

## 9. Flaky-test handling

Flag suppression patterns: `test.fixme()`/`test.skip()` left on a flaky
test indefinitely, a bumped-up `retries` count used as a substitute for a
fix, or a fixed wait added specifically because a test was flaky. A flaky
test is a defect (in the automation or the app) that needs root-causing —
see `playwright-test-implementation`'s `references/debugging-and-flaky-tests.md`
for the categories to check.

## 10. Reference file

Read `references/anti-patterns.md` for a bad/good code snippet for each
rule above — use it to produce concrete before/after examples in a review
rather than describing the fix abstractly.

---
_Last reviewed: 2026-08-17_
