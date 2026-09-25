# Service layer patterns

The service is the only thing routes call. It owns orchestration and
business rules, takes its repository via constructor injection, and
converts between domain entities and response schemas at its boundary.

```python
class ProductService:
    def __init__(self, repository: ProductRepository):
        self._repository = repository

    def create_product(self, request: CreateProductRequest) -> ProductResponse:
        product = Product(id=None, name=request.name, price=request.price)
        saved = self._repository.save(product)
        return ProductResponse.model_validate(saved)

    def list_products(self, search: str | None) -> list[ProductResponse]:
        return [ProductResponse.model_validate(p) for p in self._repository.list(search)]
```

Notes:

- One public method per use case (`create_product`, `list_products`,
  `deactivate_product`, ...) — not a generic `handle(request)` grab-bag.
- Input is typically a schema (`CreateProductRequest`); output is
  typically a schema (`ProductResponse`) so the route can return the
  service's result directly with no further transformation.
- Business invariants belong here or on the entity, not in the route and
  not in the repository. Example: if "a product's price cannot be
  negative" is a rule, enforce it either in `Product.__post_init__` (on
  the entity) or as an explicit check in the service before calling
  `save()` — raise a domain exception from `domain/exceptions.py` on
  violation, and let the app's global exception handler (registered in
  `core/exception_handlers.py`) translate it to the right HTTP status.
  Do not raise `HTTPException` from inside a service — that couples
  business logic to the transport layer.
- A service may call other methods on repositories from its *own* module
  only. If a use case genuinely needs data from another domain, call that
  domain's service (not its repository), through a normal Python import of
  its public service interface — do not reach into another module's
  `infra/`.
- Keep services synchronous or async consistently with the rest of the
  project; don't mix the two within one module without a reason.
