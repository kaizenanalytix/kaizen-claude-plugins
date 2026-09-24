---
name: react-naming-conventions
description: >
  Applies a concrete file- and identifier-naming standard for a React
  module's components/pages/hooks/services/store/context/types. Use when the
  user says things like "what should I name this file", "naming convention",
  "file naming", "how do I name this component/hook", or "what case should
  this be".
---

# React Naming Conventions

Apply this skill whenever a file, folder, or identifier needs a name inside
`modules/<domain>/` or `shared/`. One sentence of the model this depends on:
the seven-folder module skeleton from `react-module-scaffold`
(components/pages/hooks/services/store/context/types) — this skill only
covers what to *call* the files inside it, not the folder structure itself.

## 1. The core rule: file name matches export name

A file's name always matches the name of the thing it exports by default.
Never leave a mismatch like a file `list.tsx` exporting `ProductList` — rename
the file to `ProductList.tsx`. This single rule resolves most naming
questions; everything below is the category-specific spelling of it.

## 2. Category-by-category rules

- **Components** (`components/`): PascalCase, matching the exported
  component name exactly — `ProductList.tsx` exports `ProductList`. Default
  to one component per file; don't bury a second exported component in the
  same file just because it's small.
- **Pages** (`pages/`): PascalCase, suffixed `Page` — `ProductPage.tsx`,
  `AddProductPage.tsx`, `EditProductPage.tsx`. Name a page after the route it
  renders, not after the action a user takes inside it.
- **Hooks** (`hooks/`): camelCase, prefixed `use` — `useProducts.ts`,
  `useProductForm.ts`. One primary exported hook per file. Name the hook
  after what it returns or manages (`useProducts` returns product data),
  never after the component that happens to call it (`useProductPageLogic`
  is wrong).
- **Services** (`services/`): camelCase, suffixed `Api` for RTK-Query-style
  API slices — `productApi.ts`.
- **Store slices** (`store/`): camelCase, suffixed `Slice` —
  `productSlice.ts`.
- **Context** (`context/`): PascalCase, suffixed `Context` for the context
  object file itself when it's separated from its provider component —
  `ProductContext.ts` (provider component, if separate, is a normal
  PascalCase component file, e.g. `ProductProvider.tsx`).
- **Types** (`types/`): co-located in `types/`, file named
  `<domain>.types.ts` — `product.types.ts`. A type or interface name is
  PascalCase with no Hungarian prefix: `Product`, never `IProduct` or
  `TProduct`.
- **Constants**: SCREAMING_SNAKE_CASE for true constants (`MAX_PAGE_SIZE`);
  camelCase for config objects that group related settings.

Read `references/naming-cheatsheet.md` for the full case-style table across
every category — use it as a quick lookup instead of re-reading this section.

## 3. Test files

Colocate a test file next to the file it tests, with a `.test.ts` /
`.test.tsx` suffix and the same base name — `ProductList.test.tsx` next to
`ProductList.tsx`. For a module large enough that colocated tests clutter the
folder, a sibling `__tests__/` directory is acceptable instead — but pick one
convention per repo and apply it consistently; don't mix colocated and
`__tests__/` within the same module. Default to colocated `.test.tsx` unless
the user has already stated a different preference for this project. See
`react-testing` for what belongs in the test itself.

## 4. Folders are always kebab-case

Directory names are kebab-case even though the files inside use
PascalCase/camelCase per the rules above: `product-catalog/`, never
`ProductCatalog/` or `productCatalog/`. This applies to module folders
(`modules/product-catalog/`) and any nested folder.

## 5. No barrel files

Don't create a top-level `index.ts` in a module (or component folder) that
re-exports everything inside it. This is a rule, not a style preference:
barrel files hide the real import path (harder to trace where something
actually lives) and are a common source of circular-import bugs when two
modules both re-export through their barrels. Import directly from the
specific file instead:

```typescript
// Do this:
import { ProductList } from '@/modules/products/components/ProductList';

// Not this:
import { ProductList } from '@/modules/products';
```

## 6. When reviewing existing code

If asked to review or clean up a module's naming, walk the seven folders in
order (components, pages, hooks, services, store, context, types), check
each file against the matching rule above, and flag mismatches by name (old
name → new name) rather than silently renaming — a rename can break imports
elsewhere that need to be updated together with it.

---
_Last reviewed: 2026-08-05_
