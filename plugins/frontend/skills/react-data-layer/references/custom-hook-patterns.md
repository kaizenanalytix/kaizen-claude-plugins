# Custom hook patterns — the composer the page consumes

The custom hook is the seam between the data layer and the page. It reads
from both RTK Query (server state) and the slice (client state), combines
them, and returns exactly what the page needs — nothing more.

```typescript
// hooks/useProducts.ts — the composer the page consumes
export function useProducts() {
  const dispatch = useAppDispatch();
  const { search } = useAppSelector((s) => s.products.filters);
  const { data, isLoading, isError } = useGetProductsQuery({ page: 1, limit: 20 });
  const products = data?.items.filter((p) => p.name.toLowerCase().includes(search.toLowerCase()));
  return { products: products ?? [], isLoading, isError, search,
           onSearch: (v: string) => dispatch(setSearchFilter(v)) };
}
```

## Why this shape matters

- The page (`ProductPage`, see `react-module-scaffold`) calls exactly this one
  hook and nothing else. It has zero knowledge of RTK Query, Redux, or how
  filtering is implemented.
- All derived data — here, filtering the fetched list by the search term —
  happens inside the hook, not in the page and not in the slice. The slice
  only stores the raw search string; the hook derives the filtered list.
- The hook's return shape is the actual contract with the page: it should
  read like a small, purpose-built API (`products`, `isLoading`, `isError`,
  `search`, `onSearch`) rather than exposing raw dispatch/selector plumbing.
- One hook per page/feature is the norm. If a page needs data from two
  domains, either compose two module hooks inside a page-specific hook, or
  (if this happens often) reconsider whether the domain boundary is right.

## Testing implication

Because all the logic lives in this hook, it can be unit-tested with
`renderHook` in isolation from any component tree — see `react-testing` for
the pattern, including how to wrap the hook in the store/query providers it
needs.
