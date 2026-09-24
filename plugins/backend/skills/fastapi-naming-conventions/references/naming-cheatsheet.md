# Naming cheatsheet

Quick lookup: case style, example, and the rule behind it, for every category
in the module skeleton (`domain/schemas/service/infra/api/dependencies`) plus
cross-cutting categories (folders, config, tests).

| Category | Case style | Example | Rule |
|---|---|---|---|
| Domain entity | PascalCase, bare noun | `Product` | No `I` prefix, no `Entity` suffix — the plain concept name. |
| Domain exception | PascalCase + `Error` suffix | `ProductNotFoundError` | Raised from `service.py`, translated to HTTP in one exception handler — never `raise HTTPException` inside the service. |
| Create/update request schema | PascalCase + `Request` suffix | `CreateProductRequest`, `UpdateProductRequest` | One schema class per direction; never shared with the response schema. |
| Response schema | PascalCase + `Response` suffix | `ProductResponse` | Set as the route's `response_model`; never the same class as the request schema. |
| Service class | PascalCase + `Service` suffix | `ProductService` | One per domain module, file named `service.py` (singular). |
| Repository interface | PascalCase, no prefix, `Protocol` | `ProductRepository` | Declared in `domain/` or `infra/repository.py`; no `I`/`Abstract` prefix. |
| Repository implementation | Technology-prefixed PascalCase | `SqlAlchemyProductRepository`, `MongoProductRepository` | Prefix names the backing technology so multiple implementations coexist. |
| Router file | Always `api/routes.py` | `routes.py` | Plural, consistent across every module — never `route.py`. |
| Router variable | snake_case | `router` | Single module-level `APIRouter()` instance per `routes.py`. |
| Route path constant (if extracted) | SCREAMING_SNAKE_CASE | `PRODUCTS_PREFIX` | Only when a raw string is pulled out of an inline route decorator. |
| DI provider function | snake_case + `get_` prefix | `get_product_service`, `get_db_session` | Lives in `dependencies.py`; prefix signals "this is a `Depends()` provider." |
| Test file | `test_<module>.py`, mirrors module tree | `tests/modules/products/test_service.py` | One test file per source file being tested. |
| App-wide fixture | Root-level `conftest.py` | `client`, `db_session` | Anything shared across modules lives at the root. |
| Module-specific fixture | Module-level `conftest.py` | — | Only when the fixture is genuinely specific to one module; don't default to this scope. |
| Folder (module or nested) | snake_case | `product_catalog/` | Always snake_case in Python — never kebab-case, unlike a sibling `frontend` plugin's folders. |
| File (any Python module) | snake_case | `order_items.py` | Same rule as folders; classes inside are still PascalCase. |
| Env / config variable | SCREAMING_SNAKE_CASE | `DATABASE_URL`, `JWT_SECRET_KEY` | Declared once as a field on `core/settings.py`'s `BaseSettings`; never a bare `os.environ` read. |

## Quick decision flow

1. Is it a domain concept (entity/exception)? PascalCase, bare noun or
   `Error`-suffixed — no `I`/`Abstract` prefixes anywhere in this codebase.
2. Is it a Pydantic schema? PascalCase, suffixed `Request` or `Response` —
   never shared between the two directions.
3. Is it a class that does orchestration or persistence? `Service` suffix
   for orchestration, no suffix (but a technology prefix on the concrete
   class) for persistence.
4. Is it a function that resolves a dependency? snake_case, `get_` prefix,
   lives in `dependencies.py`.
5. Is it a file or folder? snake_case, always — Python has no
   kebab-case-folders convention the way the frontend does.
6. Is it a config value? SCREAMING_SNAKE_CASE, one field on
   `core/settings.py`, never a scattered `os.environ` call.
