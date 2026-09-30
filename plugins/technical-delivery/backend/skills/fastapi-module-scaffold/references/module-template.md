# Module template: starter code

Use this as the literal starting point for a new module. Rename `Product`
and `products` to match the domain being scaffolded, then adjust fields and
the example business method.

## `domain/entity.py`

```python
from dataclasses import dataclass


@dataclass
class Product:
    id: int
    name: str
    price: float
    is_active: bool = True

    def deactivate(self) -> None:
        self.is_active = False
```

Keep entities framework-free: no Pydantic, no ORM base class, no FastAPI
imports. Add one business method per invariant the domain actually
enforces — don't add speculative methods with no caller.

## `api/routes.py` — thin composer

```python
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=PaginatedResponse[ProductResponse])
def list_products(
    search: str | None = None,
    service: ProductService = Depends(get_product_service),
):
    return service.list_products(search=search)


@router.post("", response_model=ProductResponse, status_code=201)
def create_product(
    body: CreateProductRequest,
    service: ProductService = Depends(get_product_service),
):
    return service.create_product(body)
```

Notes on this file:

- Route handlers do three things and nothing else: accept validated input
  (via Pydantic schemas and typed params), call exactly one service method,
  return its result.
- No business logic, no direct repository/DB access, no manual
  try/except for domain errors — those are handled by the app's global
  exception handlers (registered in `core/exception_handlers.py`), which
  translate domain exceptions (from `domain/exceptions.py`) into HTTP
  responses.
- `response_model` is always a schema from `schemas/`, never the domain
  entity or an ORM model.

For the corresponding `schemas/`, `service.py`, `infra/repository.py`, and
`dependencies.py` content, see the `fastapi-data-layer` skill's
`references/repository-pattern.md`, `references/service-layer-patterns.md`,
`references/schema-conventions.md` (the shared base every new schema in
`schemas/requests.py`/`schemas/responses.py` should inherit from), and
`references/dependency-injection.md` — they contain the fuller
`ProductRepository` / `ProductService` / `get_product_service` example that
this scaffold's routes call into.

If the module needs its own table, `infra/models.py`'s column and index
names should follow `fastapi-naming-conventions`'
`references/database-naming.md` rather than whatever SQLAlchemy's defaults
produce.
