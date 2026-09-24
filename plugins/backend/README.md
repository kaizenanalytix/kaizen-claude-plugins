# backend

Tier 2 plugin for building clean-architecture backends with the same
domain-module discipline as a sibling `frontend` plugin. Ships one deep
adapter (FastAPI, the `fastapi-*` skills) and four thin ones
(`nodejs-architecture`, `nestjs-architecture`, `django-architecture`,
`java-kotlin-architecture` — stack detection and zone routing only, no
specialist depth yet).

## Overview

This plugin teaches Claude how to structure, scaffold, and extend a FastAPI
service using a three-zone module architecture, a domain/service/repository
split with dependency injection, routing/versioning conventions, a full test
pyramid including contract tests, standard package choices, and naming and
best-practice conventions.

It conceptually depends on a sibling `architecture-foundations` plugin (the
three-zone model and test-pyramid philosophy, its `existing-codebase-adoption`
skill — decides Kaizen-vs-existing conventions before any structural skill
below applies to a non-greenfield project — and the `contract-first` skill's
generated schemas) but every skill here works standalone — it restates the one
relevant rule in a single sentence rather than assuming that plugin's files
are physically present. `backend-architecture` also optionally consults a
sibling `codebase-map` plugin for cached, checkpointed codebase facts before
doing its own live stack detection, if that plugin is installed.

## Layout

```
skills/
├── backend-architecture/        # foundation/orchestrator — applies the three-zone model, routes below
├── fastapi-module-scaffold/    # ─┐
├── fastapi-data-layer/          # │
├── fastapi-routing/             # │
├── fastapi-testing/             # ├─ FastAPI adapter — everything FastAPI-specific
├── fastapi-project-bootstrap/   # │
├── fastapi-naming-conventions/  # │
├── fastapi-common-packages/     # │
├── fastapi-best-practices/     # ─┘
├── nodejs-architecture/         #  ─ thin adapter — stack detection + zone routing only
├── nestjs-architecture/         #  ─ thin adapter — stack detection + zone routing only
├── django-architecture/         #  ─ thin adapter — stack detection + zone routing only
└── java-kotlin-architecture/   #  ─ thin adapter — stack detection + zone routing only
```

Skills are grouped by name prefix, not by folder. Every skill sits directly at
`skills/<name>/SKILL.md`, which is the only depth Claude Code discovers: a
skill nested one level deeper (e.g. `skills/fastapi/fastapi-testing/`) still
auto-triggers off its `description`, but loses its namespaced
`/backend:<skill>` invocation form entirely. Keep this layout flat — if a
future adapter (`django/`, `litestar/`) is added, distinguish it by prefix
(`django-module-scaffold`) rather than by directory.

## Components

| Skill | Purpose |
|---|---|
| `backend-architecture` | Applies the three-zone model to a service/API app and routes to the adapter skills below. Gates on a sibling `architecture-foundations` plugin's `existing-codebase-adoption` skill first, on a non-greenfield project. |
| `fastapi-module-scaffold` | Scaffolds a new business-domain module (domain/schemas/service/infra/api) and wires it in. All seven files are created every time, deliberately — never conditional on what a module "needs". |
| `fastapi-data-layer` | Domain/service/repository split plus dependency-injection wiring: per-request dependency caching, SQL-first query design, and a shared Pydantic base model/validation conventions for schemas. |
| `fastapi-routing` | Per-module routers, versioning, auth, and route protection — including consistent path-parameter naming across routes so a validation dependency can be reused instead of re-implemented per route. |
| `fastapi-testing` | Pytest unit/integration tests (async `httpx` client over ASGI, not the sync `TestClient`) plus contract tests against the OpenAPI schema, with real auth headers injected into every generated case — including a documented pattern for backends whose auth is enforced by request-signing middleware rather than `Depends()`. Lists the intended cases in plain language and waits for confirmation before writing any test code. |
| `fastapi-project-bootstrap` | Greenfield FastAPI project setup — per-domain settings classes, docs hidden outside `debug`, and a Ruff lint/format baseline. |
| `fastapi-naming-conventions` | File/class/function naming standards for every module subfolder, plus database table/column/constraint naming. |
| `fastapi-common-packages` | Standard package choices for auth, jobs, logging, caching, HTTP, rate limiting — plus the conventions a migration itself must follow (static, reversible, consistently named) once Alembic is the choice. |
| `fastapi-best-practices` | Async/blocking pitfalls (including why CPU-bound work needs a process, not a threadpool), N+1 queries, response models, DI scope, thin routes, hiding docs outside development, and `BackgroundTasks` vs. a real task queue. |
| `nodejs-architecture` | Thin adapter for a generic Node.js backend (Express/Fastify, not NestJS): stack detection, greenfield/existing routing, and the three-zone model in Node vocabulary. No naming/data-layer/testing/bootstrap skills yet — asks rather than invents. |
| `nestjs-architecture` | Thin NestJS adapter: stack detection, greenfield/existing routing, and the three-zone model mapped onto Nest's own module/DI system, which already mirrors it closely. No naming/data-layer/testing/bootstrap skills yet — asks rather than invents. |
| `django-architecture` | Thin Django adapter: stack detection, greenfield/existing routing, and the three-zone model mapped onto Django's app-based structure. No naming/data-layer/testing/bootstrap skills yet — asks rather than invents. |
| `java-kotlin-architecture` | Thin adapter for a JVM backend (Java or Kotlin, typically Spring Boot): stack detection, greenfield/existing routing, and the three-zone model in Spring vocabulary. No naming/data-layer/testing/bootstrap skills yet — asks rather than invents. |

## Setup

Python 3.11+ and a FastAPI project (or create one via `fastapi-project-bootstrap`).

## Usage

- "Structure my backend" / "where does this code belong" → `backend-architecture`
- "This project already has a backend" / "should I follow this repo's conventions or Kaizen's" → a sibling `architecture-foundations` plugin's `existing-codebase-adoption` skill, gated via `backend-architecture`
- "Add a new products module" → `fastapi-module-scaffold`
- "Add an endpoint" / "wire up the database" → `fastapi-data-layer`
- "Add a route" / "protect an endpoint" / "version the API" → `fastapi-routing`
- "Write tests for this service/route" → `fastapi-testing`
- "Set up a new FastAPI project" → `fastapi-project-bootstrap`
- "What should I name this file/service/repository?" → `fastapi-naming-conventions`
- "Which package should I use for auth/jobs/logging?" → `fastapi-common-packages`
- "Review this endpoint" / "why is this slow" → `fastapi-best-practices`
- "Structure my Node backend" / "where does this Express/Fastify code belong" → `nodejs-architecture`
- "Structure my NestJS app" / "where does this Nest module belong" → `nestjs-architecture`
- "Structure my Django app" / "where does this Django code belong" → `django-architecture`
- "Structure my Spring Boot app" / "where does this Java/Kotlin backend code belong" → `java-kotlin-architecture`
