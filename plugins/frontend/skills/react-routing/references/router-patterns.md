# Router patterns

## Lazy-loaded pages

Every page component imported into the router is loaded via `React.lazy`,
never eagerly:

```typescript
const ProductPage = lazy(() => import('@/modules/products/pages/ProductPage'));
```

This gives each module its own code-split chunk, so a user visiting `/orders`
never downloads the `products` module's JavaScript.

## Auth via `PrivateRoute`

Wrap the routes that require authentication in a parent route using a
`PrivateRoute` wrapper component, rather than checking auth state inside each
individual page:

```typescript
// <Route element={<PrivateRoute />}>
//   <Route path="/products" element={<ProductPage />} />
// </Route>
```

`PrivateRoute` itself typically renders `<Outlet />` when authenticated and a
`<Navigate to={ROUTES.LOGIN} />` otherwise — implement it once in `core/`
(it's a routing concern, not a module concern) and reuse it for every
protected route tree.

## Path constants

Declare paths once instead of scattering string literals:

```typescript
export const ROUTES = {
  PRODUCTS: '/products',
  PRODUCT_DETAIL: '/products/:id',
  LOGIN: '/login',
} as const;
```

Use `ROUTES.PRODUCTS` in the route definition, in `<Link to={ROUTES.PRODUCTS}>`,
and in any `navigate(ROUTES.PRODUCTS)` call. This is what prevents a path
rename from silently breaking a `<Link>` somewhere that didn't get updated.

## Typed URL params

```typescript
function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  // id: string | undefined — narrow before using
}
```

Always type `useParams` explicitly with the param shape the route actually
declares, rather than leaving it untyped and accessing properties that may
not exist.

## Suspense boundary

Because every page is lazy, the route tree needs a `Suspense` boundary so
navigation shows a fallback instead of a blank screen while the chunk loads:

```typescript
<Suspense fallback={<PageLoadingSpinner />}>
  <Routes>
    <Route element={<PrivateRoute />}>
      <Route path={ROUTES.PRODUCTS} element={<ProductPage />} />
    </Route>
    <Route path={ROUTES.LOGIN} element={<LoginPage />} />
  </Routes>
</Suspense>
```
