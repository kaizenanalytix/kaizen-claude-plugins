---
name: react-project-bootstrap
description: >
  Stands up a greenfield Vite + React + TypeScript project pre-configured for
  the three-zone architecture, RTK Query, typed routing, and the full test
  pyramid. Use when the user says things like "new React project", "set up
  the project", "configure vite/tsconfig", or "start a new frontend from
  scratch".
---

# React Project Bootstrap

Use this skill when starting a brand-new React project, so it's pre-wired
for the conventions the other six skills in this plugin assume already
exist. One sentence of the model this depends on: the project ends up laid
out as `core/` / `modules/` / `shared/` per the three-zone model — see
`frontend-architecture` for the full model once the project exists.

## 1. When to use this vs. the other skills

If a React project already exists, don't use this skill — use a sibling
`architecture-foundations` plugin's `existing-codebase-adoption` skill first
to decide whether Kaizen's conventions or the project's existing structure
govern, then `frontend-architecture` to assess its current structure, or the
specific skill for whatever's being added. This skill is only for genuinely
new projects.

On a genuinely new project, this skill is normally reached *through* a sibling
`architecture-foundations` plugin's `project-kickoff` skill, which runs the
design system first and this scaffold second. If the user came straight here
instead, that's fine — but the theme still has to exist before components do,
so either route through `project-kickoff` or apply a sibling `design-system`
plugin's `tailwind-theme-setup` skill as part of step 2 below. Don't defer it;
retrofitting a token system into components that already exist is a migration,
not a config change.

## 2. Scaffold the project

Create the project with Vite's React + TypeScript template, then replace its
generated config files with the versions below so the project starts with
this plugin's conventions already in place rather than Vite's defaults:

- `vite.config.ts` — copy `assets/vite.config.ts`. It configures the React
  plugin and a `@ → src` path alias, so every skill's `@/modules/...` and
  `@/...` imports resolve correctly. A sibling `vite-config-basics` skill in
  this plugin covers the general config shape and reasoning
  framework-neutrally; this asset is that shape with the React plugin already
  slotted in.
- `.env`, `.env.development`, etc. — a sibling `vite-env-variables` skill
  covers the `VITE_`-prefix convention and per-environment file naming; apply
  it once the project needs environment-specific config, not necessarily at
  bootstrap time.
- `tsconfig.json` — copy `assets/tsconfig.json`. It enables strict mode and
  mirrors the same `@/*` path alias for TypeScript's module resolution, so
  imports type-check the same way they resolve at build time.
- `package.json` — copy `assets/package.json` as a starting point, then
  merge in any project-specific metadata (name, etc.) rather than
  overwriting it wholesale if one already exists. It includes Redux Toolkit
  (for `react-data-layer`), React Router (for `react-routing`), React
  Testing Library + MSW (for `react-testing`'s unit/integration layers —
  no `@playwright/test` here; a sibling `e2e-testing` plugin's
  `playwright-project-structure` skill owns that dependency and installs it
  itself, the one time a project actually needs a browser-driven test),
  Tailwind CSS + `clsx` + `tailwind-merge` (for the theme below and for
  `react-component-library`'s `cn()` helper), Vite, and TypeScript.
- `src/app.css` — the theme. A sibling `design-system` plugin's
  `tailwind-theme-setup` skill owns this file's contents; if that plugin isn't
  installed, still create a single central stylesheet defining the type scale,
  colours by role, and spacing before writing any component. Tailwind is now a
  real dependency of this scaffold rather than something `shadcn init` installs
  as a side effect, so the theme exists from the first commit.

## 3. Create the initial folder skeleton

After the base project is scaffolded, create the three top-level zones under
`src/` even before any module exists:

```
src/
  core/
    router/
    store/
    providers/
  modules/
  shared/
```

Don't populate `modules/` yet — that's what `react-module-scaffold` is for,
once there's an actual domain to scaffold.

## 4. Wire the minimal `core/`

Set up a minimal `core/store/store.ts` (an empty `configureStore({ reducer:
{} })` to start, ready for modules to register into), a minimal
`core/router/AppRouter.tsx` (a `<Suspense>`-wrapped `<Routes>` with just a
placeholder or landing route), and `core/providers/AppProviders.tsx`
(wrapping the app in `<Provider store={store}>`, a router provider, and any
top-level theming). These get filled in further as `react-data-layer` and
`react-routing` are used to add real modules.

Import the theme **once**, at the entry point — `import '@/app.css'` at the top
of `main.tsx`. Never per-component: a second import point is how two competing
sources of tokens start.

If a theme toggle is wanted, `AppProviders.tsx` is where it belongs — it adds
or removes the `dark` class on `<html>`. The token values themselves stay in
`app.css`; the provider only decides which set is active.

## 5. Sanity check before finishing

Once the scaffold is complete, **ask before running these** — don't start a dev
server or a build unprompted. A sibling `architecture-foundations` plugin's
`working-agreement` skill covers why verification is batched and asked for; if
that plugin isn't installed, the rule still stands on its own here.

- Run the project's dev server once to confirm the Vite config and path
  alias actually resolve.
- Confirm `tsc --noEmit` (or the project's type-check script) passes on the
  freshly generated skeleton.
- Confirm `react`, `@reduxjs/toolkit`, `react-router-dom`, `vitest`,
  `@testing-library/react`, and `msw` are all present in `package.json` so
  the other six skills' stack checks pass immediately. `@playwright/test` is
  deliberately not part of this baseline — see step 2 above.
- Confirm the theme is actually live, not merely present: render one element
  with a semantic class from the type scale (e.g. `text-page-title`) and check
  it computes to the expected pixel size. A theme file that isn't wired into
  the build fails silently — the classes exist and do nothing.

---
_Last reviewed: 2026-08-17_
