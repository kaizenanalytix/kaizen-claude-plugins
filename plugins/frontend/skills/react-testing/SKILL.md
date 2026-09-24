---
name: react-testing
description: >
  Implements the base of the test pyramid with React tooling — Vitest unit
  tests and RTL+MSW integration tests. Does not cover browser-driven tests at
  all; a sibling e2e-testing plugin owns every Playwright/browser-driven test
  in this marketplace, regardless of scope or depth. Always lists the
  intended test cases in plain language and waits for the user to confirm the
  coverage before writing any test code. Use when the user says things like
  "write tests", "test this component/hook/slice", "what should we test
  here", or "how should this be tested".
---

# React Testing

Use this skill whenever tests need to be written for React code, or when
deciding what kind of test a given piece of behavior deserves. One sentence
of the model this depends on: the test pyramid (mostly unit, some
integration, a narrow top) comes from `architecture-foundations` — this
skill implements the pyramid's base two layers with React-specific tooling.
It stops there on purpose: **any browser-driven test, at any depth — a
five-minute smoke check or a full cross-stack workflow — belongs to a
sibling `e2e-testing` plugin, not this skill.** There is exactly one home
for Playwright/browser-driven tests in this marketplace; this skill isn't a
second one at a smaller scale.

## 1. Confirm the stack

Check `package.json` for `vitest`, `@testing-library/react`, and `msw` — and
also for `jest`, which some projects use instead of Vitest. The two layers
below are tool-independent; only the syntax changes.

- **All three present** → apply this skill as written.
- **Jest instead of Vitest** → the layers and what belongs in each are
  unchanged. Match the project's existing test files rather than introducing
  Vitest alongside Jest.
- **A layer's tooling is missing** → say which layer can't be written and what
  it would take, then let the user decide. Don't install a test runner as a side
  effect of a request to write one test.
- **No test tooling at all** → this is common and it is worth naming plainly
  rather than assuming. Some projects deliberately gate on `tsc --noEmit` and
  nothing else. Report that, say what the first layer would cost to set up, and
  **don't add "run the tests" to a task in a project that has none** — that
  instruction will just fail for whoever follows it.
- **Greenfield** → hand off to `react-project-bootstrap`, which installs all
  three.

## 2. List the cases and get them confirmed before writing any test code

**This is a hard stop, not a suggestion.** Even when the request sounded like
"just write the tests", work out what the cases are, present them, and wait.

Decide the layer per section 3 first, then present the list as one line per
case — what it asserts, and which layer it belongs to:

```
Unit
  1. reducer: setFilter replaces the active filter, leaves selection untouched
  2. reducer: clearFilters resets to the initial state
  3. useProductList: returns loading on first render, then the mapped rows
  4. formatPrice: rounds to 2dp; returns "—" for null

Integration
  5. ProductList renders the rows returned by a mocked GET /products
  6. ProductList shows the empty state when the API returns []
  7. Typing in the search box refetches with the query in the request

Not covered — say so explicitly
  - the checkout flow end-to-end (needs a real backend → e2e-testing)
```

Then ask whether that's the right coverage, and adjust before writing anything.

**Why this is worth stopping for.** Which cases matter is a judgment call made by
reading the code, and reading the code is exactly what doesn't reveal intent: a
branch can look important and be dead, or look trivial and be the one carrying
the business rule. Getting that wrong produces tests that pass, look thorough,
and assert the wrong things — the most expensive kind of test, because it buys
false confidence and still has to be rewritten. A seven-line list is nearly free
to correct now; seven test files are not.

It also surfaces the gaps. The "not covered" line above is often the most useful
part of the list, because it's where the user discovers the thing they actually
cared about isn't in scope.

**Keep it proportionate.** One line per case, no ceremony. This is a list to
react to, not a document to review — and for a single genuinely trivial case,
one line and a question is the whole gate.

## 3. Decide which layer a test belongs in

- **Unit (Vitest, `renderHook`)** — the base of the pyramid, and where most
  tests should live. Use for:
  - Slice reducers (`productSlice.reducer(state, action)`) — pure functions,
    test them as such.
  - Custom hooks (`useProducts`) via `renderHook` — test the hook's logic in
    isolation from any component tree.
  - Plain utility functions.
  No real component rendering, no network mocking needed here.
  Read `references/unit-and-integration.md` for the pattern.

- **Integration (RTL + MSW)** — fewer than unit tests, more than this skill's
  top layer. Use for a page or component rendered against a mocked API seam
  (MSW intercepts the actual `fetch`/`XMLHttpRequest` call), verifying the
  component reacts correctly to loading, success, and error states. This is
  where `renderWithProviders` (see `assets/testUtils.tsx`) earns its keep — a
  page needs the store, router, and query client wired up to render at all.
  Read `references/unit-and-integration.md`.

**If the behavior needs a real browser to verify at all** — a full flow like
login or checkout, or anything the request explicitly frames as "end to
end" — this skill stops here and hands off to a sibling `e2e-testing`
plugin's `playwright-test-design` skill, regardless of how small or
critical-path-only the check sounds. There is no lighter-weight browser
layer inside this skill to reach for instead; a five-minute smoke check and
a full cross-stack workflow both go through the same door, and
`playwright-test-design` has its own "critical flows only" depth option for
exactly the smoke-check case.

If unsure which layer a specific test belongs in, prefer the lowest layer
that can actually exercise the behavior in question — don't reach for
`e2e-testing` to verify something a unit test on a hook could cover just as
well.

## 4. Use the shared test helper

For any test that renders a component or page, use `renderWithProviders` from
`assets/testUtils.tsx` instead of RTL's bare `render`. It wraps the component
under test in the app's Redux store, router, and query providers, so
components that call `useAppSelector`, `useNavigate`, or an RTK Query hook
don't crash for lack of context. Copy this file into the project's test
setup (e.g. `src/test/testUtils.tsx`) once, then import it from every test
file that needs it.

## 5. What to actually assert

- Unit tests on a slice: dispatch an action, assert the resulting state.
- Unit tests on a hook: call the hook via `renderHook`, assert the returned
  values/handlers behave correctly (e.g. calling `onSearch` updates `search`
  and refilters `products`).
- Integration tests: assert what the user would see — loading text while a
  mocked request is pending, the rendered list once it resolves, an error
  message if MSW is configured to return a failure.

Anything beyond this — a real browser, a real flow, verifying persisted
state — is a sibling `e2e-testing` plugin's job, not an assertion style this
skill covers.

---
_Last reviewed: 2026-08-17_
