# Schema conventions: lean on Pydantic, and one shared base

Two habits that keep `schemas/` small and consistent as a project grows.

## Use Pydantic's built-in validation before writing your own

Pydantic already validates the things schemas most commonly need — reach
for its own types and `Field` constraints before writing a `field_validator`
that re-implements one:

```python
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


class ProductStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class CreateProductRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    price: float = Field(gt=0)
    status: ProductStatus = ProductStatus.DRAFT
    contact_email: EmailStr
```

- `EmailStr` validates email format — don't hand-write a regex for it.
- `Field(gt=..., max_length=..., ...)` covers numeric bounds and length
  constraints — don't write `if price <= 0: raise ValueError(...)` in a
  `field_validator` for something `Field` already expresses (this is the
  specific anti-pattern `fastapi-best-practices` rule 4 flags).
- An `Enum` gives you a closed set of valid values, documented automatically
  in the OpenAPI schema, instead of a bare `str` plus a comment listing the
  allowed values.

Reach for a `field_validator` only when the check needs something `Field`
genuinely can't express — a rule spanning two fields, or one that needs a
DB/external lookup. That's a legitimate, encouraged use, not an exception to
avoid (see `fastapi-best-practices` rule 4's clarification on this).

## One shared base model

Every schema in the project inherits from one base model, so datetime
serialization and any cross-cutting config is defined once instead of
per-schema:

```python
# shared/schemas.py
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict


class AppBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def utcnow() -> datetime:
    """Use this everywhere a schema needs 'now', not datetime.now() —
    a naive local-time timestamp silently corrupts comparisons and sort
    order the moment the app runs somewhere with a different timezone."""
    return datetime.now(timezone.utc)
```

```python
# modules/products/schemas/responses.py
from shared.schemas import AppBaseModel


class ProductResponse(AppBaseModel):
    id: int
    name: str
    price: float
    created_at: datetime
```

`from_attributes=True` (Pydantic v2's replacement for v1's `orm_mode`) is
what lets `ProductResponse.model_validate(product_row)` read attributes off
an ORM object directly — set it once on `AppBaseModel` rather than repeating
it on every response schema. If the project's datetimes need a specific
serialized format (not the default ISO 8601), add a
`model_serializer`/`field_serializer` to `AppBaseModel` once, and every
schema in the app picks it up automatically.

`shared/schemas.py` is the right home for this — it's cross-cutting and
carries no business logic, matching `backend-architecture`'s rule for what
belongs in `shared/`.
