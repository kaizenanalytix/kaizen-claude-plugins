---
name: fastapi-best-practices
description: >
  Reviews a FastAPI endpoint or service against a concrete, opinionated
  checklist — blocking calls in async code, N+1 queries, response models,
  Pydantic v2 patterns, DI scope, error handling, and pagination. Use when
  the user says things like "review this endpoint/service", "is this good
  FastAPI", "FastAPI best practices", "why is this endpoint slow", or
  "async issue".
---

# FastAPI Best Practices

Apply this skill when reviewing a route or service, diagnosing a slow or
misbehaving endpoint, or asked generally whether some FastAPI code is
"good." This is a checklist of concrete rules to check against, not a
tutorial — walk the code against each item below and call out violations
by name.

## 1. Never block the event loop

Never call a blocking/synchronous library from an `async def` route or
dependency — a blocking DB driver, `requests`, `time.sleep`. A blocking
call inside an `async def` doesn't just slow down that one request; it
stalls the entire event loop, so every other concurrent request queued
behind it stalls too. Fix it one of two ways: swap in an async-native
library (`httpx` instead of `requests`, an async DB driver via SQLAlchemy's
async engine), or, if no async version exists, run the blocking call in a
thread pool via `run_in_threadpool` so it doesn't block the loop.

**This only applies to I/O-bound blocking calls.** For CPU-intensive work
(image processing, heavy computation, anything that keeps the CPU busy
rather than waiting on a socket or disk), neither fix above helps — Python's
GIL means a thread pool doesn't give you real parallelism for CPU-bound
code, so `run_in_threadpool` just moves the stall to a worker thread instead
of removing it. Route CPU-bound work to a separate process instead:
multiprocessing, or a task queue (see rule 11) whose workers run in their
own process.

## 2. Avoid N+1 queries

When a service needs related data for a list of entities (e.g. each
`Product` needs its `Category`), load it with a single query using
SQLAlchemy's `selectinload`/`joinedload` — never loop over the list and
issue one query per row. A list endpoint that works fine with 10 rows in
dev and falls over with 10,000 in production is almost always this
pattern.

## 3. Always set a response model

Set `response_model=` on a route (or rely on the return-type annotation
under Pydantic v2) so FastAPI validates and filters the outgoing shape.
Never return a raw ORM object or a bare `dict` and hope the shape happens
to match the contract — without a declared response model, an accidental
extra field (or a missing one) ships silently and nothing catches it
until a consumer breaks.

One cost worth knowing, not a reason to skip this: FastAPI builds the
Pydantic model twice per response — once from whatever the route returns,
then again to validate/filter it against `response_model`. This is the
correct trade for the safety it buys, but it's why an unnecessarily large
or deeply nested `response_model` on a hot endpoint shows up in profiling —
the fix there is trimming the model to what the endpoint actually needs to
return, not dropping the response model.

## 4. Use Pydantic v2 patterns, not v1 holdovers

- `model_validate(obj)` — not the v1 `Model.from_orm(obj)`.
- `model_dump()` — not the v1 `.dict()`.
- `Field(...)` constraints (`gt=`, `max_length=`, etc.) for validation —
  not a manual `if` check re-implementing what `Field` already does inside
  a route or service.

**This is about not re-implementing what `Field` already does — it is not
a rule against `field_validator` itself.** A `field_validator` that raises
`ValueError` is the correct, encouraged way to surface a detailed 422 for a
constraint `Field(...)` genuinely can't express: a check against another
field's value, or one that requires a DB/external lookup. The anti-pattern
in `references/anti-patterns.md` is specifically a validator re-deriving a
bound `Field(gt=0)` already covers — don't read it more broadly than that.

## 5. DI-provided sessions are request-scoped

A `Depends()`-provided DB session must be created fresh per request and
closed after the request completes. Never share a module-level global
session across requests — under concurrent load this causes cross-request
data leakage and connection-state corruption, since two requests end up
reading/writing through the same session object at once.

## 6. Raise domain exceptions, translate once

Raise domain exceptions from the service layer (`ProductNotFoundError`,
per `fastapi-naming-conventions`) and translate them to HTTP responses in
exactly one place — an exception handler registered in `core/app.py`.
Never scatter `raise HTTPException(...)` calls inside service methods:
that couples business logic to the HTTP layer and means the same service
can't be reused from, say, a CLI command or a background job without
carrying HTTP concerns into it.

## 7. Keep business logic out of routes

A route does three things: parse the request, call exactly one service
method, return the result. Any `if`/business-rule logic living directly
in `api/routes.py` is a sign it belongs in `service.py` instead — a route
should read as a thin translation layer, not a place where decisions get
made.

## 8. Paginate anything unbounded

Any list endpoint whose result set can grow without bound needs
pagination — limit/offset or cursor-based — from the day it ships.
Retrofitting pagination onto an endpoint that shipped without it is a
breaking API change for every existing consumer, so this isn't an
optimization to defer.

## 9. Idempotency

A `POST` that creates a resource is expected to be non-idempotent (two
identical calls create two resources) — that's fine and doesn't need
fixing. A `PUT`/`PATCH`, though, should genuinely be idempotent: calling it
twice with the same body should leave the resource in the same state as
calling it once. Don't design a "PUT" that actually appends or
increments each time it's called — that's a `POST` wearing a `PUT`'s
verb.

## 10. Hide interactive docs outside development

`/docs`, `/redoc`, and `/openapi.json` are useful while building the API and
a liability once it's running somewhere real — they hand anyone who finds
the URL a complete map of every endpoint, parameter, and schema.
`fastapi-project-bootstrap`'s `app.py` gates all three behind `debug`, off
by default; flag it as a finding if you see an app that always constructs
`FastAPI()` with docs enabled regardless of environment.

## 11. `BackgroundTasks` vs. a real task queue

FastAPI's `BackgroundTasks` runs a function after the response is sent, in
the same process — fine for a quick, no-retry side effect (send a
confirmation email, write an audit log entry). It is the wrong tool the
moment the work needs a retry policy, scheduling, or to survive the process
restarting: a `BackgroundTasks` job that's mid-flight when the app
redeploys is simply lost. That's the line for reaching for a real
broker-backed queue instead — `fastapi-common-packages` recommends `arq`
by default for this, so route the package choice there; this rule is only
about which one the situation calls for.

## 12. Reference file

Read `references/anti-patterns.md` for a bad/good code snippet for each
rule above — use it to produce concrete before/after examples in a review
rather than describing the fix abstractly.

---
_Last reviewed: 2026-08-17_
