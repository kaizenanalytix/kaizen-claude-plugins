# Unit and integration tests

## Unit: domain entity

```python
def test_product_deactivate_sets_is_active_false():
    product = Product(id=1, name="Widget", price=9.99, is_active=True)

    product.deactivate()

    assert product.is_active is False
```

No fixtures, no imports beyond the entity itself.

## Unit: service with a fake repository

```python
def test_create_product_saves_and_returns_response(fake_product_repository):
    service = ProductService(repository=fake_product_repository)
    request = CreateProductRequest(name="Widget", price=9.99)

    result = service.create_product(request)

    assert result.name == "Widget"
    assert fake_product_repository.list(search=None)[0].name == "Widget"


def test_list_products_filters_by_search(fake_product_repository):
    fake_product_repository.save(Product(id=None, name="Widget", price=9.99))
    fake_product_repository.save(Product(id=None, name="Gadget", price=4.99))
    service = ProductService(repository=fake_product_repository)

    result = service.list_products(search="Widget")

    assert len(result) == 1
    assert result[0].name == "Widget"
```

`fake_product_repository` comes from `assets/conftest.py` — it implements
the same `ProductRepository` Protocol as the SQLAlchemy repository but
backs it with a plain dict, so these tests need no database and run in
milliseconds.

## Integration: route via the async `client`, real repository, test DB

```python
async def test_create_product_endpoint_returns_201(client, db_session):
    response = await client.post("/api/v1/products", json={"name": "Widget", "price": 9.99})

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Widget"

    # confirm it actually persisted, via the real repository
    repo = SqlAlchemyProductRepository(db_session)
    assert repo.list(search="Widget")


async def test_get_product_requires_auth(client):
    response = await client.get("/api/v1/products/1")

    assert response.status_code == 401


async def test_get_product_not_found_returns_404(client, auth_headers):
    response = await client.get("/api/v1/products/999999", headers=auth_headers)

    assert response.status_code == 404
```

`client` and `db_session` come from `assets/conftest.py`. `client` is an
async `httpx.AsyncClient`, so every test function that uses it is `async def`
and every call is `await`ed — `asyncio_mode = "auto"` in `pyproject.toml`
means pytest runs them without a `@pytest.mark.asyncio` decorator on each one.
Integration tests exercise the full stack (route → service → real repository
→ test DB), so keep them focused on wiring correctness (status codes, auth
enforcement, serialization) rather than re-testing every business rule
already covered at the unit layer.
