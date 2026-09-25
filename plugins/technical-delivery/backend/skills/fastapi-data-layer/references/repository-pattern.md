# Repository pattern

The domain layer declares the interface (a `Protocol`); infra implements
it. This is dependency inversion: `domain/` has no import of SQLAlchemy or
any other persistence library, but `infra/` imports from `domain/` to
return entities.

```python
from typing import Protocol


class ProductRepository(Protocol):
    def get(self, product_id: int) -> Product | None: ...
    def list(self, search: str | None) -> list[Product]: ...
    def save(self, product: Product) -> Product: ...


class SqlAlchemyProductRepository(ProductRepository):
    def __init__(self, session: Session):
        self._session = session

    def get(self, product_id: int) -> Product | None:
        row = self._session.get(ProductModel, product_id)
        return row.to_entity() if row else None

    def list(self, search: str | None) -> list[Product]:
        query = self._session.query(ProductModel)
        if search:
            query = query.filter(ProductModel.name.ilike(f"%{search}%"))
        return [row.to_entity() for row in query.all()]
```

Notes:

- The `Protocol` typically lives in `domain/` (e.g.
  `domain/repository.py`) or right next to the entity — either is fine as
  long as `infra/` is the only place that implements it.
- `ProductModel` is the persistence/ORM model (see
  `backend-architecture`'s `references/domain-vs-infra-boundary.md`) — it
  lives in `infra/models.py` and is converted to a `Product` entity via a
  `to_entity()` method (or a small mapper function), never returned
  directly.
- `save()` should accept and return a domain entity, handling the
  entity-to-row conversion internally.
- Where a project uses something other than SQLAlchemy (e.g. an async
  driver, a NoSQL client, an external API as the "database"), the shape
  stays the same — only the concrete implementation class changes. Never
  let the choice of persistence technology leak into the `Protocol` itself.
- For tests, implement the same `Protocol` with an in-memory
  dict-backed fake instead of a real database — see `fastapi-testing`'s
  `assets/conftest.py` for a ready-made `fake_product_repository` fixture.

## SQL-first, Pydantic-second

Push filtering, joins, and aggregation into the query itself — the database
is built to do this efficiently at any row count; pulling every row into
Python and processing it there scales linearly with data size in the worst
possible place, application memory. The `list()` method above already does
this in miniature (the `ilike` filter runs in the query, not after
`.all()`); the pattern matters more as the query gets richer:

```python
# Bad: fetch everything, count in Python
def count_products_by_category(self) -> dict[str, int]:
    products = self._session.query(ProductModel).all()
    counts: dict[str, int] = {}
    for product in products:
        counts[product.category_name] = counts.get(product.category_name, 0) + 1
    return counts


# Good: aggregate in the query
def count_products_by_category(self) -> dict[str, int]:
    rows = (
        self._session.query(CategoryModel.name, func.count(ProductModel.id))
        .join(ProductModel, ProductModel.category_id == CategoryModel.id)
        .group_by(CategoryModel.name)
        .all()
    )
    return dict(rows)
```

The bad version loads every product row into memory just to throw away
everything except a count — it gets slower and more memory-hungry as the
table grows, and it's slower than the database's own aggregation even at
today's size. The good version returns only the aggregated result. The same
reasoning applies to joins: use SQLAlchemy's `join()` (or `selectinload`/
`joinedload` for relationship loading — see `fastapi-best-practices` rule 2
on N+1 queries) rather than fetching two lists and matching them up in a
Python loop.
