# Backend layering: the three-zone model applied to the API layer

## Example folder structure

```
app/
├── main.py                        # entrypoint: builds the app via core, mounts routers
├── core/
│   ├── app.py                     # create_app() factory
│   ├── config.py                  # Settings (Pydantic BaseSettings)
│   ├── container.py               # DI container: registers providers
│   ├── middleware.py              # CORS, logging, request-id, etc.
│   └── exception_handlers.py      # maps domain/HTTP exceptions to responses
├── modules/
│   ├── products/
│   │   ├── domain/
│   │   │   ├── entity.py          # Product (framework-free dataclass + methods)
│   │   │   └── exceptions.py      # ProductNotFound, InvalidPrice, ...
│   │   ├── schemas/
│   │   │   ├── requests.py        # CreateProductRequest, UpdateProductRequest
│   │   │   └── responses.py       # ProductResponse, PaginatedResponse[...]
│   │   ├── infra/
│   │   │   ├── models.py          # SQLAlchemy ProductModel (ORM row)
│   │   │   └── repository.py      # SqlAlchemyProductRepository
│   │   ├── api/
│   │   │   └── routes.py          # APIRouter, thin path operations
│   │   ├── dependencies.py        # get_product_service(), etc.
│   │   └── service.py             # ProductService — orchestration/business logic
│   ├── orders/
│   │   └── ...                    # same five-piece shape, never imports products/
│   └── users/
│       └── ...
└── shared/
    ├── pagination.py              # generic PaginatedResponse[T], page/limit parsing
    ├── errors.py                  # base AppException, ValidationError
    └── time.py                    # utcnow(), generic helpers
```

Rules of thumb:

- If a folder under `modules/` needs to reach into another module's
  internals (e.g. `orders` wants a `Product` row directly), that's a
  layering violation — expose a service method on the *owning* module
  instead, or emit an event/call across a defined boundary.
- `shared/` should be boring. If a helper contains a business rule
  ("an order is late if..."), it is not shared — it belongs in a module's
  `domain/`.

## Dependency-flow diagram

```
main.py
  │
  ▼
core/app.py  (create_app: settings, middleware, exception handlers, container)
  │
  ▼  include_router() per module
modules/<name>/api/routes.py           (thin path operations)
        │  Depends(get_x_service)
        ▼
modules/<name>/service.py              (business orchestration — the only
        │  Depends(get_x_repository)     thing routes call)
        ▼
modules/<name>/domain/entity.py        (framework-free entity + invariants)
        ▲  implements interface declared here
        │
modules/<name>/infra/repository.py     (persistence; implements the
                                          domain-declared interface)
```

Notice the arrow direction: `domain` declares the repository *interface*,
but does not depend on `infra`. `infra` depends on `domain` (to return
entities), not the other way around. This is dependency inversion — it's
what lets you swap Postgres for a fake in-memory repository in tests
without changing `service.py` or `domain/`.

`api/routes.py` never imports anything from `infra/` directly — only from
`service.py` and `schemas/`.
