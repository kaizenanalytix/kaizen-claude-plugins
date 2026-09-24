This is the canonical template for the "Running the E2E suite" section
`playwright-project-structure`'s step 5a adds (or updates) in the *real
project's own* `README.md` or `docs/` — not here. This file sitting in the
plugin repo is not the deliverable; a developer working in the tested
project will never open it. Copy the section below, then replace every
`<placeholder>` with that project's actual `npm` scripts and actual
`playwright.config.ts` project names before it lands in the real project.

---

## Running the E2E suite

> **Never run this suite against production.** Point `E2E_BASE_URL` /
> `E2E_API_BASE_URL` (or however this project names them) only at a local
> dev server, a dedicated test environment, or staging. These tests create
> and mutate real data — pointed at production, that's not a false pass,
> it's real orders/profiles/whatever the suite exercises, in a database
> real users see.

### Prerequisites

First run only, if the browsers aren't already installed:

```bash
npx playwright install
```

### Running the suite

- Full run: `npx playwright test` (or `npm run <e2e-script>`, if
  `package.json` defines one).
- One project/browser: `npx playwright test --project=<project-name>`
- A tagged subset: `npx playwright test --grep @smoke`
- One test by name: `npx playwright test -g "<test name>"`

### Inspecting results after a run

- HTML report: `npx playwright show-report`
- Trace viewer for one specific failed test:
  `npx playwright show-trace <path-to-trace.zip>` (the path is printed in
  the terminal output, and linked from the HTML report next to the failing
  test).

### Watching tests execute live

- `npx playwright test --headed` runs in a real, visible browser window
  instead of headless.
- `npx playwright test --ui` opens Playwright's UI mode — the easiest way
  for anyone, technical or not, to actually watch what a test does step by
  step: it steps through each action, shows the page as it looked at that
  moment, and lets you replay any part of the run without reading a line of
  code.
