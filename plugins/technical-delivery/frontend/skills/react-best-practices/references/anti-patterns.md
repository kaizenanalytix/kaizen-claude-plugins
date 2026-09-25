# React anti-patterns: bad vs. good

One before/after pair per rule from `SKILL.md`. Use these as copyable
templates when writing a review.

## 1. Rules of Hooks — hook after early return

```tsx
// Bad
function UserPanel({ userId }: { userId: string | null }) {
  if (!userId) return null;
  const [expanded, setExpanded] = useState(false); // conditional hook call
  return <Panel expanded={expanded} onToggle={() => setExpanded((e) => !e)} />;
}

// Good
function UserPanel({ userId }: { userId: string | null }) {
  const [expanded, setExpanded] = useState(false);
  if (!userId) return null;
  return <Panel expanded={expanded} onToggle={() => setExpanded((e) => !e)} />;
}
```

## 2. Impure render — side effect during render

```tsx
// Bad: fetches during render, mutates a prop
function ProductRow({ product }: { product: Product }) {
  product.viewedAt = Date.now(); // mutating a prop directly
  fetch(`/api/track-view/${product.id}`); // side effect during render
  return <li>{product.name}</li>;
}

// Good: side effect moved to an effect (or better, a data-layer hook)
function ProductRow({ product }: { product: Product }) {
  useEffect(() => {
    trackProductView(product.id);
  }, [product.id]);
  return <li>{product.name}</li>;
}
```

## 3. Over-memoization without profiling evidence

```tsx
// Bad: memoizing everything preemptively, no measured problem
const ProductCard = React.memo(function ProductCard({ product }: Props) {
  const formattedPrice = useMemo(() => formatPrice(product.price), [product.price]);
  const handleClick = useCallback(() => onSelect(product.id), [product.id]);
  return <div onClick={handleClick}>{formattedPrice}</div>;
});

// Good: plain component; memoize only after profiling shows this
// specific render is expensive and re-runs unnecessarily
function ProductCard({ product, onSelect }: Props) {
  const formattedPrice = formatPrice(product.price); // cheap, just compute it
  return <div onClick={() => onSelect(product.id)}>{formattedPrice}</div>;
}
```

## 4. Index keys on a reorderable list

```tsx
// Bad: index key breaks when the list is filtered/reordered
{products.map((product, index) => (
  <ProductRow key={index} product={product} />
))}

// Good: stable id key
{products.map((product) => (
  <ProductRow key={product.id} product={product} />
))}
```

## 5. Derived state via `useState` + `useEffect`

```tsx
// Bad: syncing derived state with an effect
function ProductSummary({ items }: { items: LineItem[] }) {
  const [total, setTotal] = useState(0);
  useEffect(() => {
    setTotal(items.reduce((sum, item) => sum + item.price, 0));
  }, [items]);
  return <p>Total: {total}</p>;
}

// Good: compute directly during render
function ProductSummary({ items }: { items: LineItem[] }) {
  const total = items.reduce((sum, item) => sum + item.price, 0);
  return <p>Total: {total}</p>;
}

// Good, if the computation is genuinely expensive
function ProductSummary({ items }: { items: LineItem[] }) {
  const total = useMemo(
    () => items.reduce((sum, item) => sum + item.price, 0),
    [items],
  );
  return <p>Total: {total}</p>;
}
```

## 6. Missing error boundary

```tsx
// Bad: one module's render error blanks the entire app
function AppRouter() {
  return (
    <Routes>
      <Route path="/products" element={<ProductPage />} />
      <Route path="/orders" element={<OrderPage />} />
    </Routes>
  );
}

// Good: app-wide boundary around the router, in core/
function AppRouter() {
  return (
    <ErrorBoundary fallback={<AppErrorFallback />}>
      <Routes>
        <Route path="/products" element={<ProductPage />} />
        <Route path="/orders" element={<OrderPage />} />
      </Routes>
    </ErrorBoundary>
  );
}
```

## 7. Accessibility — clickable `div` instead of a real element

```tsx
// Bad: not focusable, not announced as interactive, no keyboard support
<div onClick={handleDelete} className="delete-icon">
  Delete
</div>

// Good: a real button, natively focusable and keyboard-operable
<button type="button" onClick={handleDelete}>
  Delete
</button>
```

## 8. Accessibility — input without a label

```tsx
// Bad: placeholder is not a substitute for a label
<input placeholder="Product name" onChange={handleChange} />

// Good
<label htmlFor="product-name">Product name</label>
<input id="product-name" onChange={handleChange} />
```

## 9. Mixing controlled and uncontrolled inputs

```tsx
// Bad: value is controlled, but defaultValue is also set — React warns
// and behavior becomes inconsistent between renders
<input value={name} defaultValue="Untitled" onChange={(e) => setName(e.target.value)} />

// Good: fully controlled
<input value={name} onChange={(e) => setName(e.target.value)} />

// Good: fully uncontrolled, read via ref only on submit
<input ref={nameRef} defaultValue="Untitled" />
```
