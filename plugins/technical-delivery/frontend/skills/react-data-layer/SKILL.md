---
name: react-data-layer
description: >
  Establishes the server-state vs. client/UI-state split in a React module,
  composed by a custom hook the page consumes. Defaults to RTK Query and a
  Redux slice but adapts to whatever the project already uses (TanStack Query,
  Zustand, Context). Use when the user says things like "call the API", "fetch
  this data", "manage state in this module", "cache invalidation", "refetch
  after saving", "add loading and error states", "Redux slice", or "how should
  this data be fetched/stored".
---

# React Data Layer

Use this skill whenever a module needs to fetch data from an API or manage
state, and to decide what kind of state something is. One sentence of the
model this depends on: hooks own the data + dispatch logic and pages stay thin
composers, per the three-zone model — see `frontend-architecture` if that's
what's actually being asked about.

## 0. Consult the codebase map first

If a sibling `codebase-map` plugin is installed, ask its `codebase-map-sync`
skill for cached facts about this repo — which modules already have an API
slice or a client-state slice, and what naming pattern they follow — before
writing a new one. If that plugin isn't installed, look at one existing
`services/<domain>Api.ts` or `store/<domain>Slice.ts` directly instead of
guessing the project's pattern from this skill's generic examples alone.

## 1. Confirm the stack

Check `package.json` for what the project **actually** uses for server state —
`@reduxjs/toolkit` (RTK Query), `@tanstack/react-query`, `swr`, `zustand`, or
nothing at all.

**RTK Query is this plugin's greenfield default, not a prerequisite.** How to
proceed depends on what you find:

- **RTK Query present** → apply this skill as written.
- **Greenfield project** → hand off to `react-project-bootstrap`, which installs
  it, then come back.
- **A different library is already in use** → keep section 2's rule, drop this
  skill's specific API. The server-state/client-state split is the part that
  matters and it holds in every library; `createApi` + `providesTags` is just one
  implementation of it. Say plainly which library the project uses and give the
  equivalent — `queryOptions` + `invalidateQueries` in TanStack Query, a fetching
  store slice in Zustand, a fetch hook with Context.
- **No server-state library at all** → don't introduce one as a side effect of an
  unrelated request. Point out that fetches are hand-rolled, note what that costs
  (no shared cache, no invalidation, refetch-on-mount duplication), and let the
  user decide. Adding a state library is its own task.

**Never propose migrating a working app to RTK Query because this skill mentions
it.** That's a multi-week change nobody asked for, and a half-migrated app has two
caches disagreeing with each other — strictly worse than the one it started with.

## 2. The core rule: two kinds of state, two different tools

- **Server state** — anything that is a response from an API (a list of
  products, a single order, a paginated result). This always goes through
  **RTK Query**, which owns caching, loading/error flags, and tag-based
  invalidation. Read `references/rtk-query-patterns.md` and copy its pattern
  into `services/<domain>Api.ts`.
- **Client/UI state** — anything the UI owns that isn't a server response:
  filters, the currently selected row, a search box's value, a wizard step.
  This goes in a **Redux slice** via `createSlice`. Read
  `references/slice-patterns.md` and copy its pattern into
  `store/<domain>Slice.ts`.

**Never hand-store an API response in a slice.** If you see a `useEffect`
that copies `data` from a query into `useState` or a slice, that's a bug —
remove it and read straight from the RTK Query hook instead.

## 3. Compose both in a custom hook

The page never talks to `productApi` or `productSlice` directly. Instead,
write one hook per page/feature that reads from both and returns exactly what
the page needs (data, loading/error flags, and handler functions). Read
`references/custom-hook-patterns.md` and copy its pattern into
`hooks/use<Domain>.ts`.

This is what keeps pages thin: `ProductPage` calls `useProducts()` and
renders — it has no idea whether the underlying data comes from RTK Query, a
slice, or both.

## 4. Wire the store

In `core/store/store.ts`, `configureStore` needs both the RTK Query API's
reducer + middleware and the slice's reducer:

```typescript
export const store = configureStore({
  reducer: {
    [productApi.reducerPath]: productApi.reducer,
    products: productSlice.reducer,
  },
  middleware: (getDefault) => getDefault().concat(productApi.middleware),
});
```

Also set up typed versions of the hooks so call sites get full type inference
instead of relying on the untyped `useDispatch`/`useSelector`:

```typescript
export const useAppDispatch: () => typeof store.dispatch = useDispatch;
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;
```

## 5. DTO types

Domain and request/response types (`Product`, `CreateProductRequest`,
`PaginatedList<T>`) should be imported from a generated `api-contract` plugin
if one is installed, rather than hand-written — that keeps the frontend types
in sync with the backend contract. If that plugin isn't present, define the
types locally in the module's `types/` folder and leave a note that they
should be replaced once generated types exist.

## 6. Cache invalidation

Use `tagTypes` and `providesTags`/`invalidatesTags` (see
`references/rtk-query-patterns.md`) rather than manually refetching after a
mutation. A `createProduct` mutation that `invalidatesTags: ['Product']`
automatically refreshes any active `getProducts` query — no manual refetch
calls needed.

---
_Last reviewed: 2026-08-05_
