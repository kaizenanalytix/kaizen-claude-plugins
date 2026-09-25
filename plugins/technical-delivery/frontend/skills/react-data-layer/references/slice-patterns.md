# Redux slice patterns — client/UI state only

A slice holds state the UI owns — filters, selection, wizard steps — never a
copy of an API response. If you're tempted to put `products: Product[]` in a
slice, stop: that belongs in the RTK Query cache (see
`references/rtk-query-patterns.md`), not here.

```typescript
// store/productSlice.ts — client/UI state only
export const productSlice = createSlice({
  name: 'products',
  initialState: { selectedProductId: null, filters: { search: '', isActive: null } },
  reducers: {
    selectProduct: (s, a: PayloadAction<number | null>) => { s.selectedProductId = a.payload; },
    setSearchFilter: (s, a: PayloadAction<string>) => { s.filters.search = a.payload; },
  },
});

export const { selectProduct, setSearchFilter } = productSlice.actions;
```

## What belongs in a client-state slice

- Filter/search values that drive a query's arguments.
- The currently selected item's id (not the item itself — look that up from
  the RTK Query cache by id).
- UI-only flags: is a modal open, which tab is active, which step of a wizard.
- Anything that needs to persist across a page unmount but isn't a server
  response.

## What does not belong here

- API response bodies or lists of entities — those live in the RTK Query
  cache and are read via the generated query hooks.
- Anything derived entirely from server data plus a filter — compute that in
  the composing hook (see `references/custom-hook-patterns.md`), don't store
  the derived result in the slice either.

## Store wiring

`productSlice.reducer` gets registered under its own key in
`core/store/store.ts`'s `configureStore` call, alongside `productApi.reducer`
— see the SKILL.md body for the full shape.
