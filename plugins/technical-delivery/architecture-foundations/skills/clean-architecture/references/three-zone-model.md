# The Three-Zone Model, In Detail

This model applies to any application — a web frontend, an API backend, a CLI tool, a
worker service — because it makes no assumption about frameworks, languages, or runtime.
It only assumes an application has an entrypoint, some business domains, and some
reusable plumbing.

## Zone 1: `core`

`core` is the composition root. It is the only zone the entrypoint imports directly, and
its job is to wire everything else together.

What belongs in `core`:
- App bootstrap / startup sequence.
- Global configuration loading (environment variables, feature flags, app-wide settings).
- Top-level routing or dispatch that decides which module handles what (without
  containing the domain logic itself).
- Dependency injection / composition wiring — constructing module instances and handing
  them their shared dependencies.
- Cross-cutting infrastructure setup that has to happen once for the whole app (e.g.
  initializing a logger, a database connection pool, a global error boundary) — the
  *setup* of these things lives in `core`; generic *reusable helpers* for using them
  belong in `shared`.

What does NOT belong in `core`:
- Any business rule specific to one domain. If you find yourself writing an `if` that
  only makes sense for "orders" or "users" inside `core`, that logic belongs in a module.
- Generic utilities with no wiring responsibility — those belong in `shared`.

Mental test: if you deleted every module, would `core` still make sense as "the empty
skeleton that used to wire modules together"? If yes, it's correctly scoped.

## Zone 2: `modules`

`modules` holds one folder per business domain. Each folder is self-contained: its
logic, its data access, its types, its own internal structure. Examples of domains:
`products`, `orders`, `billing`, `users`, `notifications`.

What belongs in a module:
- Domain logic and business rules for that one domain.
- Domain-specific data access/persistence code.
- Domain-specific types/models.
- Anything that would need to change if — and only if — the business rules for that one
  domain changed.

What does NOT belong in a module:
- Code needed by more than one domain with no domain-specific behavior — that's a signal
  it belongs in `shared`.
- Direct imports of another module's internals.

## Zone 3: `shared`

`shared` holds reusable code with **zero business logic**. If you can imagine reusing a
piece of code in a completely unrelated application (a different product, a different
company) without modification, it likely belongs here.

What belongs in `shared`:
- Generic utility functions (string formatting, date math, generic collection helpers).
- Generic types (e.g. a `Result<T, E>`-style wrapper, a generic pagination shape).
- Base classes or generic abstractions that modules extend, with no domain awareness
  baked in.
- Generic error types (e.g. a `NotFoundError` base class — not a `ProductNotFoundError`,
  which belongs in the `products` module since it names a domain concept).

What does NOT belong in `shared`:
- Anything that mentions or assumes a specific business domain by name or behavior.
- Anything that imports from `modules` or `core` — `shared` must have zero inbound
  dependency on the rest of the app so it stays trivially reusable and testable in
  isolation.

## The dependency-flow diagram

```
        ┌─────────────┐
        │    core      │   (entrypoint imports this; wires everything)
        └──────┬───────┘
               │  depends on
               ▼
        ┌─────────────┐
        │   modules    │   (one folder per business domain; siblings never import
        │  ┌────────┐  │    each other)
        │  │products│  │
        │  ├────────┤  │
        │  │billing │  │
        │  ├────────┤  │
        │  │ users  │  │
        │  └────────┘  │
        └──────┬───────┘
               │  depends on
               ▼
        ┌─────────────┐
        │   shared     │   (zero business logic; depends on nothing above)
        └─────────────┘
```

Arrows only ever point downward in this diagram. `shared` is the foundation and knows
nothing about what's built on top of it. `core` is the top of the structure and is the
only piece allowed to know about everything.

## Concrete "which zone" examples

- A function that formats a currency amount using a locale → `shared` (no domain logic,
  purely generic formatting).
- A function that computes a discount based on a customer's loyalty tier → `modules`
  (specific to a domain — e.g. `billing` or `orders` — because "loyalty tier" and
  "discount" are domain concepts).
- The code that reads environment variables at startup and constructs the app → `core`.
- A generic retry/backoff helper for calling out to any remote system → `shared`.
- The specific set of remote calls a `products` module makes to fetch and validate
  product data → `modules/products`.
- A base "domain error" class with no knowledge of any specific domain → `shared`.
- A `ProductNotFoundError` that extends that base class and adds product-specific
  fields → `modules/products`.
- The top-level route table that says "requests for /orders go to the orders module" →
  `core` (it's wiring, not business logic).
