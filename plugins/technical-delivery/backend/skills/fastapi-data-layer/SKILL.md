---
name: fastapi-data-layer
description: >
  Places persistence access behind a domain-declared repository interface,
  keeps business orchestration in a service that routes call, and wires
  dependency injection so repositories and services resolve cleanly. Use
  this skill when the user says "add an endpoint", "add a repository",
  "wire up the database", "dependency injection", "business logic goes
  where", or "how do I connect this route to the database".
---

# FastAPI Data Layer (repository, service, DI)

## Purpose

Answer, concretely, "where does this piece of logic go, and how does it
get to the route": persistence goes in a repository, orchestration goes in
a service, and both get to the route through `Depends()`. One relevant
rule from `backend-architecture`: `infra` implements an interface `domain`
declares (dependency inversion) — `api` never imports `infra` directly.

## 0. Consult the codebase map first

If a sibling `codebase-map` plugin is installed, ask its `codebase-map-sync`
skill for cached facts about this repo — which modules already have a
repository/service/DI wiring in place, and what pattern they follow —
before adding a new one. If that plugin isn't installed, look at one
existing module's `infra/repository.py`, `service.py`, and
`dependencies.py` directly instead of assuming this skill's generic
examples match the project's actual conventions.

## The three pieces

### 1. Repository — persistence, behind an interface

Define the interface in `domain/` (as a `Protocol`) so the domain layer
owns the contract, and implement it in `infra/repository.py`. This is what
lets you swap databases, or swap in a fake for tests, without touching
`service.py`.

Read `references/repository-pattern.md` for the full
`ProductRepository` Protocol and `SqlAlchemyProductRepository`
implementation before writing a new repository — copy its shape rather
than inventing a new one.

### 2. Service — business rules/orchestration, the only thing routes call

`service.py` takes its repository via constructor injection, exposes one
method per use case, and is the *only* thing `api/routes.py` calls.
Repositories, ORM sessions, and other modules' services should never be
called directly from a route.

Read `references/service-layer-patterns.md` for the full `ProductService`
example (`create_product`, `list_products`) — note how it converts between
entities and response schemas (`ProductResponse.model_validate(...)`) at
its boundary, and where it would raise a domain exception on an invariant
violation rather than an `HTTPException` (HTTP concerns stay in `api/` and
the global exception handlers, not in the service).

### 3. Schemas — request/response shape

Request/response shape is defined via Pydantic schemas in `schemas/`,
ideally imported from `api-contract`-generated types so the wire format
matches what the frontend expects byte-for-byte. If no such generated
types are available, hand-write minimal `BaseModel` classes with only
shape/format validation — no business rules.

Read `references/schema-conventions.md` for what "shape/format validation"
should actually lean on (Pydantic's own built-in validators, not hand-rolled
`if` checks) and the shared base model every schema inherits from.

### 4. Dependency injection — how it all reaches the route

`dependencies.py` (or a shared `core/container.py` for larger apps) is
where `Depends()` providers live: a provider builds a repository from a DB
session, then builds a service from that repository, and the route depends
on the service provider only — never on the repository or session
directly.

Read `references/dependency-injection.md` for the full
`get_product_service` provider, the app-wide `get_db_session` provider it
depends on, and guidance on when to introduce a centralized `Container`
class instead of scattering ad hoc `Depends()` chains across modules.

## Workflow for a typical request ("add an endpoint that needs the DB")

1. Check whether a repository interface already exists in this module's
   `domain/`. If not, define one (see `repository-pattern.md`).
2. Check whether the concrete implementation exists in `infra/repository.py`.
   If not, implement it against the project's actual persistence layer
   (SQLAlchemy, or whatever the project already uses — don't introduce a
   new ORM).
3. Add or extend the method on `service.py` that the new endpoint needs.
   The service method should take/return domain entities or schemas, never
   raw ORM rows.
4. Add or extend the `Depends()` provider in `dependencies.py` if a new
   service method needs new inputs.
5. Only then write the route in `api/routes.py` (or hand off to
   `fastapi-routing` if the endpoint also needs auth/versioning concerns).

## Larger apps: consider a `Container`

When a project has many modules and `Depends()` chains start repeating the
same session-to-repository-to-service wiring, centralize provider
registration in a `Container` class in `core/container.py` instead of
duplicating that chain in every module's `dependencies.py`. Keep this as a
later refactor, not a day-one requirement — a handful of modules is fine
with per-module `dependencies.py` files.

---
_Last reviewed: 2026-08-17_
