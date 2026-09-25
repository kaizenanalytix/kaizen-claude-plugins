# Module skeleton — copy-paste template

Use "ProductX" as the running example; rename `Product` → the actual domain
entity when scaffolding a real module. The point isn't the specific domain —
it's the shape: a thin page, a dumb component, and a hook that does the real
work (built out fully in `react-data-layer`).

```typescript
// pages/ProductPage.tsx — thin composer, no business logic
export default function ProductPage() {
  const { products, isLoading, isError, onSearch, search } = useProducts();
  if (isError) return <div>Failed to load products.</div>;
  return (
    <>
      <input value={search} onChange={(e) => onSearch(e.target.value)} placeholder="Search…" />
      <ProductList products={products} isLoading={isLoading} />
    </>
  );
}

// components/ProductList.tsx — dumb, renders props only
export function ProductList({ products, isLoading }: { products: Product[]; isLoading: boolean }) {
  if (isLoading) return <div>Loading…</div>;
  if (!products.length) return <div>No products found.</div>;
  return <ul>{products.map((p) => <ProductItem key={p.id} product={p} />)}</ul>;
}
```

## What each piece is responsible for

- `ProductPage` doesn't know *how* products are fetched, filtered, or how
  search state is stored — it only knows to call `useProducts()` and render
  the result. Swap the hook's internals (switch data sources, add pagination,
  change the store) and the page never has to change.
- `ProductList` doesn't know where `products` came from. It could be fed real
  data, mock data in a test, or Storybook fixtures — it just renders what it's
  given. This is what makes it trivially testable in isolation (see
  `react-testing`).
- The actual logic — the `useProducts` hook, the `productApi` service, the
  `productSlice` — is built out in full in `react-data-layer`. Scaffold the
  empty `hooks/`, `services/`, `store/` folders here, then hand off to that
  skill to fill them in.

## Full skeleton to create

```
modules/products/
  components/
    ProductList.tsx
    ProductItem.tsx
  pages/
    ProductPage.tsx
  hooks/
    useProducts.ts        # filled in by react-data-layer
  services/
    productApi.ts         # filled in by react-data-layer
  store/
    productSlice.ts       # filled in by react-data-layer
  context/                # only if needed — see react-module-context
  types/
    product.types.ts      # or import from generated api-contract types
```

Follow this same shape for any domain — an `orders` module gets
`OrderPage.tsx`, `OrderList.tsx`, `useOrders.ts`, and so on.
