# shadcn/ui setup and composition patterns

## Init workflow, expanded

```bash
npx shadcn@latest init
```

Prompts (typical defaults for this codebase):

- **Style**: `default` (or `new-york` if the project has already chosen it —
  don't mix styles within one project).
- **Base color**: pick once, keep it consistent (e.g. `slate`). **If the
  project already has a theme file, this choice is about to be overridden —
  read "Reconciling with an existing theme" below before running init.**
- **CSS variables**: yes — enables theming (light/dark) via CSS variables
  rather than hard-coded Tailwind color classes.
- **Tailwind config**: points at `tailwind.config.ts`; init appends the
  shadcn color/plugin config to whatever already exists.
- **Components alias**: `@/shared/components/ui` — this is the setting that
  makes generated components land in the `shared/` zone.
- **Utils alias**: `@/shared/lib/utils` — where `cn()` lives.

## `components.json` shape

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "default",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "src/app.css",
    "baseColor": "slate",
    "cssVariables": true
  },
  "aliases": {
    "components": "@/shared/components/ui",
    "utils": "@/shared/lib/utils"
  }
}
```

Point `tailwind.css` at whichever stylesheet is actually the project's theme —
`src/app.css` on a project scaffolded by `react-project-bootstrap`. On Tailwind
v4 the `config` key is vestigial (there is no `tailwind.config.ts`); leave it
or drop it, but don't create an empty config file to satisfy it.

This file is what `npx shadcn add <component>` reads to know where to write
new component source — don't hand-edit the aliases after other components
already depend on the old paths, or re-run `init` deliberately if paths
genuinely need to move.

## Reconciling with an existing theme

`shadcn init` writes its own colour variables into the CSS file. On a project
that already has a theme — anything created via a sibling
`architecture-foundations` plugin's `project-kickoff` skill, or styled by a
sibling `design-system` plugin's `tailwind-theme-setup` skill — that will
duplicate or clobber the token block.

The rule is that **the project's theme file wins**. shadcn's variables are
defaults meant to be replaced, not a second palette to maintain alongside.

- **Preferred order on a new project**: run `init` first, then apply the theme
  over it. The theme's values end up authoritative with nothing to untangle.
- **If init ran second** and has overwritten things: keep the project's token
  block and re-point shadcn's variable names at it rather than keeping the
  `slate` defaults. The mapping is mostly one-to-one:

  | shadcn variable | Project token |
  |---|---|
  | `--card`, `--popover` | `--surface` |
  | `--card-foreground`, `--popover-foreground` | `--surface-foreground` |
  | `--destructive` | `--danger` |
  | `--accent` | `--primary-subtle` |
  | `--muted`, `--border`, `--input`, `--ring`, `--primary`, `--secondary` | same names already |

- **Never keep two colour systems.** If both `--destructive` and `--danger`
  hold real values, some components are red-by-shadcn and others are
  red-by-token, and they will drift the first time either is adjusted.

One thing genuinely worth leaving alone: the Tailwind utility classes *inside*
vendored `shared/components/ui/*.tsx` files. They use built-in names like
`text-sm` and `sm:`, and those still resolve because the theme adds semantic
names rather than clearing the defaults. Rewriting vendored files to semantic
names only creates conflicts the next time a component is re-added.

## The `cn()` utility

`shared/lib/utils.ts`:

```typescript
import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- `clsx` handles conditional class composition (`cn('base', isActive && 'active')`).
- `twMerge` resolves conflicting Tailwind classes so a later override wins
  (e.g. `cn('p-2', someCondition && 'p-4')` correctly yields `p-4`, not both).

Every shadcn primitive uses `cn()` internally for its own class merging, and
every composite component that needs conditional styling should reuse it
rather than string-concatenating class names.

## Worked example: `Button` + `Dialog` → `ProductDeleteConfirm`

Primitives already exist from `npx shadcn@latest add button dialog`:
`shared/components/ui/button.tsx`, `shared/components/ui/dialog.tsx`.

Domain composite, `modules/products/components/ProductDeleteConfirm.tsx`:

```tsx
import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/shared/components/ui/dialog';
import { Button } from '@/shared/components/ui/button';
import type { Product } from '@/modules/products/types/product.types';

interface ProductDeleteConfirmProps {
  product: Product;
  onConfirm: (productId: string) => void;
}

export function ProductDeleteConfirm({
  product,
  onConfirm,
}: ProductDeleteConfirmProps) {
  const [open, setOpen] = useState(false);

  const handleConfirm = () => {
    onConfirm(product.id);
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="destructive" size="sm">
          Delete
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete {product.name}?</DialogTitle>
          <DialogDescription>
            This action cannot be undone. This will permanently remove the
            product from the catalog.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={handleConfirm}>
            Confirm delete
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

Notes on the pattern:

- `ProductDeleteConfirm` imports `Dialog`/`Button` from `shared/components/ui`
  — it never redefines modal or button markup itself.
- All domain knowledge (`Product`, the delete confirmation copy, the
  `onConfirm(productId)` callback) lives in the composite, not in the
  primitives.
- Focus trapping and `Escape`-to-close come for free from Radix's `Dialog`
  primitive — the composite doesn't need to implement either.
- This file lives in `modules/products/components/`, following the
  `react-naming-conventions` PascalCase rule, even though it's built almost
  entirely from `shared/` primitives.
