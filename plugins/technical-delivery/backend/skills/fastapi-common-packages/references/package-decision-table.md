# Package decision table

Full install commands and "when NOT to use this" caveats for each standard
choice in `SKILL.md`. Check `pyproject.toml`/`requirements.txt` first —
this table is for adding a package that isn't already present.

| Need | Package | Install (`uv`) | Install (`pip`) | When NOT to use this |
|---|---|---|---|---|
| ORM / database access | SQLAlchemy 2.0 | `uv add "sqlalchemy[asyncio]"` | `pip install "sqlalchemy[asyncio]"` | The project genuinely needs a document store with no relational shape at all (then a Mongo driver behind the same repository interface is fine — the pattern still applies, just not SQLAlchemy). |
| Migrations | Alembic | `uv add alembic` | `pip install alembic` | Don't add this without SQLAlchemy already present — Alembic assumes a SQLAlchemy `MetaData`/engine to diff against. |
| Settings/config | pydantic-settings | `uv add pydantic-settings` | `pip install pydantic-settings` | Never skip this in favor of a bare `os.environ` wrapper — you lose validation, type coercion, and a single source of truth for what settings exist. |
| Auth (app owns users) | fastapi-users | `uv add "fastapi-users[sqlalchemy]"` | `pip install "fastapi-users[sqlalchemy]"` | The app doesn't manage its own users at all (SSO/external IdP only) — this is overkill; use the JWT-verification-only option instead. |
| Auth (verify external JWTs) | python-jose (or PyJWT) | `uv add "python-jose[cryptography]"` | `pip install "python-jose[cryptography]"` | The app needs full user registration, password reset flows, or session management — that's `fastapi-users`, not a bare JWT verifier. |
| Background/async jobs | arq | `uv add arq` | `pip install arq` | The team already runs Celery in production for other services — don't introduce a second job runner; extend the existing Celery setup instead. |
| Background/async jobs (alternative) | Celery | `uv add celery` | `pip install celery` | The codebase is async-first and Celery isn't already standardized on — prefer `arq` for a new async FastAPI service. |
| Structured logging | structlog | `uv add structlog` | `pip install structlog` | A tiny script or one-off tool with no request/response cycle to correlate — plain `logging` may be fine there, but not inside the FastAPI app itself. |
| Caching | redis (redis-py, async client) | `uv add "redis[hiredis]"` | `pip install "redis[hiredis]"` | The data being cached is small enough and per-process (no cross-instance sharing needed) — an in-process LRU cache (`functools.lru_cache` or `cachetools`) may be simpler; reach for Redis once caching needs to be shared across instances or survive a restart. |
| HTTP client (outbound calls) | httpx | `uv add httpx` | `pip install httpx` | Never use `requests` in an async route or service — it's a blocking call that stalls the event loop. `httpx` also has a sync client if a genuinely synchronous script (not inside the app) needs one. |
| Rate limiting | slowapi | `uv add slowapi` | `pip install slowapi` | Rate limiting needs to be enforced across multiple app instances with strict global limits — `slowapi`'s default in-memory/Redis-backed limiter may need additional configuration; for very strict global limits consider an API-gateway-level limiter instead of (or in addition to) application-level limiting. |

## Applying a choice

1. Confirm the package isn't already a dependency under a different name
   (e.g. `aiohttp` already present when considering `httpx` — don't add
   both for outbound HTTP).
2. Add it with the project's existing package manager convention: if a
   `uv.lock` file exists, use `uv add`; otherwise use `pip install` and add
   the pin to `pyproject.toml`/`requirements.txt` directly.
3. For anything touching persistence (SQLAlchemy, Alembic, redis), wire it
   through the `infra/` layer per `fastapi-data-layer` — never import the
   raw client directly into `service.py`.
