# The three-zone model, in React folder terms

A sibling `architecture-foundations` plugin's `ui-architecture` skill defines
the neutral shape this maps from (`references/ui-layering.md` there has the
full framework-neutral walkthrough). This file only adds the concrete React
folder names and React-specific mechanics.

## Top-level layout

```
src/
  core/            # app bootstrap — imported only by the entrypoint
    router/
      AppRouter.tsx
    store/
      store.ts
    providers/
      AppProviders.tsx
  modules/
    products/      # one folder per business domain
      components/
      pages/
      hooks/
      services/
      store/
      context/     # optional
      types/
    orders/
      ...
  shared/          # zero business logic
    components/
    hooks/
    utils/
```

## What lives in `core/`

- `router/AppRouter.tsx` — the top-level `<Routes>` tree, composed from routes
  each module contributes (see `react-routing`).
- `store/store.ts` — `configureStore`, wiring in every module's reducer and
  any RTK Query middleware (see `react-data-layer`).
- `providers/AppProviders.tsx` — theme provider, query client, top-level auth
  context. This is the *only* place app-wide context providers should mount.
  Module-scoped context providers do not belong here (see `react-module-context`).

`core/` is imported only by the entrypoint (`main.tsx`). No module should ever
import from `core/` except to register itself (e.g. exporting a reducer that
`store.ts` imports).

## What lives in `modules/<name>/`

Every business domain gets exactly these seven subfolders, even if some start
empty:

- **`components/`** — dumb, render-props-only. No fetching, no dispatching, no
  business logic. Given the same props, always renders the same thing.
- **`pages/`** — thin route composers. A page calls one hook to get data and
  handlers, then renders components. No business logic in a page — if you're
  writing an `if` statement that isn't about "is this loading / did this
  error", it's probably logic that belongs in a hook.
- **`hooks/`** — own the data-fetching and dispatch logic. This is where a
  page's brain lives.
- **`services/`** — the API layer for this domain (e.g. RTK Query API slices).
- **`store/`** — client/UI state only for this domain (filters, selection,
  wizard step). Never a place to hand-store API responses — that's what
  `services/` (via RTK Query's cache) is for.
- **`context/`** (optional) — module-scoped React Context, for state that
  needs to reach many descendants within this module's subtree but doesn't
  belong in the global store.
- **`types/`** — domain entity types and request/response DTOs. If a sibling
  `api-contract` plugin's `contract-first` skill has generated DTO types, import those
  instead of hand-writing them here; otherwise define them locally and note
  they should be replaced once that plugin's generated types exist.

Example, using a `products` module:

```
modules/products/
  components/
    ProductList.tsx
    ProductItem.tsx
  pages/
    ProductPage.tsx
  hooks/
    useProducts.ts
  services/
    productApi.ts
  store/
    productSlice.ts
  context/
    (optional — only if this module needs it)
  types/
    product.types.ts
```

## What lives in `shared/`

Anything reusable that has *zero* business logic: generic buttons, modals,
form fields, date formatters, `useDebounce`, `useMediaQuery`. The moment a
"shared" file needs to know what a Product or an Order is, it isn't shared —
move it into the owning module (or, if genuinely needed by two-plus modules,
reconsider whether it's really domain-agnostic first).
