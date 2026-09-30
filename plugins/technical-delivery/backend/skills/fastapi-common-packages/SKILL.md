---
name: fastapi-common-packages
description: >
  Standardizes on one vetted package per common backend need (ORM,
  migrations, auth, background jobs, logging, caching, HTTP client, rate
  limiting) instead of picking ad hoc per feature. Use when the user says
  things like "which package should I use for X", "add authentication",
  "add background jobs", "add logging", "add caching", "set up
  migrations", or "install a package for this".
---

# FastAPI Common Packages

Apply this skill whenever a feature needs a capability the standard library
doesn't provide — persistence, migrations, auth, background jobs, logging,
caching, outbound HTTP, or rate limiting. This codebase picks one package
per need up front so every module solves the same problem the same way,
rather than each feature branch reaching for whatever the author happened
to know.

## 1. Check before you add

Before recommending or installing anything, check `pyproject.toml` (or
`requirements.txt`) for a package that already covers the need. Don't
introduce a second package for a job an existing dependency already does —
e.g. if `httpx` is already a dependency, don't add `aiohttp` for a new
outbound call just because it's a different endpoint. If the codebase
already made a different (reasonable) choice than the table below, follow
the existing choice for consistency rather than mixing two libraries for
the same job.

## 2. The standard choice per need

- **ORM / database access** → **SQLAlchemy 2.0**. Async-capable, typed,
  and it's what the repository pattern from `fastapi-data-layer` is built
  against (`infra/repository.py` implementations wrap a SQLAlchemy
  session).
- **Migrations** → **Alembic**. Pairs with SQLAlchemy. Every schema
  change ships as an Alembic revision — never a hand-run `ALTER TABLE`
  against a live database, even for a "quick fix," because that leaves no
  record other environments can replay. Read
  `references/alembic-conventions.md` for the rules a revision itself
  needs to follow (static, reversible, named consistently) — this row is
  only about the package choice.
- **Settings/config** → **`pydantic-settings`'s `BaseSettings`**. Already
  the pattern `fastapi-project-bootstrap` sets up in `core/settings.py`;
  don't introduce `python-decouple` or a hand-rolled `os.environ` wrapper
  alongside it.
- **Auth**: two different needs, two different answers — don't reach for
  the heavier one by default.
  - The app owns its own users/passwords/sessions → **`fastapi-users`**,
    a full user-management + JWT auth solution.
  - The app only needs to verify JWTs issued by an external identity
    provider (Auth0, Cognito, an internal SSO service) → **`python-jose`**
    (or **`PyJWT`**) directly, just to validate signatures/claims. Don't
    pull in a full auth framework to do what a JWT-verification dependency
    already does in ten lines.
- **Background/async jobs** → **`arq`** by default: Redis-backed,
  async-native, and it fits an async FastAPI app without a second event
  loop model to reason about. Mention **Celery** only when the team is
  already standardized on it elsewhere — don't introduce Celery fresh into
  an async-first codebase.
- **Structured logging** → **`structlog`**, attached once at the
  middleware boundary (the observability pattern from
  `backend-architecture`) so every request gets structured, correlated log
  lines. Never sprinkle bare `print()` or ad hoc `logging.info(...)` calls
  inside services — that produces unstructured, unsearchable output with
  no request correlation.
- **Caching** → **`redis`**, accessed through a repository-like interface
  in `infra/` — the same pattern used for persistence. A service asks a
  cache interface for data; it doesn't know or care whether Redis,
  memcached, or something else is behind it. Don't call the Redis client
  directly from `service.py`.
- **HTTP client for outbound calls** → **`httpx`**, async-native. Never
  `requests` inside an async route or service — `requests` blocks the
  thread it runs on, and a blocking call inside an `async def` stalls the
  event loop for every other concurrent request (see
  `fastapi-best-practices`).
- **Rate limiting** → **`slowapi`**.

Read `references/package-decision-table.md` for install commands (`pip
install` / `uv add`) and a one-line "when NOT to use this" caveat for each
package above — use it when actually adding a dependency, not just naming
one.

## 3. How to apply this when asked "which package for X"

1. Map the request to one of the categories above (auth, caching, jobs,
   etc.) — most requests fit one category even if phrased differently
   ("add a job queue" and "process this in the background" both mean
   background/async jobs).
2. Check `pyproject.toml`/`requirements.txt` for an existing package
   already covering that category. If found, use it — don't relitigate the
   choice per feature.
3. If nothing covers it yet, recommend the standard choice from the table
   above, state the one-sentence reason from this file, and add it via the
   project's package manager (`uv add <package>` if a `uv.lock` exists,
   otherwise `pip install <package>` and update `pyproject.toml`).
4. For the auth category specifically, ask (or infer from the codebase)
   whether this app owns its users or only verifies externally-issued
   tokens before picking between `fastapi-users` and `python-jose` — this
   is the one category with a real branch, not a single default.

## 4. Don't relitigate an existing choice

If a project already uses, say, Celery for background jobs, don't propose
switching to `arq` mid-project just because it's the default in this
skill — the cost of running two job systems (or migrating a working one)
usually outweighs the marginal benefit. This skill's table is for green
field choices and for "which package should I add" when nothing exists
yet, not a mandate to migrate working infrastructure.

---
_Last reviewed: 2026-08-17_
