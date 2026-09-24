---
name: backend-architecture
description: >
  Applies the three-zone architecture model (core / modules / shared) to a FastAPI
  service so business domains stay isolated and layering stays clean, then routes
  the actual work to the right specialist skill. Use this skill when the user says
  "structure my backend", "where does this code belong", "set up the API
  architecture", "how should I organize this FastAPI project", or "which module
  does this belong in".
---

# Backend Architecture (FastAPI, three-zone model)

## Purpose

Give every FastAPI backend the same three-zone shape so business logic never
leaks into transport code and domains never import each other. This skill is
the foundation and orchestrator for the other 5 skills in this plugin — read
it first, decide what the user actually needs, then hand off.

## Step 0: Consult the codebase map first

If a sibling `codebase-map` plugin is installed, ask its `codebase-map-sync`
skill for cached facts about this repo before doing anything below yourself —
it already knows the stack and module list, refreshed cheaply via a
checkpoint rather than a full re-read. If that plugin isn't installed, fall
through to step 1's own live checks; nothing here requires it.

## Step 1: Detect the stack

Before applying anything, confirm this is a FastAPI project:

- Look for `fastapi` in `pyproject.toml` or `requirements.txt`.
- Look for a `main.py` / `app.py` that calls `FastAPI()`.

If FastAPI is not present but the user wants a new service, go straight to
the `fastapi-project-bootstrap` skill instead of guessing at conventions.

## Step 1a: Check for an existing structure that predates this plugin

If the project already has an existing `core/`/`modules/` split, or any
FastAPI app structure that wasn't scaffolded by this plugin, route to a
sibling `architecture-foundations` plugin's `existing-codebase-adoption`
skill first — it decides whether Kaizen's conventions or the existing
structure govern before the three-zone model below gets applied to anything.
If the project is genuinely greenfield (no existing app code), skip straight
to Step 2.

## Step 2: Apply the three-zone model

- **`core/`** — app bootstrap only: the `create_app()` / `FastAPI()` factory,
  settings, the DI container, middleware, and global exception handlers.
  `core/` is imported only by the entrypoint (`main.py`) and by modules that
  need shared infrastructure (e.g. a DB session provider) — modules are never
  imported by `core/`.
- **`modules/`** — one folder per business domain (e.g. `modules/products/`,
  `modules/orders/`). Modules never import each other. Each module has the
  same five-piece internal shape:
  - `domain/` — `entity.py` (a framework-free business object with methods
    and invariants) and `exceptions.py` (domain-specific errors).
  - `schemas/` — request/response Pydantic DTOs. Ideally these are generated
    from a sibling `api-contract` plugin's `contract-first` skill's schema rather than hand-written,
    so the wire format stays in lockstep with the frontend.
  - `service.py` — business logic and orchestration. This is the *only*
    thing routes call.
  - `infra/` — `repository.py`, the persistence implementation. It
    implements an interface the domain layer declares (dependency
    inversion), so swapping databases never touches `service.py`.
  - `api/` — `routes.py`, thin path operations that parse input, call the
    service, and return its result.
  - `dependencies.py` — the module's own DI wiring (its `Depends()`
    providers).
- **`shared/`** — reusable code with zero business logic: generic
  pagination helpers, base exception types, common utility functions.
  Anything domain-specific does not belong here.

Layering rule inside a module: **`api → service → domain`**, with `infra`
implementing an interface `domain` declares. `api` never imports `infra`
directly — it only ever talks to `service.py`.

Read `references/backend-layering.md` for the full example folder tree and
a dependency-flow diagram before generating or reviewing a structure.

## Step 3: Know the entity/DTO/persistence-model boundary

A recurring point of confusion is what goes in `domain/entity.py` vs
`schemas/` vs an ORM model in `infra/`. Read
`references/domain-vs-infra-boundary.md` for the decision rule before
telling a user where a given class belongs.

## Step 4: Route to the right skill

This skill only decides *where things go*. Once you know what the user
actually wants to build, hand off:

| User intent | Skill to use |
|---|---|
| Scaffolding a brand-new domain/module | `fastapi-module-scaffold` |
| Adding an endpoint, a repository, or wiring DI | `fastapi-data-layer` |
| Exposing, versioning, or protecting routes | `fastapi-routing` |
| Writing unit/integration/contract tests | `fastapi-testing` |
| Starting a new project from scratch | `fastapi-project-bootstrap` |

Read `references/adapter-map.md` for the expanded version of this table
(with trigger phrases and rationale) when the intent is ambiguous.

If a sibling `architecture-foundations` plugin's `existing-codebase-adoption`
skill recorded `"existing"` for this project, don't apply
`fastapi-module-scaffold`'s five-folder skeleton or `fastapi-naming-conventions`'
rules verbatim — read the project's current module/file organization first
and match it instead. `fastapi-best-practices` and `fastapi-testing`'s
pyramid shape still apply regardless, since they're correctness concerns,
not folder/file shape.

## Note: there is no "module context" skill, and that's intentional

A sibling `frontend` plugin's `react-module-context` skill covers locating UI state.
Backend requests are stateless, so the equivalent concerns are already
solved by FastAPI's own request-scoped `Depends()` injection:

- Function arguments = the "props" equivalent (data passed explicitly into
  a call).
- Request-scoped `Depends()` = the "module-context" equivalent (state
  local to one request, resolved fresh per call).
- App-wide state/cache (e.g. a singleton in the DI container) = the "store"
  equivalent.

Do not invent a sixth skill to fill this gap — there isn't one. If a user
asks "what's the backend equivalent of module context", explain the mapping
above and point them at `fastapi-data-layer` for DI patterns.

---
_Last reviewed: 2026-08-17_
