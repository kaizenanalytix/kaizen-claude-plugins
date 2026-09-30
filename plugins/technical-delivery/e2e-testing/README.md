# e2e-testing

The seam between a sibling `frontend` plugin and a sibling `backend` plugin,
same as `api-contract` — but where `api-contract` is the seam for *data
shapes*, this plugin is the seam for *behavior*: does a real UI action,
driven through a real backend and database, actually produce the business
result it claims to.

## Overview

This plugin teaches Claude how to design, document, structure, and write
cross-stack Playwright tests. It does not re-teach the test pyramid — a
sibling `architecture-foundations` plugin's `test-pyramid` skill already
covers unit/integration/e2e proportions — and it does not re-teach API-only
validation, which a sibling `backend` plugin's `fastapi-testing` skill
already covers via Pytest/Schemathesis. This plugin owns every
browser-driven test in this marketplace, at any depth: a sibling `frontend`
plugin's `react-testing` skill covers unit and integration only and hands
off here for anything needing a real browser, whether that's a five-minute
smoke check or a full cross-stack workflow verifying a real frontend, real
backend, and real database wired together and exercised the way a real user
would.

It conceptually depends on `architecture-foundations`'s `test-pyramid` (this
plugin implements that pyramid's top e2e layer for the cross-stack case) and
optionally on a sibling `api-contract` plugin (reusing its OpenAPI schema to
know what a "correct API response" looks like) — but every skill here
restates the one relevant rule in a sentence rather than assuming those
plugins' files are physically present. `playwright-test-design` also
optionally consults a sibling `codebase-map` plugin for cached, checkpointed
codebase facts before exploring the frontend/backend code live, the same way
`frontend-architecture` and `backend-architecture` do.

## Layout

```
skills/
├── playwright-test-design/          # what to test, how to prioritize it, how to document it
├── playwright-project-structure/    # page-object-model layout, auth storage state, browser matrix
├── playwright-test-implementation/  # writing the actual test: locators, waiting, data, API+UI, debugging
└── playwright-best-practices/       # reviewing an existing suite against a violation checklist
```

Skills are grouped by the shared `playwright-` prefix, not by folder. Every
skill sits directly at `skills/<name>/SKILL.md`, which is the only depth
Claude Code discovers: a skill nested one level deeper still auto-triggers
off its `description`, but loses its namespaced `/e2e-testing:<skill>`
invocation form entirely. Keep this layout flat.

## Components

| Skill | Purpose |
|---|---|
| `playwright-test-design` | Asks the user to choose testing depth (critical vs. comprehensive) and device/browser coverage as explicit options before doing any exploration, then traces the full User Action → DB → Response → UI chain, prioritizes flows/failure modes, and documents scenarios in a standard test-case format — presenting the full list for confirmation before any code is written. |
| `playwright-project-structure` | Scaffolds the `e2e/{pages,fixtures,api,utils,test-data,auth}/` layout — the one place in this marketplace a browser-driven test lives, owning `@playwright/test` as a dependency itself rather than a sibling `frontend` plugin's greenfield scaffold — the Page Object Model split, per-role auth `storageState`, a dual base-URL fixture for frontend vs. backend calls, the `webServer` convention for bringing both up locally, the Chromium/Firefox/WebKit project matrix, and a responsive/viewport matrix (mobile Chrome, mobile Safari, tablet, desktop) in `playwright.config.ts`. |
| `playwright-test-implementation` | Writes the actual Playwright test: locator priority, auto-waiting assertions, unique per-test data, combining API calls with UI actions, responsive/viewport assertions, network inspection/mocking limits, and root-causing flaky failures. |
| `playwright-best-practices` | Reviews an existing Playwright suite against a concrete checklist: locator strategy, fixed waits, missing business-result assertions, test independence, page-object misuse, over-mocking, error-path coverage, auth reuse, and flaky-test handling. |

## Setup

Node.js and `@playwright/test` in the frontend repo (or scaffold via
`playwright-project-structure`, which sets this up in a dedicated `e2e/`
folder there). Frontend and backend are modeled as two distinct
origins, not one shared `baseURL`: `E2E_BASE_URL` for the frontend,
`E2E_API_BASE_URL` for the backend, each read by its own fixture. Locally,
`playwright.config.ts`'s `webServer` array brings both up automatically; in
CI, both env vars point at a deployed staging environment instead, and
nothing is built from source. **Never point either URL at production** —
these tests create and mutate real data. See
`playwright-project-structure`'s `references/multi-service-setup.md` for the
full convention, including why the suite lives inside the frontend repo
rather than a dedicated third repo or the backend repo.

## Usage

- "Design test cases for X" / "what should I test for this flow" / "test plan for checkout" → `playwright-test-design`
- "Set up Playwright" / "organize this e2e suite" / "add a page object" / "reuse login across tests" / "run across multiple browsers" → `playwright-project-structure`
- "Write e2e tests for X" / "test the checkout flow end-to-end" / "this test is flaky" / "mock/inspect a request in this test" → `playwright-test-implementation`
- "Review this e2e test" / "is this good Playwright" / "e2e best practices" / "review my test suite" → `playwright-best-practices`
