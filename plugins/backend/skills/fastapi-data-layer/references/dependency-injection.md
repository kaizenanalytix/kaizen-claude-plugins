# Dependency injection

`Depends()` is how a route gets a ready-to-use service without knowing how
it was built. The provider chain always goes session → repository →
service, and a route only ever depends on the service provider.

```python
def get_product_service(session: Session = Depends(get_db_session)) -> ProductService:
    return ProductService(repository=SqlAlchemyProductRepository(session))
```

`get_db_session` is an app-wide provider (defined once in `core/`, e.g.
`core/database.py` or `core/container.py`), typically something like:

```python
def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

Every module's `dependencies.py` depends on this one shared provider
rather than each module opening its own DB connection logic.

## FastAPI caches a dependency's result for the life of one request

If a single request ends up depending on `get_db_session` twice — say a
route both takes `service: ProductService = Depends(get_product_service)`
and separately `Depends(get_current_user)`, and `get_current_user` also
needs a DB session — FastAPI resolves `get_db_session` **once** for that
request and reuses the result everywhere it's needed, rather than opening a
second session. This is why chains like session → repository → service (or
the resource-ownership dependency in `fastapi-routing`, which depends on
both `get_current_user` and a service provider) are cheap to compose — the
shared lower-level dependency underneath them doesn't run twice just
because two things above it depend on it.

This caching is per-request and keyed by the callable, not global — a
second, unrelated request gets its own fresh session. If a dependency
genuinely needs to run twice within the same request (rare — a case that
must observe a side effect from earlier in the same request), opt out with
`Depends(get_x, use_cache=False)` rather than restructuring the dependency
graph to avoid the cache.

## When to introduce a `Container`

For a small number of modules, per-module `dependencies.py` files with
plain `Depends()` functions (as above) are enough — no extra abstraction
needed.

Once a project has many modules and the same wiring pattern
(session → repository → service) is being repeated everywhere, centralize
provider registration in a `Container` class in `core/container.py`:

```python
class Container:
    def __init__(self, session_factory: Callable[[], Session]):
        self._session_factory = session_factory

    def product_service(self) -> ProductService:
        session = self._session_factory()
        return ProductService(repository=SqlAlchemyProductRepository(session))
```

Modules' `dependencies.py` files then become thin wrappers that pull from
the shared container instance rather than each redefining the same chain.
Introduce this only when the duplication is real — don't add a container
for a one- or two-module app.

## Common mistakes to flag

- A route with `Depends()` on a repository directly, skipping the service.
- A service constructed inline inside a route function instead of through
  a `Depends()` provider (makes it impossible to override in tests).
- A provider that opens a DB session but never closes it (missing
  try/finally or context manager) — this leaks connections under load.
