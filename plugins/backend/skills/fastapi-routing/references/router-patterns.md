# Router patterns

## Mounting: version prefix lives in `core/app.py`

```python
# core/app.py
from app.modules.products.api.routes import router as products_router
from app.modules.orders.api.routes import router as orders_router

def create_app() -> FastAPI:
    app = FastAPI()
    app.include_router(products_router, prefix="/api/v1")
    app.include_router(orders_router, prefix="/api/v1")
    return app
```

## Module router: own prefix + tags

```python
# modules/products/api/routes.py
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    user: User = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    return service.get_product(product_id)
```

Resulting full route: `GET /api/v1/products/{product_id}`, requiring an
authenticated user.

## Protected vs public routes in the same router

Mix protected and public routes in the same `APIRouter` freely — the auth
dependency is declared per-route, not per-router:

```python
@router.get("", response_model=PaginatedResponse[ProductResponse])
def list_products(
    search: str | None = None,
    service: ProductService = Depends(get_product_service),
):
    # public: no get_current_user dependency
    return service.list_products(search=search)


@router.post("", response_model=ProductResponse, status_code=201)
def create_product(
    body: CreateProductRequest,
    user: User = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    # protected: requires a signed-in user
    return service.create_product(body)
```

If an entire router should be uniformly protected, apply the dependency at
the router level instead of repeating it on every route:

```python
router = APIRouter(
    prefix="/admin/products",
    tags=["admin-products"],
    dependencies=[Depends(get_current_admin_user)],
)
```

## Role-scoped auth dependency

```python
def get_current_admin_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
```

Building narrower dependencies like this on top of `get_current_user`
keeps permission checks declarative and out of route bodies.

## Chained dependency for resource ownership — the same technique, a different use

Role-scoping isn't the only place a dependency should depend on another
dependency's result. Resolving "does this ID belong to a real resource the
current user is allowed to touch" is the same shape, keyed on the path
parameter's name:

```python
def valid_owned_product(
    product_id: int,
    user: User = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
) -> Product:
    product = service.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not your product")
    return product


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    body: UpdateProductRequest,
    product: Product = Depends(valid_owned_product),
    service: ProductService = Depends(get_product_service),
):
    return service.update_product(product, body)


@router.delete("/{product_id}", status_code=204)
def delete_product(
    product: Product = Depends(valid_owned_product),
    service: ProductService = Depends(get_product_service),
):
    service.delete_product(product)
```

`valid_owned_product` is written once and reused by every route that takes
a `product_id` — the lookup-and-ownership check never gets re-implemented
inline. This only works because every one of these routes names its path
parameter `product_id`; a route that instead used `id` for the same
resource couldn't share this dependency (see `fastapi-routing/SKILL.md`
Rule 4).

## Path constants for repeated segments

```python
# core/constants.py
API_V1_PREFIX = "/api/v1"
```

```python
app.include_router(products_router, prefix=API_V1_PREFIX)
```

Use this once a prefix is referenced from more than one place (e.g. app
mounting and a test's base URL) — for a single usage, a literal string is
fine.
