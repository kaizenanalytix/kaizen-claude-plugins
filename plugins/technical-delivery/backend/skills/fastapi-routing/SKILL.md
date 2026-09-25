---
name: fastapi-routing
description: >
  Mounts each module's APIRouter with a consistent prefix/versioning
  scheme, protects endpoints with a reusable auth dependency, and keeps
  route signatures typed via Pydantic and function parameters. Use this
  skill when the user says "add a route", "set up routing", "protect an
  endpoint", "version the API", or "how do I add authentication to this
  endpoint".
---

# FastAPI Routing

## Purpose

Standardize how routes get exposed, versioned, and protected, so every
module's `api/routes.py` looks the same and auth is never bolted on
ad hoc. One relevant rule from `backend-architecture`: routes are the
thin `api` layer — they call only `service.py`, never `infra/` directly.

## Rule 1: every module owns one `APIRouter`, mounted in `core/app.py`

Each module defines exactly one `APIRouter` in its `api/routes.py`, scoped
with its own path prefix and tags. `core/app.py` is the single place that
mounts every module's router, with the API version prefix applied there
(not repeated inside each module):

```python
# core/app.py
app.include_router(products_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")
```

```python
# modules/products/api/routes.py
router = APIRouter(prefix="/products", tags=["products"])
```

The full path for a route is the composition of the two prefixes (here,
`/api/v1/products`). Keep the version prefix (`/api/v1`) only in
`core/app.py` so bumping the API version is a one-line change, not a
find-and-replace across every module.

## Rule 2: auth via a reusable `Depends(get_current_user)`

Define `get_current_user` once (typically in `core/` or a shared `auth`
module) and depend on it from any route that needs a signed-in user. Never
re-implement token parsing/validation inside an individual route.

```python
@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    user: User = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    return service.get_product(product_id)
```

For role- or permission-scoped endpoints, wrap `get_current_user` in a
narrower dependency (e.g. `get_current_admin_user`) rather than checking
`user.role` by hand inside each route body.

**This nesting technique isn't specific to auth** — chain any dependency
that needs another dependency's already-validated result, rather than
re-deriving that result inline. A "does this ID resolve to a real, owned
resource" check is the other common case: write it once as a dependency
that itself depends on `get_current_user`, and reuse it on every route that
takes that resource's ID, instead of repeating the lookup-and-ownership
check inside each route body.

Read `references/router-patterns.md` for the full worked example (module
router + versioned mount + protected detail route, plus a chained
resource-ownership dependency) before writing new routes — copy its shape.

## Rule 3: prefixes as constants, params as real types

- If a prefix or path segment is referenced in more than one place (e.g. a
  route and a redirect, or a route and a test), define it as a constant
  rather than repeating the literal string.
- Path/query parameters are typed directly in the function signature
  (`product_id: int`, `search: str | None = None`) so FastAPI validates and
  documents them automatically — don't parse them manually from a raw
  `Request` object.
- Request bodies are always a Pydantic schema parameter, never a raw
  `dict` or manually parsed JSON.

## Rule 4: the same resource's ID keeps the same parameter name everywhere

If `products/{product_id}` exists, every other route that takes a product's
ID — a nested route, a related resource, an admin variant — uses
`product_id` too, never `id` in one place and `product_id` in another. This
isn't just consistency for its own sake: it's what makes the chained
resource-ownership dependency in Rule 2 reusable across routes. A dependency
declared to resolve `product_id` can be `Depends()`-ed on by any route that
also names its path parameter `product_id`; rename it to `id` on one route
and that route can no longer share the dependency, so the ownership check
gets re-implemented inline instead — exactly what Rule 2 exists to avoid.

## Workflow for "add a route"

1. Confirm which module owns this route; if none does yet, hand off to
   `fastapi-module-scaffold` first.
2. Confirm the service method the route will call exists (see
   `fastapi-data-layer`); add it there if not — don't put logic in the
   route to compensate for a missing service method.
3. Write the route: typed params, a schema for the body (if any), a
   `response_model`, and `Depends(get_current_user)` if the endpoint
   requires auth.
4. Confirm the module's router is mounted in `core/app.py` (it should be,
   if the module was created via `fastapi-module-scaffold`).

---
_Last reviewed: 2026-08-17_
