---
name: clean-architecture
description: >
  Applies a framework-agnostic three-zone model (core, modules, shared) for organizing
  any application's codebase, and enforces a one-way dependency flow between zones so
  business domains stay decoupled and reusable code stays free of business logic.
  This skill should be used when the user asks to "structure the app", "where does this
  code belong", "set conventions", or otherwise needs help deciding how to lay out
  folders, files, or dependencies in a codebase.
---

# Clean Architecture: The Three-Zone Model

Apply this model to any application, regardless of language, framework, or whether it is
frontend or backend code. It has no library-specific content — do not translate it into
React, FastAPI, or any other concrete technology here; that translation belongs in a
stack-specific plugin.

## The three zones

Divide every codebase into exactly three zones:

1. **`core`** — app bootstrap and wiring. This is the only zone imported directly by the
   entrypoint. It composes modules together, configures cross-cutting concerns (routing,
   dependency injection, global config), and contains no business logic of its own.
2. **`modules`** — one folder per business domain (e.g. `products`, `billing`, `users`).
   Each module is self-contained and owns its own logic, data access, and domain rules.
   Modules never import each other directly.
3. **`shared`** — zero-business-logic reusables: generic utilities, primitive types,
   base classes, generic error types. `shared` never contains business logic and never
   imports from `modules` or `core`.

For full detail and concrete examples of what lives in each zone, read
`references/three-zone-model.md`.

## Dependency flow is one-way

Dependencies flow in exactly one direction:

```
core → modules → shared
```

`core` may depend on `modules` and `shared`. `modules` may depend on `shared`. `shared`
depends on nothing else in the app. Never reverse an arrow, and never create a cycle —
not between zones, and not between two modules. When asked to wire something up, check
the direction of every new import against this rule before writing it.

For the full rule, why cycles are banned, how to detect a violation, what to do when two
modules seem to need the same thing, and how to spot duplication that accumulated
silently (nobody decided to duplicate it, it just happened), read
`references/dependency-rules.md`.

## Domain modules

Treat each module as a folder mapped to one business domain, meant to be self-contained
and structurally recognizable on both sides of a frontend/backend boundary — a
`products` module should look like a `products` module whether it's UI code or API code,
even though the two codebases share no code-level dependency. A module never imports
another module directly; if two modules seem to need to share something, that is a signal
to promote the shared thing into `shared/` (if it has no business logic) or to route it
through `core` as a contract (if it does) — never to reach across with a direct import.

For a boundary-setting checklist and the frontend/backend mirroring principle, read
`references/domain-modules.md`.

## Quick "which zone" checklist

When deciding where a piece of code belongs, ask in this order:

1. **Does it wire the whole app together** (bootstrap, global routing/config, composing
   modules)? → `core`.
2. **Is it specific to one business domain** (its logic, rules, or data only make sense
   in the context of one domain)? → that domain's folder under `modules`.
3. **Is it reusable with zero business logic** (a generic helper, type, or base class
   that would make sense in a completely different app)? → `shared`.

If a candidate piece of code seems to answer "yes" to both #2 and #3, prefer `shared` only
if you can strip out every domain-specific detail and it's still useful; otherwise it
belongs in the module. If it answers "yes" to more than one domain, it usually means the
domain boundary is drawn wrong — read `references/domain-modules.md` before proceeding.

When laying out a new codebase or reviewing an existing one, state which zone each new
file or import belongs to, and flag any import that violates the one-way flow before
writing code.

---
_Last reviewed: 2026-08-05_
