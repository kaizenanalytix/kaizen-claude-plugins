# FastAPI anti-patterns: bad vs. good

One before/after pair per rule from `SKILL.md`, for rules 1–9 — the ones
where a concrete code snippet makes the point better than prose. Rules 10
and 11 (hiding docs, `BackgroundTasks` vs. a task queue) are config/judgment
calls rather than code shapes, so they don't get a snippet here. Use these
as copyable templates when writing a review.

## 1. Blocking call inside an async route

```python
# Bad: requests is a blocking, synchronous call inside an async def route —
# it stalls the event loop for every other concurrent request while it waits
@router.get("/products/{product_id}/price-check")
async def price_check(product_id: str):
    response = requests.get(f"https://pricing.internal/api/{product_id}")
    return response.json()

# Good: httpx is async-native, so awaiting it yields control back to the
# event loop instead of blocking the thread
@router.get("/products/{product_id}/price-check")
async def price_check(product_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://pricing.internal/api/{product_id}")
    return response.json()

# Good, when no async version of the library exists: push the blocking
# call onto a thread pool so it doesn't block the loop
from starlette.concurrency import run_in_threadpool

@router.get("/products/{product_id}/legacy-price-check")
async def legacy_price_check(product_id: str):
    return await run_in_threadpool(legacy_blocking_client.get_price, product_id)
```

## 2. N+1 queries when loading related data

```python
# Bad: one query for the products, then one more query per product to
# fetch its category — 1 + N queries for a list of N products
async def list_products_with_category(session: AsyncSession) -> list[Product]:
    products = (await session.execute(select(ProductModel))).scalars().all()
    for product in products:
        product.category = (
            await session.execute(
                select(CategoryModel).where(CategoryModel.id == product.category_id)
            )
        ).scalar_one()
    return products

# Good: a single query with selectinload eagerly loads every product's
# category in one round trip
async def list_products_with_category(session: AsyncSession) -> list[Product]:
    result = await session.execute(
        select(ProductModel).options(selectinload(ProductModel.category))
    )
    return result.scalars().all()
```

## 3. Missing response model

```python
# Bad: returns the raw ORM object — no validation or filtering of the
# outgoing shape, so an internal-only column (e.g. cost_price) leaks
# straight into the API response
@router.get("/products/{product_id}")
async def get_product(product_id: str, service: ProductService = Depends(get_product_service)):
    return await service.get(product_id)

# Good: response_model both validates the shape and filters out anything
# not declared on ProductResponse
@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str, service: ProductService = Depends(get_product_service)):
    return await service.get(product_id)
```

## 4. Pydantic v1 patterns under v2

```python
# Bad: v1-era API, deprecated (and removed in stricter v2 configurations)
product_response = ProductResponse.from_orm(product)
payload = product_response.dict()

# Good: v2 API
product_response = ProductResponse.model_validate(product)
payload = product_response.model_dump()
```

```python
# Bad: manual validation re-implementing what Field already does
class CreateProductRequest(BaseModel):
    price: float

    @field_validator("price")
    @classmethod
    def check_price(cls, v):
        if v <= 0:
            raise ValueError("price must be positive")
        return v

# Good: constraint expressed declaratively via Field
class CreateProductRequest(BaseModel):
    price: float = Field(gt=0)
```

## 5. Module-level global DB session

```python
# Bad: one session shared across every request — concurrent requests read
# and write through the same session object, corrupting each other's state
db_session = SessionLocal()

@router.get("/products")
async def list_products():
    return db_session.query(ProductModel).all()

# Good: a fresh, request-scoped session per request, closed after
async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session

@router.get("/products")
async def list_products(session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(select(ProductModel))
    return result.scalars().all()
```

## 6. HTTPException raised from the service layer

```python
# Bad: the service layer raises HTTPException directly — now this service
# can't be called from a CLI script or background job without dragging in
# an HTTP-specific exception type
class ProductService:
    async def get(self, product_id: str) -> Product:
        product = await self._repository.get_by_id(product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

# Good: the service raises a domain exception; one exception handler in
# core/app.py translates it to HTTP
class ProductService:
    async def get(self, product_id: str) -> Product:
        product = await self._repository.get_by_id(product_id)
        if product is None:
            raise ProductNotFoundError(product_id)
        return product

# core/app.py
@app.exception_handler(ProductNotFoundError)
async def handle_product_not_found(request: Request, exc: ProductNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})
```

## 7. Business logic living in the route

```python
# Bad: discount eligibility logic is embedded directly in the route
@router.post("/orders", response_model=OrderResponse)
async def create_order(payload: CreateOrderRequest, service: OrderService = Depends(get_order_service)):
    if payload.total > 100 and payload.customer_tier == "gold":
        payload.discount = payload.total * 0.1
    else:
        payload.discount = 0
    return await service.create(payload)

# Good: the route stays a thin translation layer; the rule lives in the service
@router.post("/orders", response_model=OrderResponse)
async def create_order(payload: CreateOrderRequest, service: OrderService = Depends(get_order_service)):
    return await service.create(payload)

class OrderService:
    async def create(self, payload: CreateOrderRequest) -> Order:
        discount = self._calculate_discount(payload.total, payload.customer_tier)
        ...
```

## 8. List endpoint with no pagination

```python
# Bad: returns every row, unbounded — fine at 50 products, a problem at 500,000
@router.get("/products", response_model=list[ProductResponse])
async def list_products(service: ProductService = Depends(get_product_service)):
    return await service.list_all()

# Good: limit/offset pagination from day one
@router.get("/products", response_model=Page[ProductResponse])
async def list_products(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    service: ProductService = Depends(get_product_service),
):
    return await service.list_page(limit=limit, offset=offset)
```

## 9. A "PUT" that behaves like an append

```python
# Bad: calling this twice with the same body adds the tag twice —
# not idempotent, despite being a PUT
@router.put("/products/{product_id}/tags", response_model=ProductResponse)
async def add_tag(product_id: str, payload: AddTagRequest, service: ProductService = Depends(get_product_service)):
    return await service.append_tag(product_id, payload.tag)

# Good: PUT replaces the full tag set — calling it twice with the same
# body leaves the resource in the same state both times
@router.put("/products/{product_id}/tags", response_model=ProductResponse)
async def replace_tags(product_id: str, payload: ReplaceTagsRequest, service: ProductService = Depends(get_product_service)):
    return await service.set_tags(product_id, payload.tags)
```
