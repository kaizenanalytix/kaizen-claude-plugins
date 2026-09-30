---
name: playwright-project-structure
description: >
  Scaffolds and maintains a growing Playwright test suite's project layout —
  the e2e/{pages,fixtures,api,utils,test-data,auth} folder structure, the one
  place a browser-driven test lives in this marketplace (a sibling frontend
  plugin's react-testing skill covers no browser tests at all), the Page
  Object Model split between page objects (interactions) and spec files
  (scenarios and assertions), per-role auth storageState reuse, a dual
  base-URL fixture for frontend vs. backend calls, and
  playwright.config.ts's browser/project matrix and webServer setup. Use
  when the user says things like "set up Playwright", "organize this e2e
  suite", "add a page object", "reuse login across tests", "run tests
  across multiple browsers", or "how do I run this against a real backend".
---

# Playwright Project Structure

## 1. Check what already exists before creating anything

Never copy an `assets/` file over one that already exists without reading
it first. This skill scaffolds a **separate `e2e/` folder** at the
project root (never mixed into `src/`/app code) — but "scaffold" means
filling in what's missing, not recreating what's already there:

- No `e2e/` directory at all → genuinely greenfield, copy the `assets/`
  files in directly as the starting scaffold.
- `e2e/` already exists → read its current layout first. Only create the
  subfolders/files that are actually missing; don't move, rename, or
  restructure what's already there just to match the layout below exactly.
- `playwright.config.ts` already exists → read it first. Don't overwrite it
  wholesale with `assets/playwright.config.ts` — add only what's missing
  (e.g. a project the file doesn't have yet). If the existing config is
  structured differently enough that a real rewrite is warranted, say so
  and confirm with the user before doing it, the same way scenario design
  gets confirmed in `playwright-test-design`.
- A page object (e.g. `login-page.ts`) already exists → treat
  `assets/pages/*` as the pattern to follow for any *new* page object, not
  a file to copy over the existing one.

**This skill owns `@playwright/test` as a dependency, not
`react-project-bootstrap`.** A sibling `frontend` plugin's greenfield
scaffold deliberately doesn't install Playwright at all — every
browser-driven test in this marketplace lives here, none in `react-testing`.
The first time this skill scaffolds a project, add `@playwright/test` to
`package.json`'s `devDependencies` and an `"e2e": "playwright test"` script,
merged in alongside whatever's already there — same rule as everything else
in this step, don't overwrite.

**Why `e2e/`, specifically:** a clear, self-explanatory name for the one
place a browser-driven test lives in this repo — read
`references/multi-service-setup.md` for the dual base-URL setup and
`webServer` convention this skill also owns.

The target layout to fill in incrementally:

```
e2e/
├── pages/       # Page Object Model classes — one per page/major UI area
├── fixtures/    # Playwright fixtures (custom test/expect, shared setup)
├── api/         # thin API client(s) for setup/teardown/verification calls
├── utils/       # test-data generators and other shared helpers
├── test-data/   # static seed data that isn't generated per-test
└── auth/        # spec files that exercise auth itself (login/logout/expiry)
```

- `pages/` — interactions only, no assertions (see section 2).
- `fixtures/` — anything injected into tests via Playwright's fixture
  system, including a custom `test` that auto-provides page objects, and
  `assets/fixtures.ts`'s dual base-URL `api` fixture (see
  `references/multi-service-setup.md`).
- `api/` — used by specs to set up or verify state without going through
  the UI (see `playwright-test-implementation`).
- `utils/` — e.g. unique test-data generators, date helpers.
- `test-data/` — read-only seed/reference data, not generated-per-test data
  (that belongs in a factory in `utils/`).
- `auth/` — specs that test the login/logout/session-expiry flow itself;
  everything else authenticates via stored state instead of re-testing
  login every time (section 3).

## 2. Page objects hold interactions, specs hold scenarios

A page object exposes user-observable actions and queries (`login(email,
password)`, `addToCart(productName)`, `getOrderTotal()`) — never
assertions. Assertions live in the spec file, calling the page object's
methods and then asserting on what they return or on page state directly.
Keep page objects narrow: a `CheckoutPage` shouldn't also expose unrelated
`ProductSearchPage` methods just because they're both reachable from it.

See `references/page-object-model.md` for the full rule with a good/bad
example, and copy `assets/pages/base-page.ts` +
`assets/pages/login-page.ts` as the starting pattern.

## 3. Per-role authenticated storage state

Login itself usually isn't what a given test is checking — re-running the
full UI login flow in every test is slow and couples unrelated tests to the
login flow's stability. Instead, log each role in **once** and reuse the
saved session:

1. A Playwright "setup" project logs in as each role and saves
   `storageState` to `playwright/.auth/<role>.json` — see
   `assets/auth.setup.ts` for the admin/manager/employee/customer pattern.
2. `playwright.config.ts`'s `projects` array points each role-scoped spec
   directory at its saved state via `test.use({ storageState:
   'playwright/.auth/<role>.json' })`.
3. Only `e2e/auth/` specs (which test login/logout/expiry itself) skip
   the stored state and drive the real login flow.

Read `references/auth-storage-state.md` for the full config wiring and
when to regenerate a stored state (e.g. after an auth-flow change breaks
the saved session's shape).

## 4. Browser/project matrix

Define Chromium, Firefox, and WebKit projects in the project's own
`playwright.config.ts`, using `assets/playwright.config.ts` as the
reference pattern (merge into an existing config per step 1, don't
overwrite it). Tag a small, critical subset of specs (e.g. via `@smoke` in
the test title or a dedicated `smoke` project with a `grep`) to run on all
three engines on every PR; let broader regression coverage run on the
primary engine (or all three on a schedule) depending on the project's CI
budget.

**Bringing up the frontend and backend together** (a `webServer` array
starting both, local dev vs. CI, and never pointing either at production)
is also config-level and lives in the same file — read
`references/multi-service-setup.md` before wiring `playwright.config.ts` for
a project where frontend and backend are separate repos.

## 4a. Responsive/viewport matrix

Cross-browser and responsive are two different axes — three desktop
engines does not mean the app has been checked at a phone or tablet width.
Add the `responsive-*` projects from `assets/playwright.config.ts`: mobile
Chrome (`Pixel 5`), mobile Safari (`iPhone 13`), a tablet size
(`iPad Mini`), and a real desktop viewport, each gated behind a
`@responsive` grep tag the same way `@smoke` gates the cross-browser subset.
This is deliberately not "run the whole suite at every device size" — read
`references/responsive-breakpoints.md` for which specs actually belong in
that tagged subset and why the rest don't need it.

## 4b. Verify the target environment is real — before anything runs against it

`E2E_BASE_URL` and `E2E_API_BASE_URL` (however this project names them)
decide what a running suite actually touches, so before wiring `webServer`
or handing this project off to be tested, confirm what those variables
really point at. A naive check — "the string contains `localhost` or
`staging`" — is not a check; it's exactly the kind of assumption that lets a
suite run against a shared or production-sounding host by accident.

First, determine whether a real backend even exists for this project at
all. Some frontends have no backend yet — every request resolves through an
in-process mock (RTK Query's `fakeBaseQuery`, an MSW handler, or similar),
with no real network call and nothing a test run could put at risk. If
that's the case, say so explicitly in whatever you tell the user or write
in config comments, and skip the rest of this check — there is nothing to
protect against.

If a real backend does exist, actively confirm the configured target is a
genuine test/dev/staging environment, not production and not someone else's
shared environment. Read the actual source of truth — the project's env
files, its deployment config, or a `webServer` block that starts a local
instance — and confirm the URL resolves to something under this project's
own control. "It looks like a staging URL" is not confirmation; "this env
file is generated by our own deploy pipeline for our own test account, and I
read the value" is.

If there is any doubt at all after checking, stop and ask the user to
explicitly confirm the target before running anything against it. Never
assume an env var is safe by default just because its name or value looks
like it should be — see `references/multi-service-setup.md`'s "never point
either URL at production" section for what's actually at stake: these tests
create and mutate real data, and pointed at the wrong host that's not a
false pass, it's real damage. `playwright-test-implementation` repeats this
same check at the point tests are actually run, since that's the last
chance to catch a target that changed after scaffolding.

## 5. Wire debugging artifacts into config

Set `trace: 'on-first-retry'` and screenshot/video-on-failure in the
project's `playwright.config.ts` — this is the config-side half of the
debugging policy; `playwright-test-implementation` covers what to actually
do with those artifacts when a test fails.

## 5a. Document how to run the suite in the project's own README

Once this skill scaffolds an `e2e/` folder — or a
`playwright-test-implementation` run adds meaningfully to one that already
exists (a new spec directory, a new tagged project, enough new specs that
the existing instructions are stale) — add or update a "Running the E2E
suite" section in the project's own documentation, not this plugin's. Check
first whether the project already documents things in a `docs/` folder (a
`docs/DEPLOYMENT.md`, a `docs/qa/` tree, etc.) versus a root `README.md`,
and follow whichever convention the project already has rather than
defaulting to the root README out of habit.

This matters because the audience is a developer working inside that
project, who will actually open that project's own README — not an end
user of this plugin, who has no reason to ever read this plugin's README.
`assets/e2e-readme.md` is the canonical template for what this section
should contain, but the template file itself sitting in this plugin's repo
accomplishes nothing on its own: the actual deliverable is this content
landing inside the real project's own docs, adapted to that project's real
`npm` scripts and real `playwright.config.ts` project names — never left as
generic placeholders.

Cover, at minimum:

- Full run: `npx playwright test` (or the project's own `npm run
  <e2e-script>`, if `package.json` defines one).
- Running one project: `--project=<name>`, using the project's actual
  project names.
- A tagged subset: `--grep @smoke`.
- One test by name: `-g "<test name>"`.
- Inspecting results after a run: `npx playwright show-report` for the HTML
  report, `npx playwright show-trace <path>` to open the trace viewer for
  one specific failed test.
- Watching tests execute live: `--headed` for a real, visible browser
  window, and Playwright's UI mode (`npx playwright test --ui`) — call this
  out specifically as the easiest way for a non-technical stakeholder to
  actually watch what a test does step by step, without reading any code.
- A clearly-marked warning box: this suite must only ever run against a
  local/test/staging environment, never production — the same rule
  `references/multi-service-setup.md` states for the config itself, restated
  here where a developer who never opens this skill's references will still
  see it.

## 6. Hand off

Once the structure exists: scenarios come from `playwright-test-design`,
actual test code from `playwright-test-implementation`.

Scaffolding the structure is not the same as writing the tests, even though
the two can start to feel adjacent once the layout, page-object pattern,
and config are all in place. Hand off to `playwright-test-implementation`
explicitly rather than continuing on to hand-write spec files here — its
own checklist (locator priority, a real business-result assertion instead
of a UI-only check, error-path coverage, waiting strategy, and the
run-and-triage step it owns) is exactly what gets missed when an agent
feels it already has "enough context" from this skill and
`playwright-test-design` combined, and skips straight to writing code
instead of actually working through that checklist.

---
_Last reviewed: 2026-08-17_
