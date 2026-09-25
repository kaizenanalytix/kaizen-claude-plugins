---
name: playwright-test-design
description: >
  Designs and documents cross-stack end-to-end test coverage for a business
  workflow before any code is written — tracing the full user-action-to-
  database-and-back chain, splitting frontend vs backend vs cross-stack
  responsibilities, prioritizing which flows and failure modes matter most,
  and recording scenarios in a standard test-case format. Use when the user
  says things like "design test cases for X", "what should I test for this
  flow", "write a test plan for checkout", "how should QA document this
  scenario", or "what's the priority order for testing this feature".
---

# Playwright Test Design

Design what to test before writing any Playwright code. One relevant rule
from `architecture-foundations`'s `test-pyramid`: e2e/contract tests are the
fewest and most expensive layer — spend that budget deliberately, on the
flows and failure modes that actually matter, not on every variant a unit
test could cover instead.

## 0. Consult the codebase map first

If a sibling `codebase-map` plugin is installed, ask its `codebase-map-sync`
skill for cached facts about this repo — the frontend and backend stacks,
module list, and file tree with per-file descriptions — before exploring the
code yourself in step 2. It already knows where the relevant pages,
components, routes, and services live, refreshed cheaply via a checkpoint
rather than a full re-read, so the chain below can be traced by reading the
one or two files the map points at instead of grepping the repo cold. If
that plugin isn't installed, explore the relevant frontend and backend code
directly; nothing here requires it.

## 1. Ask about scope: depth and device coverage, before designing anything

Before tracing any chain or reading any code, ask the user two scoping
questions as multiple-choice options, not open-ended ones — the scenario
list built in the steps below should match how much testing they actually
want, not a guess:

**Depth:**
- Critical flows only (recommended default) — the happy path plus the
  highest-priority negative/permission cases for this workflow.
- Comprehensive — every distinct feature/workflow in scope, using the same
  design method for each (see the note on this in step 5).
- Something narrower/specific — let the user name exactly which flows.

**Device/browser coverage:**
- Desktop only, primary engine (fastest to build and run).
- Desktop + mobile, both engines (Chrome and Safari) — no tablet.
- Full matrix — desktop, mobile, and tablet, cross-browser smoke on all
  three engines (see `playwright-project-structure`'s
  `references/responsive-breakpoints.md` for what that actually includes).

Skip asking only when the request already answers both unambiguously (e.g.
"just a quick smoke test for login on desktop" already answers both) —
otherwise ask before doing any exploration work, since the answer changes
how much of that work is worth doing at all. Carry both answers forward:
they scope how far step 5 prioritizes down to, and which scenarios get
tagged `@smoke`/`@responsive` when the list is presented for confirmation
in step 9.

## 2. Trace the full business-result chain

For every feature, trace: User Action → Frontend → API Request → Backend
Service → Business Logic → Database / External Service → API Response →
Frontend Result → User Confirmation.

Never design a test that only checks the UI *looked* successful. For
"Create Order", the chain means designing coverage for: the UI accepted
valid input → the correct API request/payload was sent → the API returned
the expected status/body → the order appears in the UI → the order is
retrievable via the API afterward → the error paths behave correctly. A
test plan that stops at "success toast appeared" hasn't verified the
business result at all.

## 3. Split responsibilities before scoping the test

- **Frontend concerns** — rendering, navigation, forms/inputs, validation
  messages, loading/error states, responsive behavior (only where a
  breakpoint genuinely changes behavior, not routine reflow — see
  `playwright-project-structure`'s `references/responsive-breakpoints.md`),
  auth redirects, role-based UI visibility.
- **Backend/API concerns** — method, endpoint, headers, body, auth/authz,
  status codes, response schema, invalid/missing input, duplicate requests,
  permission failures, boundary conditions.
- **Genuinely cross-stack** — the workflow itself: does the UI action
  actually produce the backend/DB result it claims to.

If the ask has no UI involved at all (e.g. "does this endpoint reject
invalid input correctly"), that's API-only — hand off to a sibling `backend`
plugin's `fastapi-testing` skill instead of designing a cross-stack workflow
test here.

## 4. Run the pre-test-design analysis first

Before listing scenarios, fill in: Feature / User / Business goal / Entry
point / Frontend behavior / API endpoints involved / Backend behavior /
Expected result / Failure possibilities / Required test data / User roles /
Dependencies. Copy `assets/pre-test-analysis-template.md` and fill it in.
This can be skipped for a trivial, low-risk flow, but do it for anything
touching money, permissions, or data mutation.

## 5. Prioritize using the standard order

Critical business workflows > authentication > payments/transactions > data
creation/modification > permissions > integrations > error handling >
regression > edge cases > cosmetic UI behavior.

Every critical workflow needs: a happy-path test, negative tests, validation
tests, permission tests, failure-handling tests, and the important edge
cases — not just the happy path.

**This order is for sequencing and CI tiering, not for silently shrinking
scope.** The default, unprompted scope is the critical few — that's what
keeps the suite small per `test-pyramid`. But if the user explicitly asks
for comprehensive coverage ("test every feature," "cover the whole app,"
"I want full e2e coverage, not just the critical path"), that is a valid,
explicit choice to honor: design a scenario list covering every distinct
workflow named, using this same method for each one — trace its chain,
apply the error-scenario checklist, document it in the standard format —
rather than quietly narrowing it back down to a handful of "critical" flows
the user didn't ask for. Use the priority order in that case to decide
*sequencing* (build and confirm the critical ones first, then work down the
list) and which ones get cross-browser/responsive tagging, not to decide
what gets left out entirely.

## 6. Cover the standard error-scenario checklist

Read `references/error-scenario-checklist.md` and confirm the scenario list
covers the applicable items (invalid input, missing/expired auth, permission
failures, the relevant HTTP error codes, duplicate submission, slow/failed
network, etc.) — don't design a plan that's happy-path-only.

## 7. Document every scenario in the standard format

For each scenario, record: Test ID / Feature / Scenario / Preconditions /
Test Data / Steps / Expected Result / Priority / Automation Candidate / Test
Type. Copy `assets/test-case-template.md`; read
`references/test-case-documentation.md` for the full format plus a worked
`LOGIN-001` example and the Test-ID/Automation-Candidate conventions.

## 8. Design for test independence

Every scenario must be runnable on its own: no scenario may depend on
another scenario's side effects. Each is its own Setup → Execute → Verify →
Cleanup unit, and setup should favor API calls over UI steps wherever the UI
path itself isn't what's being tested. This is a design constraint here;
*how* it gets coded is `playwright-test-implementation`'s job.

## 9. Confirm the scenario list with the user before writing any code

Do not move on to `playwright-project-structure` or
`playwright-test-implementation` in the same turn a scenario list is
produced. Stop and present the documented scenarios — Test ID, one-line
Scenario, Priority, and which tag (if any: `@smoke`, `@responsive`, both,
or neither) each one gets, based on the device/browser answer from step 1 —
and ask the user to confirm the list covers the right business flows and
the right coverage depth before any Playwright code gets written.

This matters because scenario design is a business-judgment call this skill
makes from reading the code (see the note on this in
`playwright-test-implementation`'s "Confirm the stack" step): it can miss a
flow the code doesn't make obvious, misjudge a priority, or scope a
workflow too narrowly or too broadly. Writing test code against an
unconfirmed scenario list risks implementing the wrong coverage, or
coverage the user didn't actually want yet. A short scenario list is cheap
to correct before code exists; it's expensive to correct after.

Treat this as a hard stop, not a suggestion — even if the user's original
ask sounded like "just write the tests," produce and confirm the scenario
list first. Proceed to implementation only after the user confirms or
edits the list.

## 10. Hand off

Once the scenario list is confirmed by the user:

- No Playwright project structure yet → hand off to
  `playwright-project-structure`.
- Structure exists → hand off to `playwright-test-implementation` to write
  the actual tests.

---
_Last reviewed: 2026-08-07_
