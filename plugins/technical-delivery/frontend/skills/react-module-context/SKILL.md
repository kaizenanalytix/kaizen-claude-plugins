---
name: react-module-context
description: >
  Applies the props vs. module-context vs. store decision rule and provides a
  safe, memoized module-scoped React Context factory. Use when the user says
  things like "share state across the module", "avoid prop drilling",
  "module-scoped context", "Context vs store", or "this component needs data
  from way up the tree".
---

# React Module Context

Use this skill when someone wants to share state across a module's component
subtree without prop drilling, or is unsure whether to reach for Context or
the store. One sentence of the model this depends on: modules are
self-contained per-domain folders under `modules/<name>/`, per the three-zone
model — see `frontend-architecture` if the actual question is about overall
structure.

## 1. Apply the decision rule first

Before writing any Context code, confirm Context is actually the right tool.
Apply this rule, in order:

1. **Outlives the screen, or needed app-wide** → put it in the **Store**
   instead (see `react-data-layer`). Don't use Context for this.
2. **Needed only within one module's subtree, by descendants several levels
   down** → **Module Context**. Keep reading.
3. **Otherwise — parent owns it, child is 1-2 levels down** → **Props**. This
   is the default and covers roughly 80% of cases. If props would work, use
   props; don't reach for Context just to avoid two prop declarations.

## 2. The critical caveat: Context is a transport, not a state manager

React Context does not do selective re-rendering. Every component that calls
`useContext` on a given context re-renders whenever that context's value
changes, regardless of which part of the value it actually reads. This makes
Context a poor fit for anything that changes frequently (keystrokes, mouse
position, frequently-ticking data) — for that, use the store, which supports
selector-based subscriptions.

Because of this:

- Only use module Context for **low-frequency** state (a wizard step, an
  active tab, a "currently editing" flag) — not for anything that updates on
  every render or every keystroke.
- Back the context's value with `useState` or `useReducer` inside the
  provider component, same as you would for any other piece of local state.
- **Memoize the value** passed to the provider (`useMemo`) so that unrelated
  re-renders of the provider component don't force every consumer to
  re-render for no reason.

## 3. Use the safe context factory

Don't hand-write `createContext` + a raw `useContext` call at each module —
copy the small factory in `assets/createModuleContext.ts`. It gives you a
provider and a hook that throws a clear error if used outside its provider,
instead of silently returning `null` or `undefined` and failing later with a
confusing error somewhere deep in a render.

```typescript
const [ProductWizardProvider, useProductWizard] = createModuleContext<ProductWizardState>('ProductWizard');
```

## 4. Mount the provider at the module's page boundary

The provider goes where the module's page renders — for example, wrapping the
JSX returned by `pages/ProductWizardPage.tsx` — never inside the app-wide
`core/providers/AppProviders.tsx` file. `core/` providers are for genuinely
app-wide concerns (theme, top-level auth, the query client); a module context
provider mounting there would make it globally available and defeat the point
of scoping it to the module.

```typescript
// pages/ProductWizardPage.tsx
export default function ProductWizardPage() {
  const value = useMemo(() => ({ step, setStep }), [step]);
  return (
    <ProductWizardProvider value={value}>
      <WizardSteps />
    </ProductWizardProvider>
  );
}
```

## 5. Naming and location

Put the context and its hook in `modules/<name>/context/`, named after what
it provides (e.g. `ProductWizardContext.tsx`), not generically `Context.tsx`.
Only create this folder when a module actually needs it — it's optional, per
`react-module-scaffold`'s skeleton.

---
_Last reviewed: 2026-08-05_
