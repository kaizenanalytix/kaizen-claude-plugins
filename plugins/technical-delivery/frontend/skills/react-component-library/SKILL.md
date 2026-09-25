---
name: react-component-library
description: >
  Standardizes on shadcn/ui (Radix primitives + Tailwind CSS, copy-paste
  owned source) for generic UI components in `shared/components/ui/`, and
  adapts to whatever primitive layer a project already owns. Use when the user
  says things like "add a UI component", "install a component", "add a
  button", "add a modal", "add a form", "add a table", "add a dropdown",
  "add a tooltip", "we need a date picker", "set up shadcn", or "which
  component library".
---

# React Component Library (shadcn/ui)

Apply this skill whenever a generic, non-domain UI primitive is needed —
buttons, dialogs, dropdowns, form inputs, toasts, tooltips, and similar. This
codebase standardizes on **shadcn/ui**: Radix UI primitives styled with
Tailwind CSS, distributed as source you copy into the repo and own, not an
npm black-box package you import and can't edit.

## 1. Why shadcn fits this architecture

One sentence of the model this depends on: the three-zone model
(`frontend-architecture`) puts reusable, business-logic-free code in
`shared/`. shadcn components carry zero domain logic by design, so they
belong in `shared/components/ui/` — never in a `modules/<domain>/components/`
folder. Domain-specific composite components (e.g. `ProductCard`,
`ProductDeleteConfirm`) still live in `modules/<domain>/components/`, but
they're built **by composing shadcn primitives**, not by hand-rolling raw
`<div>`/`<button>` markup.

## 2. One-time setup

Check whether `components.json` exists at the project root — that's the
signal shadcn has already been initialized.

**If it doesn't, check what the project uses instead before running `init`.** A
project can already own a full primitive layer without shadcn — Radix plus
`cva()` directly, or a hand-built `components/ui/` folder. Running `shadcn init`
there adds a second, competing set of primitives and a colour config that fights
the existing theme. Look for a `components/ui/` directory, `@radix-ui/*` or
`class-variance-authority` in `package.json`, and match what's there instead:
the composition rules in sections 4 and 5 apply to any owned primitive layer,
shadcn-generated or not.

Only run `init` when there is genuinely no primitive layer yet:

```bash
npx shadcn@latest init
```

This sets up `components.json` (paths + style config), configures Tailwind,
and drops `shared/lib/utils.ts` containing the `cn()` classname helper
(`clsx` + `tailwind-merge`) that every shadcn component uses internally and
that composite components should reuse for conditional classes.

Only run `init` once per project. If the project doesn't exist yet, hand off
to `react-project-bootstrap` first.

**If the project already has a theme file**, `init` will write its own colour
variables over it. Read `references/shadcn-setup.md`'s "Reconciling with an
existing theme" section before running the command — the project's tokens are
authoritative, and shadcn's `slate` defaults are meant to be replaced rather
than maintained alongside them.

## 3. Adding a primitive

```bash
npx shadcn@latest add button dialog dropdown-menu
```

Each name added drops an owned, editable source file into
`shared/components/ui/` (e.g. `shared/components/ui/button.tsx`). Nothing is
installed as an opaque dependency — the component's source is now part of
this codebase.

## 4. Decision rule: new primitive vs. compose existing ones

Before running `add`, check `shared/components/ui/` for something that
already covers the need:

- An existing primitive covers it (even if styling needs a tweak) → edit that
  file directly, or compose it into a domain component. Don't re-add it.
- A composite UI need (e.g. "a confirm-delete dialog") is really an existing
  primitive (`Dialog`) plus domain content → build it as a composite
  component in `modules/<domain>/components/`, don't add a new primitive.
- A genuinely new primitive category is needed (e.g. no `Tooltip` exists yet
  and one is needed) → run `add` for that one category only.

## 5. Editing owned components

Because the code is copy-paste/owned (not a versioned dependency), make
one-off styling tweaks by editing the file in `shared/components/ui/`
directly rather than fighting an unmodifiable package API — that's the point
of shadcn's distribution model.

Do **not**, without a good reason:
- Rename a generated file (`button.tsx` staying `button.tsx`).
- Change a generated component's exported prop API (e.g. renaming `variant`
  or removing a prop `Button` is documented to support).

Other shadcn components (e.g. `AlertDialog` internally using `Button`) and
any future `npx shadcn add` re-run both assume the default file name and
shape. Renaming or reshaping breaks that assumption silently.

## 6. Composing a domain component from primitives

Read `references/shadcn-setup.md` for the expanded init workflow, the
`components.json` shape, the `cn()` pattern, and a full worked example
composing `Button` + `Dialog` into a domain-specific
`ProductDeleteConfirm` component — use that file as the concrete template
for "shared primitive → domain composite."

## 7. Accessibility note

Prefer shadcn/Radix primitives over hand-rolled interactive elements
(`<div onClick>`, custom modal markup) because Radix already handles focus
trapping, `Escape`-to-close, and ARIA attributes correctly — see
`react-best-practices` for the accessibility baseline this satisfies.

---
_Last reviewed: 2026-08-11_
