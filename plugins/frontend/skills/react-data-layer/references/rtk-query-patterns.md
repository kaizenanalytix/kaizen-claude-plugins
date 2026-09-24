# RTK Query patterns — server state

Server state (anything that's an API response) is owned entirely by RTK
Query. It handles caching, request de-duplication, loading/error flags, and
tag-based invalidation, so none of that needs to be hand-rolled with
`useEffect` + `useState`.

```typescript
// services/productApi.ts — server state (caching + invalidation live here)
export const productApi = createApi({
  reducerPath: 'productApi',
  baseQuery: fetchBaseQuery({ baseUrl: '/api/v1' }),
  tagTypes: ['Product'],
  endpoints: (b) => ({
    getProducts: b.query<PaginatedList<Product>, { page?: number; limit?: number }>({
      query: ({ page = 1, limit = 20 } = {}) => `/products?page=${page}&limit=${limit}`,
      providesTags: ['Product'],
    }),
    createProduct: b.mutation<Product, CreateProductRequest>({
      query: (body) => ({ url: '/products', method: 'POST', body }),
      invalidatesTags: ['Product'],
    }),
  }),
});
```

## Notes on this pattern

- One `createApi` call per module, keyed by a unique `reducerPath` (e.g.
  `productApi`, `orderApi`) — don't share one giant API slice across every
  module; each module owns its own.
- `tagTypes` names the kinds of data this API serves. A query that
  `providesTags: ['Product']` says "I return Product data — invalidate me
  when Product data changes."
- A mutation that `invalidatesTags: ['Product']` automatically triggers a
  refetch of any active query that provides that tag. This replaces manual
  "refetch after save" logic entirely.
- `Product`, `CreateProductRequest`, and `PaginatedList<T>` are DTO types.
  Import them from a generated `api-contract` plugin if one is installed;
  otherwise define them in the module's `types/` folder and flag them as
  temporary hand-written types.
- Endpoints auto-generate hooks: `getProducts` becomes `useGetProductsQuery`,
  `createProduct` becomes `useCreateProductMutation`. These are what the
  module's custom hook (see `references/custom-hook-patterns.md`) calls
  internally — pages never call generated RTK Query hooks directly.

## Store wiring

`productApi.reducer` and `productApi.middleware` both need to be registered
in `core/store/store.ts` — see the SKILL.md body for the exact
`configureStore` shape and the typed `useAppSelector`/`useAppDispatch` hooks.
