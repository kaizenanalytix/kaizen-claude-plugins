# Component composition decision tree and worked examples

## Flowchart-as-text

```
1. Have you seen this exact shape (markup or logic) before?
   - No, this is the 1st occurrence
     -> Does it already share business meaning with something that exists
        (same domain concept, same reason to change)?
        - Yes -> extract now (skip the rule of three). Go to step 3.
        - No  -> ship it inline. Stop.
   - Yes, this is the 2nd occurrence
     -> Same question: shared business meaning, or just visual resemblance?
        - Shared meaning -> extract now. Go to step 3.
        - Just resemblance -> leave both inline. Note it mentally, don't
          extract yet. Stop.
   - Yes, this is the 3rd+ occurrence (rule of three triggered)
     -> Go to step 2.

2. Is the resemblance business meaning or coincidence?
   - Coincidence (different domains, different reasons to change, might
     diverge) -> leave duplicated. See Example 3. Stop.
   - Business meaning (same concept, same reason to change) -> go to step 3.

3. What's actually shared: markup, logic, or both?
   - Markup + a bit of logic, one owner of behavior
     -> Extract a component. Prefer composition (children / named slot
        props) over boolean props that toggle internal JSX.
   - Logic only (fetching, event handling, derived values); markup differs
     -> Extract a custom hook. Do not force a shared component with a
        render prop just to reuse the logic.
   - Both markup and logic, but one side needs to control content while the
     other controls structure (a wrapper + slot situation)
     -> Extract a component using children/named slots. Do not add a
        boolean prop (`showFooter`, `variant="withHeader"`) per case.

4. Does the shared thing get used outside the current module?
   - No, only this module uses it -> keep it in
     `modules/<domain>/components/` or `modules/<domain>/hooks/`.
   - Yes, another module needs it too
     -> Is it still domain-specific (knows about `Product`, `Order`, etc.)?
        - Yes -> it does NOT belong in `shared/`. Either duplicate it in
          each module (see step 2) or find the truly generic primitive
          underneath it and promote only that (see react-component-library).
        - No, it's generic (no business logic) -> promote to
          `shared/components/ui/` or `shared/hooks/`.

5. Is a render prop or HOC being considered?
   - Only if a third-party library's API requires it -> use it, scoped to
     that integration point.
   - Otherwise -> use a custom hook + composition instead.
```

## Example A: prop explosion → composition via `children`

**Before** — a `Panel` component that grew a boolean/enum prop for every
new caller's needs instead of letting callers compose their own content:

```tsx
// modules/products/components/ProductPanel.tsx — premature abstraction
interface ProductPanelProps {
  title: string;
  product: Product;
  showFooter?: boolean;
  footerVariant?: 'actions' | 'summary';
  showBadge?: boolean;
  badgeText?: string;
  compact?: boolean;
}

export function ProductPanel({
  title,
  product,
  showFooter,
  footerVariant,
  showBadge,
  badgeText,
  compact,
}: ProductPanelProps) {
  return (
    <div className={compact ? 'panel panel--compact' : 'panel'}>
      <div className="panel-header">
        {title}
        {showBadge && <span className="badge">{badgeText}</span>}
      </div>
      <div className="panel-body">{product.description}</div>
      {showFooter &&
        (footerVariant === 'actions' ? (
          <div className="panel-footer">
            <button onClick={() => {}}>Edit</button>
            <button onClick={() => {}}>Delete</button>
          </div>
        ) : (
          <div className="panel-footer">{product.updatedAt}</div>
        ))}
    </div>
  );
}
```

Every new caller needing slightly different footer content adds another
prop. None of these props share real behavior — they only toggle which JSX
renders, which is the prop-explosion smell called out in the main skill.

**After** — composition via `children` and named slot props; the wrapper
controls structure, callers control content:

```tsx
// shared/components/ui/panel.tsx — generic, no product knowledge
interface PanelProps {
  header: React.ReactNode;
  footer?: React.ReactNode;
  compact?: boolean;
  children: React.ReactNode;
}

export function Panel({ header, footer, compact, children }: PanelProps) {
  return (
    <div className={compact ? 'panel panel--compact' : 'panel'}>
      <div className="panel-header">{header}</div>
      <div className="panel-body">{children}</div>
      {footer && <div className="panel-footer">{footer}</div>}
    </div>
  );
}

// modules/products/components/ProductPanel.tsx — domain composite
export function ProductPanel({ product }: { product: Product }) {
  return (
    <Panel
      header={
        <>
          {product.name}
          {product.isNew && <span className="badge">New</span>}
        </>
      }
      footer={
        <>
          <button onClick={() => {}}>Edit</button>
          <button onClick={() => {}}>Delete</button>
        </>
      }
    >
      {product.description}
    </Panel>
  );
}
```

`Panel` has zero business logic and lives in `shared/`; `ProductPanel`
supplies all the domain content and stays in `modules/products/`. Each
caller decides its own header/footer content instead of adding a prop to
`Panel` for every variation.

## Example B: same logic, different markup → extract a custom hook

**Before** — two components independently re-implement the same
fetch-sort-filter logic because they render it differently:

```tsx
// modules/products/components/ProductTable.tsx
function ProductTable({ categoryId }: { categoryId: string }) {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProducts(categoryId)
      .then((data) => setProducts(data.filter((p) => p.inStock)))
      .finally(() => setLoading(false));
  }, [categoryId]);

  if (loading) return <Spinner />;
  return (
    <table>
      {products.map((p) => (
        <tr key={p.id}>
          <td>{p.name}</td>
          <td>{p.price}</td>
        </tr>
      ))}
    </table>
  );
}

// modules/products/components/ProductGrid.tsx
function ProductGrid({ categoryId }: { categoryId: string }) {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProducts(categoryId)
      .then((data) => setProducts(data.filter((p) => p.inStock)))
      .finally(() => setLoading(false));
  }, [categoryId]);

  if (loading) return <Spinner />;
  return (
    <div className="grid">
      {products.map((p) => (
        <ProductCard key={p.id} product={p} />
      ))}
    </div>
  );
}
```

The markup is completely different (table vs. grid), but the data logic —
fetch, filter to in-stock, track loading — is identical. This is the
"components look different but do the same three things internally" case:
extract a hook, not a shared component.

**After**:

```tsx
// modules/products/hooks/useInStockProducts.ts
export function useInStockProducts(categoryId: string) {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchProducts(categoryId)
      .then((data) => setProducts(data.filter((p) => p.inStock)))
      .finally(() => setLoading(false));
  }, [categoryId]);

  return { products, loading };
}

// modules/products/components/ProductTable.tsx
function ProductTable({ categoryId }: { categoryId: string }) {
  const { products, loading } = useInStockProducts(categoryId);
  if (loading) return <Spinner />;
  return (
    <table>
      {products.map((p) => (
        <tr key={p.id}>
          <td>{p.name}</td>
          <td>{p.price}</td>
        </tr>
      ))}
    </table>
  );
}

// modules/products/components/ProductGrid.tsx
function ProductGrid({ categoryId }: { categoryId: string }) {
  const { products, loading } = useInStockProducts(categoryId);
  if (loading) return <Spinner />;
  return (
    <div className="grid">
      {products.map((p) => (
        <ProductCard key={p.id} product={p} />
      ))}
    </div>
  );
}
```

Both components keep their own markup entirely; only the logic moved. The
hook lives in `modules/products/hooks/` since only this module uses it —
not `shared/`, since it embeds domain logic (`inStock` filtering,
`fetchProducts`).

## Example C: legitimate duplication — leave it alone

```tsx
// modules/checkout/components/AddressForm.tsx
// NOTE: This looks identical to modules/shipping/components/AddressForm.tsx
// today (same fields, same layout). Do NOT extract into a shared component.
// Checkout's address validation will diverge from shipping's once
// PO-box restrictions and billing/shipping-match rules land here — see the
// checkout module's ticket backlog. Extracting now would couple two domains
// that have no real reason to change together, which is worse than the
// short-term duplication.
export function AddressForm({ onSubmit }: { onSubmit: (a: Address) => void }) {
  // checkout-specific fields and validation
  return <form>{/* ... */}</form>;
}
```

The two `AddressForm` components share structure by coincidence, not by
business meaning — per step 2 of the decision tree, that's a signal to
leave them duplicated, not to extract. The comment records *why*, so a
future reviewer doesn't "fix" this into an over-DRY merge.
