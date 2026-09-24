# Multi-service setup: two base URLs, bringing both up, and where the suite lives

This suite exists to verify that a real UI action produces a real backend/database
result — which means it always involves at least two services (frontend, backend),
and usually two separate origins. This file covers the mechanics of that: modeling
the two origins correctly, starting both for local development, where the suite's
own files live when frontend and backend are separate repos, and how CI runs it.

## Read this first: never point either URL at production

**These tests create and mutate real data.** `playwright-test-design` and
`playwright-test-implementation` both require verifying real persistence — a
direct API call confirming a record actually exists after a UI action, not just
that the UI displayed a success message. That means every "create X" scenario
genuinely writes a record into whatever `E2E_BASE_URL` and `E2E_API_BASE_URL`
point at.

Pointed at production, this doesn't produce a false pass — it creates real
orders, real profiles, whatever the suite happens to exercise, in a real database
real users see. **Staging, or a dedicated, regularly-reset test environment,
only. Never production.** Treat a change to either env var that points somewhere
unverified as something to stop and ask about before merging, not something to
wave through.

## Two base URLs, modeled separately

A frontend dev server and a backend API server are almost never the same origin
— even in a single monorepo, they're typically two different ports. Playwright's
`use.baseURL` (in `playwright.config.ts`) is what `page.goto()` resolves relative
paths against, and it's also what the built-in `request` fixture resolves against
by default. If a test calls `request.post('/api/orders', ...)` expecting it to
reach the backend, it will instead silently hit the frontend's own origin unless
the two happen to be proxied together — which nothing here guarantees.

The fix: a second, independently-configured request context, bound to
`E2E_API_BASE_URL` instead of `E2E_BASE_URL`. `assets/fixtures.ts` provides this
as an `api` fixture:

```typescript
import { test as base, expect, type APIRequestContext } from '@playwright/test';

const API_BASE_URL = process.env.E2E_API_BASE_URL ?? 'http://localhost:8000';

export const test = base.extend<{ api: APIRequestContext }>({
  api: async ({ playwright }, use) => {
    const context = await playwright.request.newContext({ baseURL: API_BASE_URL });
    await use(context);
    await context.dispose();
  },
});

export { expect };
```

The rule this creates: `page` (and cookie manipulation, which is page-context) use
the frontend origin; any direct backend call — setup, verification, anything
`assets/api-client.ts` does — uses `api`, imported from this fixtures file, never
the built-in `request`. Never let a relative path in an API call "happen" to
resolve correctly by coincidence of matching ports in local dev; it will stop
working the moment the two services genuinely diverge.

## Bringing both services up for local development

Playwright's `webServer` config option starts one or more processes before the
suite runs, waits for each one's `url` to respond, and tears them down after —
this is what replaces manually starting both services by hand every time:

```typescript
webServer: process.env.CI
  ? undefined
  : [
      // Frontend: this repo's own dev server, no `cwd` override needed.
      {
        command: 'npm run dev',
        url: process.env.E2E_BASE_URL ?? 'http://localhost:3000',
        reuseExistingServer: true,
      },
      // Backend: a SEPARATE repo, checked out as a sibling directory.
      {
        command: 'uvicorn main:app --port 8000',
        cwd: '../../backend/<backend-project-name>',
        url: process.env.E2E_API_BASE_URL ?? 'http://localhost:8000',
        reuseExistingServer: true,
      },
    ],
```

The `cwd` on the backend entry assumes a workspace laid out with frontend and
backend as sibling directories under a shared parent (`frontend/<project>`,
`backend/<project>`) — adjust the relative path to match the actual layout.
`reuseExistingServer: true` unconditionally, not `!process.env.CI`, because this
whole block is skipped in CI (see below) — there's no "always start fresh in CI"
case to encode here, since CI never runs this block at all.

## Where the suite lives

**Inside the frontend repo, in a folder named `e2e/`.**

- **Inside the frontend repo, not a dedicated third repo.** Playwright is a
  JS/TS tool; the frontend repo already has that toolchain. The backend keeps its
  own, completely separate test suite in its own repo (`fastapi-testing`'s
  unit/integration/contract layers) — this suite reaches the backend purely as an
  external HTTP dependency via the `api` fixture above, and never needs to "live"
  there.
- **`e2e/` as the name.** There is exactly one place a browser-driven test
  lives in this marketplace — a sibling `frontend` plugin's `react-testing`
  skill covers unit and integration only and hands off every browser-driven
  case here, regardless of scope. `e2e/` names that one place plainly. Set
  `testDir: './e2e'` explicitly in `playwright.config.ts` (as
  `assets/playwright.config.ts` does) rather than relying on Playwright's
  default `testDir`, so the folder name is a deliberate choice, not an
  accident of the tool's defaults.

## CI: default to a deployed/staging environment

`E2E_BASE_URL` and `E2E_API_BASE_URL` point at an already-running staging
deployment. The CI job for this suite never checks out or builds the backend repo
at all — it just runs Playwright against whatever's already deployed there. This
avoids the meaningfully heavier lift of one CI job checking out, building, and
starting two-plus separately-versioned repos before it can even begin testing.

For a team that outgrows this and wants to test the exact commit under review
rather than whatever's on staging: check out the backend repo as a sibling
directory in the same CI job, build/start it, and let the `webServer` array above
handle bringing both services up — the same mechanism used for local dev, just
run inside CI instead of skipped by it. This is a real option, just not the
documented default here, since it's a meaningfully heavier CI setup to build and
maintain across multiple repos.
