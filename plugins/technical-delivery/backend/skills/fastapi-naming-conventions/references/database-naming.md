# Database naming conventions

Two categories SQLAlchemy will happily let you skip, and shouldn't: an
explicit constraint/index naming convention, and consistent table/column
names. Both matter because a migration or a `\d` in `psql` should be
readable without cross-referencing model source.

## Explicit constraint/index naming convention

Left to its defaults, SQLAlchemy generates constraint and index names that
are inconsistent across dialects and, on Postgres, silently truncated past
63 characters — two tables with similarly-named long columns can produce
colliding truncated constraint names. Set an explicit `naming_convention` on
the shared `MetaData` once, in `core/database.py`:

```python
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
```

Every model built off this `Base` picks up the convention automatically —
nothing to repeat per model. This is also what makes Alembic's
autogenerate produce stable, predictable migration diffs when a constraint
changes; without it, a constraint can appear to change on every
autogenerate run purely because its auto-derived name shifted.

## Table and column naming

- **Tables**: lowercase snake_case, singular — `product`, not `Products` or
  `products_table`. (Singular is a deliberate, opinionated choice here;
  either convention is defensible, but pick one and never mix them within a
  project — a codebase with both `product` and `order_items` is worse than
  one consistently using either.)
- **Related tables share a prefix** when they form a clear group —
  `billing_invoice`, `billing_invoice_line`, `billing_payment` — so they
  sort and grep together, and so the grouping is visible from the table
  name alone, without opening a schema diagram.
- **Datetime columns end in `_at`** — `created_at`, `updated_at`,
  `deleted_at`. **Date-only columns end in `_date`** — `billing_date`,
  `due_date`. This distinction is worth keeping precise: a column named
  `created_date` that actually stores a full timestamp misleads the next
  person who queries it expecting date-only granularity.
- **Foreign key columns are `<singular_table>_id`** — `product_id`,
  `order_id` — matching the path-parameter naming rule in `fastapi-routing`
  (Rule 4), so the same identifier reads the same way at the database, the
  domain, and the API layer.

## Applying this to an existing project

If a project already has an established (even if different) convention,
match it rather than introducing a second one — the value here is
consistency within one codebase, not universal agreement on singular vs.
plural table names. Flag the mismatch per this suite's
`existing-codebase-adoption` rule rather than silently converting existing
tables to match this document.
