---
name: fastapi-naming-conventions
description: >
  Applies a concrete file- and identifier-naming standard for a FastAPI
  module's domain/schemas/service/infra/api/dependencies layers. Use when the
  user says things like "what should I name this file", "naming
  convention", "file naming", "how do I name this endpoint/service/
  repository", or "what case should this be".
---

# FastAPI Naming Conventions

Apply this skill whenever a file, folder, or identifier needs a name inside
`modules/<domain>/` or `core/`. One sentence of the model this depends on:
the five-folder module skeleton from `fastapi-module-scaffold`
(domain/schemas/service/infra/api/dependencies) — this skill only covers what
to *call* the files and classes inside it, not the folder structure itself.

## 1. The core rule: name by role, not by guesswork

Every identifier's name encodes its role in the layer it lives in — an
entity is a bare noun, an exception ends in `Error`, a schema ends in
`Request`/`Response`, a service ends in `Service`, and so on. Never invent a
one-off name that skips the suffix for a category that has one; a reader
should be able to tell what something is from its name alone, without
opening the file.

## 2. Category-by-category rules

- **Domain entities** (`domain/entity.py`): PascalCase, bare noun —
  `Product`. Never prefix with `I` and never suffix with `Entity`
  (`IProduct`, `ProductEntity` are both wrong) — `domain/` is the one place
  in the module where the type *is* the concept, so it needs no
  qualifier.
- **Domain exceptions** (`domain/exceptions.py`): PascalCase, suffixed
  `Error` — `ProductNotFoundError`, `InsufficientStockError`. These are
  raised from `service.py`, never from `api/routes.py` directly — see
  `fastapi-best-practices` for why.
- **Pydantic schemas** (`schemas.py`): PascalCase, suffixed by intent —
  `CreateProductRequest`, `UpdateProductRequest`, `ProductResponse`. Never
  reuse one schema class for both a request and the response, even when
  today's fields happen to match — a request and a response diverge over
  time (a response gains `id`/`created_at`, a request gains
  write-only fields), and collapsing them now just means a painful split
  later. One schema class, one direction.
- **Service classes** (`service.py`, singular — never `services.py`):
  PascalCase, suffixed `Service` — `ProductService`. One service class per
  domain module.
- **Repository interface + implementation** (`infra/repository.py`): the
  interface itself carries no prefix and is a `Protocol` —
  `ProductRepository`. Each concrete implementation is prefixed by its
  technology so multiple implementations can coexist side by side:
  `SqlAlchemyProductRepository`, `MongoProductRepository`. Never name the
  interface `IProductRepository` or `AbstractProductRepository`, and never
  name a concrete implementation just `ProductRepositoryImpl`.
- **Routers** (`api/routes.py`, always this name — plural, never
  singular `route.py` and never mixed with `routers.py` elsewhere in the
  codebase): a single snake_case module-level variable named `router`.
  Route path constants, if extracted out of inline strings, are
  SCREAMING_SNAKE_CASE (`PRODUCTS_PREFIX = "/products"`).
- **Dependency-injection providers** (`dependencies.py`): snake_case,
  prefixed `get_` — `get_product_service`, `get_db_session`. The prefix
  signals "this is a `Depends()` provider function", not a plain helper.
- **Test files** (`tests/`, mirroring the module tree): `test_<module>.py`
  — `tests/modules/products/test_service.py`. Fixtures live in
  `conftest.py`; put an app-wide fixture (`client`, `db_session`) in the
  root-level `conftest.py`, and only add a module-level `conftest.py` when
  a fixture is genuinely specific to that one module.
- **Environment/config variables**: SCREAMING_SNAKE_CASE —
  `DATABASE_URL`, `JWT_SECRET_KEY`. Defined exactly once, as a field on
  the domain-specific `BaseSettings` class it belongs to in `core/settings.py`
  (`DatabaseSettings`, `AuthSettings`, ... — see `fastapi-project-bootstrap`'s
  `settings.py`, which splits config by domain rather than one monolithic
  class) — one declared home per domain, not one giant settings object.
  Never read a config value via a bare `os.environ["..."]` call scattered
  through services or routes.
- **Database tables and columns**: lowercase snake_case, singular table
  names, `_at`/`_date` suffixes, index/constraint naming. Read
  `references/database-naming.md` — this category has enough content to
  warrant its own file rather than a single bullet here.

Read `references/naming-cheatsheet.md` for the full case-style table across
every category — use it as a quick lookup instead of re-reading this
section.

## 3. Folders and files are always snake_case

Unlike the frontend's kebab-case-folders/PascalCase-files split, Python
code in this backend is snake_case everywhere at the filesystem level —
`product_catalog/`, `order_items.py` — even though the *classes* inside
those files are PascalCase. Do not carry the frontend's kebab-case folder
habit into backend code; `product-catalog/` is wrong here even though it
would be correct in a sibling `frontend` plugin's naming conventions.

## 4. When reviewing existing code

If asked to review or clean up a module's naming, walk the five files in
order (`domain/entity.py`, `domain/exceptions.py`, `schemas.py`,
`service.py`, `infra/repository.py`, `api/routes.py`, `dependencies.py`),
check each identifier against the matching rule above, and flag mismatches
by name (old name → new name) rather than silently renaming — a rename can
break imports elsewhere that need to be updated together with it.

## 5. Common violations to flag on sight

- A schema class reused for both create and response (`ProductSchema` used
  in both a `POST` body and a `GET` response model).
- A repository whose concrete class has no technology prefix
  (`ProductRepository` used directly as the SQLAlchemy implementation
  instead of `SqlAlchemyProductRepository` implementing a `ProductRepository`
  `Protocol`).
- A `services.py` (plural) file — always singular `service.py`.
- A DI provider function missing the `get_` prefix (`product_service()`
  instead of `get_product_service()`).
- A config value read via `os.environ.get(...)` instead of a
  `core/settings.py` field.

---
_Last reviewed: 2026-08-17_
