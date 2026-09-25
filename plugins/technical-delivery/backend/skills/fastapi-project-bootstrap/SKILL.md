---
name: fastapi-project-bootstrap
description: >
  Stands up a greenfield FastAPI project with the app-factory pattern,
  env-driven settings, and the dependency baseline the rest of this
  plugin's skills assume. Use this skill when the user says "new FastAPI
  project", "set up the backend", "configure the project", or "start a new
  service from scratch".
---

# FastAPI Project Bootstrap

## Purpose

Stand up a new FastAPI service with the exact conventions
`backend-architecture`, `fastapi-module-scaffold`, `fastapi-data-layer`,
`fastapi-routing`, and `fastapi-testing` all assume already exist. One
relevant rule from `backend-architecture`: `core/` holds the app
bootstrap (factory, settings, DI, middleware, exception handlers) and is
imported only by the entrypoint — nothing here should require a
`modules/` folder to exist yet, but the structure should make adding one
trivial.

## Step 1: Confirm this is actually greenfield

Check for an existing `pyproject.toml`/`requirements.txt` with `fastapi`
already listed, or an existing `core/`/`modules/` split. If either exists,
this is not a bootstrap task — hand off to `backend-architecture`, which
routes to a sibling `architecture-foundations` plugin's
`existing-codebase-adoption` skill from there to decide whether Kaizen's
conventions or the project's existing structure govern before any
scaffolding happens.

## Step 2: Lay down the base project structure

```
app/
├── main.py              # entrypoint — calls create_app()
├── core/
│   ├── __init__.py
│   ├── app.py           # create_app() factory
│   ├── config.py        # Settings (Pydantic BaseSettings)
│   ├── database.py      # engine, SessionLocal, get_db_session, Base
│   └── exception_handlers.py
├── modules/             # empty to start; fastapi-module-scaffold fills this in
└── shared/
    └── __init__.py
tests/
└── conftest.py          # copy from fastapi-testing's assets/conftest.py
pyproject.toml
.env.example
```

## Step 3: Write the starter files

Copy these assets into the new project, adjusting the project name and
any obviously project-specific values (DB URL, app title) as needed —
don't regenerate them from scratch:

- `assets/pyproject.toml` — dependency baseline: FastAPI, Pydantic v2,
  SQLAlchemy, Uvicorn, Pytest, pytest-asyncio, httpx, Schemathesis, and
  Ruff (linting + formatting, configured in the same file). Copy to the
  project root as `pyproject.toml`.
- `assets/settings.py` — env-driven config, split into one `BaseSettings`
  class per domain (`AppSettings`, `DatabaseSettings`, `CORSSettings`,
  `AuthSettings`) composed into one `Settings`, rather than a single flat
  class — see `fastapi-naming-conventions` for why. Copy to
  `app/core/config.py`.
- `assets/app.py` — the `create_app()` factory: builds the `FastAPI()`
  instance with `/docs`/`/redoc`/`/openapi.json` gated behind `debug`
  (off unless `debug=True`, so a production-configured instance never
  exposes them), registers exception handlers, and includes routers (empty
  list to start, ready for `fastapi-module-scaffold` to add to). Copy to
  `app/core/app.py`.

## Step 4: Write a minimal `main.py`

```python
# main.py
from app.core.app import create_app

app = create_app()
```

Run with `uvicorn main:app --reload` for local development.

## Step 5: Set up `.env` and dependencies

- Copy `.env.example` alongside `pyproject.toml` listing every setting
  field across all four settings classes in `assets/settings.py` (e.g.
  `APP_NAME=`, `DEBUG=true`, `DATABASE_URL=`, `CORS_ORIGINS=`,
  `JWT_SECRET=`, `JWT_ALGORITHM=`) with placeholder values — never commit
  a real `.env`. Each domain class reads the same flat env var names it
  always did; splitting the classes didn't change how a value is supplied,
  only where it's declared.
- Run `pip install -e .` (or the project's package manager equivalent) to
  install the dependency baseline from `pyproject.toml`.

## Step 6: Verify and hand off

Once every file above is in place, **ask before running anything** — don't start
a server or an install unprompted. A sibling `architecture-foundations` plugin's
`working-agreement` skill covers why verification is batched and asked for; if
that plugin isn't installed, the rule still stands on its own here.

- Confirm `uvicorn main:app --reload` starts without error. `/docs` only
  loads when `debug=True` (`assets/app.py` gates it deliberately — see
  Step 3) — set `DEBUG=true` in the local `.env` before checking it, and
  leave it `false` for anything resembling a production config.
- Copy `fastapi-testing`'s `assets/conftest.py` into `tests/conftest.py`
  so the test baseline is in place from day one.
- Once the skeleton runs, hand off to `fastapi-module-scaffold` for the
  first real domain module — this skill's job ends at a running, empty
  service.

---
_Last reviewed: 2026-08-17_
