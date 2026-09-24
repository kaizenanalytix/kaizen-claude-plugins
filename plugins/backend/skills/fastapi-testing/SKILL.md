---
name: fastapi-testing
description: >
  Applies the test pyramid to a FastAPI backend using Pytest, an async
  httpx test client, and contract testing against the OpenAPI schema, with
  shared fixtures
  for fakes and a test database. Always lists the intended test cases in plain
  language and waits for the user to confirm the coverage before writing any
  test code. Use this skill when the user says "write tests", "test this
  service", "test this repository", "test this route", "what should we test
  here", or "add integration tests".
---

# FastAPI Testing

## Purpose

Put each test at the right layer so the suite runs fast where it can and
catches real integration/contract problems where it must. One relevant
rule from `backend-architecture`: `domain` is framework-free, so domain
tests need no FastAPI app, no DB, and no HTTP client at all.

## The three layers

### 1. Unit tests (Pytest) — domain entities and services with a fake repository

- Test domain entities directly: construct one, call its methods, assert
  on invariants (e.g. `product.deactivate()` sets `is_active = False`). No
  mocking needed — entities are plain Python.
- Test services by injecting a fake/in-memory repository that implements
  the same `Protocol` as the real one (see `fastapi-data-layer`'s
  `references/repository-pattern.md`), asserting on the service's return
  value and on what got persisted, without touching a real database.
- No `TestClient`, no DB, no network — these tests should run in
  milliseconds and dominate the suite by count.

### 2. Integration tests (Pytest + an async `httpx` client + a test DB) — routes against a real repository

- Use an `httpx.AsyncClient` over `ASGITransport` to call actual routes on
  the event loop, backed by a real (test) database and the real repository
  implementation — not FastAPI's synchronous `TestClient`, which spins up
  its own event loop per call and can mask a bug that only surfaces when
  something genuinely awaits alongside other work on the same loop.
- These catch wiring bugs that unit tests can't: a missing
  `Depends()` override, a serialization mismatch between the entity and
  the response schema, a route mounted at the wrong prefix.
- Keep this layer smaller than the unit layer — enough to cover each
  route's happy path and its key error responses (404, 422, 403), not
  every business-rule permutation (those belong in the service's unit
  tests).

### 3. Contract tests (Schemathesis, or the schema from `api-contract`) — do actual responses conform to the OpenAPI schema

- This is the layer that catches frontend/backend drift: it asserts that
  what the API actually returns matches its declared OpenAPI schema
  (types, required fields, status codes) — not just that the endpoint
  "works" for one example payload.
- If a sibling `api-contract` plugin's `contract-first` skill's schema is present, prefer running contract
  tests against the schema it generates/owns, so both sides of the
  contract are checked against the same source of truth. If not present,
  run against the FastAPI app's own generated schema via `app.openapi()` —
  in-memory, not the `/openapi.json` route, which `fastapi-project-bootstrap`
  disables by default outside `debug` mode.

Read `references/unit-and-integration.md` for worked Pytest examples of
layers 1 and 2, and `references/contract-testing.md` for a worked
Schemathesis example of layer 3.

## Shared fixtures

Copy `assets/conftest.py` into the project's test root (or merge it into
an existing `conftest.py`) rather than redefining `client`, `db_session`,
or fake repositories per module. Every module's test suite should import
these shared fixtures instead of hand-rolling its own test client or fake
repository setup. `client` is an `async` fixture, so every test that uses
it is `async def` — `pyproject.toml`'s `asyncio_mode = "auto"` means pytest
runs them with no per-test decorator needed.

## Workflow for "write tests for X"

1. If X is an entity or a service method with business rules → unit test,
   using a fake repository if a service is involved.
2. If X is a route → integration test with the async `client`, using the
   `client` and `db_session` fixtures from `assets/conftest.py`.
3. If the ask is "make sure frontend and backend agree" or "check nothing
   broke the API shape" → contract test against the OpenAPI schema.
4. Default to writing at the *lowest* layer that actually exercises the
   behavior in question — don't write an integration test for a pure
   business-rule check that a unit test on the service would cover just as
   well and much faster.
5. If X is "does this whole business workflow work end-to-end through the
   real UI", that's not this skill — see a sibling `e2e-testing` plugin's
   `playwright-test-design` skill to scope the workflow and
   `playwright-test-implementation` to write it; those tests should call
   this project's own API for setup/verification the same way
   `assets/conftest.py`'s `client` fixture does, rather than reinventing it.

## List the cases and get them confirmed before writing any test code

**A hard stop, not a suggestion.** Even when the request sounded like "just write
the tests", work out the cases using the workflow above, present them, and wait.

One line per case, grouped by layer, and say plainly what you're *not* covering:

```
Unit (fake repository)
  1. OrderService.submit rejects an order with no line items
  2. OrderService.submit applies the volume discount above 100 units
  3. Order.total sums line items and excludes cancelled ones

Integration (async client + test DB)
  4. POST /orders returns 201 and the order is actually persisted
  5. POST /orders returns 422 for a missing customer_id
  6. GET /orders/{id} returns 404 for another tenant's order

Contract
  7. the OpenAPI schema still matches the generated client's expectations

Not covered — say so explicitly
  - the payment provider call (external; needs a stub decision from you)
```

Then ask whether that's the right coverage, and adjust before writing anything.

**Why stop.** Which cases matter is a judgment call made by reading the code, and
code doesn't reveal intent — a branch can look important and be unreachable, or
look trivial and be the one carrying the business rule. Guess wrong and you get
tests that pass, look thorough, and assert the wrong thing: the most expensive
kind, because it buys false confidence and still has to be rewritten. A short
list is nearly free to correct now; seven test files are not.

The "not covered" line is often the most valuable part — it's where the user
finds out the case they actually cared about wasn't in scope.

**Keep it proportionate.** A list to react to, not a document to review. For one
genuinely trivial case, one line and a question is the whole gate.

This mirrors the gate a sibling `e2e-testing` plugin's `playwright-test-design`
skill applies at the top of the pyramid — same reasoning, lighter format, because
these tests are cheaper to write and correspondingly cheaper to get wrong.

---
_Last reviewed: 2026-08-17_
