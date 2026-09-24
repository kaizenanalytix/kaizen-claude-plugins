# Domain entity vs DTO vs persistence model: the decision rule

Three lookalike classes tend to get confused. Use this rule to place a new
class correctly.

## 1. Domain entity (`domain/entity.py`)

- Framework-free: no Pydantic, no SQLAlchemy, no FastAPI imports. Plain
  Python (a `@dataclass` is the default choice).
- Carries **business methods and invariants** — behavior, not just data.
  Example: `Product.deactivate()`, `Order.can_be_cancelled()`.
- Represents the concept the business cares about, independent of how it's
  stored or transmitted.
- Lives only inside its own module; other modules never import it directly.

Ask: "Does this object have business rules attached to it, and would it
still make sense with no database and no HTTP framework installed?" If
yes, it's a domain entity.

## 2. DTO / schema (`schemas/`)

- A Pydantic model. Its only job is to define **what is actually
  serialized over the wire** — request bodies and response bodies.
- No business methods. At most, field validators for shape/format
  (e.g. "email looks like an email"), never business rules (e.g. "price
  must be positive because of a pricing policy" — that belongs on the
  entity or in the service). Prefer Pydantic's own built-in validation
  (`EmailStr`, `Field` constraints, enums) over hand-written checks for
  shape/format — see `fastapi-data-layer`'s `references/schema-conventions.md`.
- Ideally generated from, or kept in lockstep with, a sibling
  `api-contract` plugin's `contract-first` skill's schema definitions, so frontend and backend
  never drift on wire shape.
- Converted to/from entities at the edges: `service.py` builds/reads
  entities and returns DTOs (e.g. `ProductResponse.model_validate(entity)`).

Ask: "Is this shape only about what crosses the HTTP boundary?" If yes,
it's a schema/DTO.

## 3. Persistence / ORM model (`infra/models.py`)

- Framework-bound to the persistence layer (e.g. a SQLAlchemy
  `DeclarativeBase` subclass with `Column`/`Mapped` fields).
- Infra-only. It **never crosses into `domain/` or `api/`** — a route or a
  service should never see a raw ORM row.
- The repository (`infra/repository.py`) is responsible for converting a
  persistence model to a domain entity on read (`row.to_entity()`) and back
  on write.

Ask: "Is this shape dictated by the database schema/ORM?" If yes, it's a
persistence model, and it must stay inside `infra/`.

## Quick table

| | Domain entity | Schema/DTO | Persistence model |
|---|---|---|---|
| Framework | none (plain Python) | Pydantic | ORM (e.g. SQLAlchemy) |
| Has business methods | yes | no | no |
| Visible outside its layer | within module (service, api via DTO conversion) | over the wire | never leaves `infra/` |
| Lives in | `domain/entity.py` | `schemas/` | `infra/models.py` |

A one-line violation to watch for: a route function with a return type
annotation that is an ORM model, or a service method that accepts a
Pydantic schema and never converts it to an entity before applying business
rules. Both indicate the boundary has been skipped.
