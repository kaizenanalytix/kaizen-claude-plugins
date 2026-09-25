# Naming cheatsheet

Quick lookup: case style, example, and the rule behind it, for every category
in the module skeleton (`components/pages/hooks/services/store/context/types`)
plus cross-cutting categories (folders, constants, tests).

| Category | Case style | Example | Rule |
|---|---|---|---|
| Component file | PascalCase | `ProductList.tsx` | File name matches the exported component name exactly. |
| Component (exported identifier) | PascalCase | `ProductList` | Matches its file name. |
| Page file | PascalCase + `Page` suffix | `ProductPage.tsx` | Named after the route it renders, not the action taken on it. |
| Page (add/edit variants) | PascalCase + `Page` suffix | `AddProductPage.tsx`, `EditProductPage.tsx` | Same rule; the verb describes the route, not a handler. |
| Hook file | camelCase + `use` prefix | `useProducts.ts` | One primary exported hook per file, named after what it returns/manages. |
| Hook (form-specific) | camelCase + `use` prefix | `useProductForm.ts` | Same rule, applied to form state/logic hooks. |
| Hook (exported identifier) | camelCase, `use...` | `useProducts` | Matches its file name. |
| Service / API slice file | camelCase + `Api` suffix | `productApi.ts` | RTK-Query-style API slice for one domain. |
| Store slice file | camelCase + `Slice` suffix | `productSlice.ts` | Client/UI state slice for one domain. |
| Context object file | PascalCase + `Context` suffix | `ProductContext.ts` | Only when the context object is separated from its provider component. |
| Context provider component | PascalCase (component rules apply) | `ProductProvider.tsx` | Normal component naming; not suffixed `Context`. |
| Types file | `<domain>.types.ts` (lowercase domain, dot-suffix) | `product.types.ts` | Co-located under `types/`, one file per domain. |
| Type / interface name | PascalCase, no Hungarian prefix | `Product` (not `IProduct`, not `TProduct`) | Never prefix with `I` or `T`. |
| Test file (colocated) | Same base name + `.test.ts(x)` | `ProductList.test.tsx` | Sits next to the file under test. |
| Test file (`__tests__/` variant) | Same base name + `.test.ts(x)`, inside `__tests__/` | `__tests__/ProductList.test.tsx` | Only for modules large enough that colocation clutters the folder; pick one convention per repo. |
| Folder (module or nested) | kebab-case | `product-catalog/` | Always kebab-case, even though files inside use PascalCase/camelCase. |
| True constant | SCREAMING_SNAKE_CASE | `MAX_PAGE_SIZE` | Reserved for values that never change at runtime. |
| Config object | camelCase | `defaultQueryConfig` | Used when grouping related settings into one object. |
| Barrel file (`index.ts` re-exporting a module) | N/A — disallowed | — | Never create one; import directly from the specific file. |

## Quick decision flow

1. Is it a file? Name it to match what it exports (component name, hook name,
   etc.) using the case style for that category above.
2. Is it a folder? kebab-case, no exceptions.
3. Is it a type/interface name? PascalCase, no `I`/`T` prefix.
4. Is it a value that never changes? SCREAMING_SNAKE_CASE. Otherwise camelCase.
5. Never write an `index.ts` that re-exports a module's internals.
