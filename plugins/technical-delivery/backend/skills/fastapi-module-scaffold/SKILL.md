---
name: fastapi-module-scaffold
description: >
  Scaffolds a new business-domain module under modules/<name>/ with the
  standard five-folder skeleton (domain, schemas, service, infra, api,
  dependencies) and wires it into the app's router and DI container. Use
  this skill when the user says "add a module", "new feature", "new
  domain", "scaffold the X module", or "create a module for Y".
---

# FastAPI Module Scaffold

## Purpose

Every business domain in the backend gets the same module shape, so that
switching between domains is never a surprise. This skill creates that
shape and wires it in — it does not decide *whether* something belongs in
its own module (that's `backend-architecture`) or write the actual business
logic beyond a minimal working example.

One relevant rule from `backend-architecture` before you start: `modules/`
holds one folder per business domain, modules never import each other, and
inside a module the flow is `api → service → domain`, with `infra`
implementing an interface `domain` declares.

## Step 0: Consult the codebase map first

If a sibling `codebase-map` plugin is installed, ask its `codebase-map-sync`
skill for cached facts about this repo — the existing module list and the
naming convention actually in use — before naming and scaffolding a new
one. If that plugin isn't installed, do the equivalent live: look at one
existing module under `modules/` directly before creating the new one.

## Step 1: Confirm the module name and location

- The module folder is `modules/<name>/` where `<name>` is a plural,
  lowercase, snake_case noun for the domain (e.g. `products`, `orders`,
  `invoices`) — match whatever convention the existing `modules/` folder
  already uses if one exists.
- If `modules/` doesn't exist yet, this is likely a greenfield project —
  check whether `fastapi-project-bootstrap` should run first.

## Step 2: Create the five-folder skeleton

Under `modules/<name>/`, create:

```
modules/<name>/
├── domain/
│   ├── __init__.py
│   ├── entity.py        # framework-free entity + invariants
│   └── exceptions.py     # domain-specific exceptions
├── schemas/
│   ├── __init__.py
│   ├── requests.py       # Create<Name>Request, Update<Name>Request
│   └── responses.py      # <Name>Response
├── infra/
│   ├── __init__.py
│   ├── models.py          # ORM model (if using a DB)
│   └── repository.py      # implements the domain-declared interface
├── api/
│   ├── __init__.py
│   └── routes.py           # APIRouter + thin path operations
├── __init__.py
├── dependencies.py         # DI providers for this module
└── service.py              # business logic/orchestration
```

Read `references/module-template.md` for the exact starter code to use for
`domain/entity.py` and `api/routes.py` — copy it and adapt the entity name,
fields, and business method to the domain being scaffolded. Follow the same
pattern (Protocol-based repository interface, service taking the repository
via constructor injection, thin route handlers) for `schemas/`, `service.py`,
`infra/repository.py`, and `dependencies.py` — see the `fastapi-data-layer`
skill for the fuller versions of those files if the user needs more than
the minimal skeleton.

**All seven files above are created every time — none are conditional on
whether the module "needs" them.** This is a deliberate divergence from
looser "create only the files a module actually uses" conventions some
FastAPI guidance recommends: the domain/infra split is what makes the
repository-interface pattern (`fastapi-data-layer`) and fake-repository unit
testing (`fastapi-testing`) possible at all, and that only works if every
module keeps the same shape. A module that skips `domain/` because "it's
simple" has nowhere for `fastapi-testing`'s fake-repository pattern to
attach later, and inconsistent module shapes are exactly what this skill
exists to prevent. Create all seven every time, even when one starts out
nearly empty.

## Step 3: Wire the module into the app

Two wiring points, both in `core/`:

1. **`core/app.py`** — import the module's router and include it:
   ```python
   from app.modules.products.api.routes import router as products_router
   app.include_router(products_router, prefix="/api/v1")
   ```
   (See `fastapi-routing` for prefix/versioning conventions.)

2. **`core/container.py`** — register the module's repository and service
   providers so they're available for `Depends()` resolution app-wide, if
   the project centralizes DI in a container rather than scattering
   `Depends()` chains directly in `dependencies.py`. If the project has no
   container yet, a plain `dependencies.py` with `Depends()` functions is
   fine — don't introduce a container just for one module.

## Step 4: Sanity-check module isolation

Before finishing, verify:

- Nothing in the new module imports from another module's `domain/`,
  `infra/`, or `service.py`.
- `api/routes.py` imports only from `service.py`, `schemas/`, and
  `dependencies.py` — never from `infra/` directly.
- `domain/entity.py` has no FastAPI, Pydantic, or SQLAlchemy imports.

If the user also needs an authenticated route, a real repository
implementation, or tests for the new module, hand off to `fastapi-routing`,
`fastapi-data-layer`, or `fastapi-testing` respectively rather than trying
to cover those in this scaffold.

---
_Last reviewed: 2026-08-17_
