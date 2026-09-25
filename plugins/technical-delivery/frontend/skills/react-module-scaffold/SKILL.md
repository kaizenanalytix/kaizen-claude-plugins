---
name: react-module-scaffold
description: >
  Scaffolds a new business-domain module in a React app — the seven-folder
  skeleton (components/pages/hooks/services/store/context/types) — and wires
  it into the app's store and router. Use when the user says things like
  "add a module", "new feature/domain", "scaffold the X module", or "create a
  new domain folder for Y".
---

# React Module Scaffold

Use this skill to create a new business-domain module under `modules/<name>/`
and connect it to the rest of the app. One sentence of the model this depends
on: a module is a self-contained folder for one business domain, per the
three-zone model (`core/modules/shared`) — see `frontend-architecture` for the
full model if that's what's actually being asked about.

## 0. Consult the codebase map first

If a sibling `codebase-map` plugin is installed, ask its `codebase-map-sync`
skill for cached facts about this repo — the existing module list and the
naming convention actually in use — before scaffolding a new one. Matching
an existing module's real shape matters more here than following this
skill's template verbatim, and the map gives that for free instead of
opening several existing modules to compare. If that plugin isn't
installed, do the equivalent live: look at one existing module under
`src/modules/` directly before creating the new one.

## 1. Check the stack

Confirm `react` is a dependency in `package.json`. If the project doesn't
exist yet, hand off to `react-project-bootstrap` first. If the project
already exists but wasn't scaffolded by this plugin, hand off to a sibling
`architecture-foundations` plugin's `existing-codebase-adoption` skill
first — scaffolding a new module is exactly where this plugin's seven-folder
skeleton can conflict with a project's existing conventions.

## 2. Create the seven-folder skeleton

Under `src/modules/<name>/`, create:

```
modules/<name>/
  components/   # dumb, render-props-only
  pages/        # thin composers, no business logic
  hooks/        # own the data + dispatch logic
  services/     # API calls (typically RTK Query, see react-data-layer)
  store/        # client/UI state only (see react-data-layer)
  context/      # optional — only if the module needs module-scoped state
  types/        # domain entity + request/response DTOs
```

Only create `context/` if there's an actual need for module-scoped shared
state (see `react-module-context`); it's fine to leave it out until needed.

Read `references/module-template.md` for a concrete, copy-paste skeleton
(using a "Product" domain as the running example) showing how a page and a
component should look and divide responsibility. Adapt the naming to the
domain being scaffolded, but keep the shape: the page is a thin composer, the
component is dumb.

## 3. Populate `types/`

Put domain entity types and request/response DTOs here. If a sibling
`api-contract` plugin's `contract-first` skill has generated these DTO types, import them
from there instead of hand-writing. If it's not installed or hasn't been run yet, define them
locally in `types/` and leave a comment noting they should be replaced by the
generated types once that plugin is adopted.

## 4. Wire the module into the store

In `core/store/store.ts`, register the new module's reducer (and, if the
module uses RTK Query, its API middleware — see `react-data-layer`) alongside
the other modules'. Do not let `core/store/store.ts` contain any business
logic itself — it only imports and composes what each module exports.

## 5. Wire the module into the router

In `core/router/AppRouter.tsx`, add a lazy-loaded route for each new page (see
`react-routing` for the exact `React.lazy` + `PrivateRoute` pattern). Do this
as its own step — don't inline routing logic into the module.

## 6. Enforce the responsibility split

- **Pages** (`pages/`): call exactly one hook to get everything they need
  (data, loading/error flags, handlers), then render. No conditionals beyond
  loading/error/empty states. No fetching, no dispatching directly from a
  page.
- **Components** (`components/`): pure render of the props they're given.
  No hooks that fetch or dispatch. If a component needs local-only UI state
  (e.g. whether a dropdown is open), that's fine — but never business state.
- **Hooks** (`hooks/`): this is where fetching, dispatching, and deriving data
  happens. A page should be replaceable by swapping which hook it calls.

If asked to scaffold data fetching or state management inside the new module,
hand off to `react-data-layer` rather than improvising it here.

---
_Last reviewed: 2026-08-05_
