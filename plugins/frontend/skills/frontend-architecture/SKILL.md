---
name: frontend-architecture
description: >
  Translates the framework-neutral UI architecture (core/modules/shared) into
  React-specific vocabulary and routes to the right React specialist skill in
  this plugin. Use when the user says things like "structure my frontend",
  "where does this UI code belong", "set up the app architecture", "how
  should I organize this React app", or "is this the right place for this
  file", on a project that is confirmed to be React.
---

# Frontend Architecture (React Adapter)

This skill is the React-specific translator and traffic-director for the
other 10 skills in this plugin. It is deliberately thin: the architectural
reasoning itself lives one plugin over, in a sibling `architecture-foundations`
plugin's `ui-architecture` skill (framework-neutral UI shape) and
`clean-architecture` skill (framework-neutral, any-app shape). This skill's
only job is to confirm React, translate the neutral vocabulary into React's
real vocabulary, and hand off.

## 0. Consult the codebase map first

If a sibling `codebase-map` plugin is installed, ask its `codebase-map-sync`
skill for cached facts about this repo before doing anything below yourself —
it already knows the stack, module list, and whether the frontend code
predates this plugin, refreshed cheaply via a checkpoint rather than a full
re-read. If that plugin isn't installed, fall through to step 1's own live
checks; nothing here requires it.

## 1. Profile the stack — not just "is this React"

"Has a `react` dependency" is nowhere near enough to route on. A Next.js app, a
React Router framework-mode app, and a Remotion video project all have `react` in
`package.json` and need almost entirely different advice. Read `package.json` and
record four facts before touching anything:

| Fact | Look for | Why it changes the answer |
|---|---|---|
| **Is it a web app at all?** | `remotion`, `react-native`, `ink`, a `main`/`exports` field with no app entry | A Remotion video project or a component library isn't a UI app. Most of this plugin doesn't apply. |
| **Meta-framework** | `next`, `@react-router/dev`, `@remix-run/*`, else plain Vite/CRA | Decides whether file location *is* routing, and whether `core/router/` even exists as a concept. |
| **Router** | `react-router-dom` (library mode) vs `react-router` + `routes.ts` (framework mode) vs Next's file router vs **none** | `react-routing` assumes library mode with a central route table. |
| **Server-state layer** | `@reduxjs/toolkit`, `@tanstack/react-query`, `zustand`, `swr`, or none | `react-data-layer` assumes RTK Query. |

State what you found in one line before proceeding — the user should be able to
catch a misread before advice is built on it. For example: *"Next.js 15 App
Router, Zustand, no RTK Query — so the routing and data-layer skills don't apply
as written; here's the equivalent."*

**Then route on it:**

- **Not a React project at all** → say so and stop. These conventions are
  React-specific.
- **React but not a web app** (Remotion, React Native, a published component
  library) → say so and stop before applying any of section 2. The three-zone
  model assumes an application with pages and routes; a video composition or a
  library has neither.
- **Project doesn't exist yet** → route to `react-project-bootstrap`. It builds
  the stack the table in section 2 assumes, so everything downstream lines up by
  construction.
- **Project exists and predates this plugin** → route to a sibling
  `architecture-foundations` plugin's `existing-codebase-adoption` skill first. It
  decides whether Kaizen's conventions or the existing structure govern before any
  further routing happens.
- **Project exists on a different stack than section 2 assumes** → this is the
  common case, not the exception. Keep the *principles* (the server-state /
  client-state split, thin pages, dumb components, one hook per page) and
  translate them into the libraries actually present. Do not propose migrating a
  working app to RTK Query or React Router because a skill mentions them. Each
  specialist skill below carries its own guard for this.

## 2. Translate the neutral shape into React vocabulary

A sibling `architecture-foundations` plugin's `ui-architecture` skill defines a
UI app's three zones in framework-neutral terms (presentation units,
composers, a logic layer, data-access, local state, an optional module-scoped
shared-state mechanism, types). If that plugin isn't installed, this section
stands on its own — the translation is what matters:

| Neutral concept (`ui-architecture`) | React term |
|---|---|
| presentation unit | dumb component (renders props, no side effects) |
| composer | page (calls one hook, then renders components) |
| logic layer | a custom hook |
| data-access layer | RTK Query API slice (`services/`) |
| local state | a Redux slice (`store/`) — client/UI state only |
| module-scoped shared-state mechanism | React Context, module-scoped (`context/`) |
| global store | the app's Redux store |
| types/shapes | TypeScript types/interfaces (`types/`) |

**The right-hand column names this plugin's greenfield default stack, not a
requirement.** Only the last four rows are stack-independent; the two data rows
say "RTK Query" and "Redux" because that's what `react-project-bootstrap`
installs. On a project using something else, substitute per the step-1 profile —
the *distinction* between the two rows (server state that's cached and
invalidated vs. client state you own) is the part that matters and holds in every
library:

| Row | Project uses TanStack Query | Zustand | Context only |
|---|---|---|---|
| data-access layer | a `queryOptions`/hook module | a store slice doing the fetch | a fetch hook |
| local state | a Zustand/`useState` store | the same store, UI keys | a module Context |

A page still calls **one** hook, components stay dumb, and server state still
never gets hand-copied into client state. Those rules survive the swap; the
library names don't.

Read `references/frontend-layering.md` for the React folder layout this
produces. Read `references/ui-vs-domain-state.md` for the React-specific
version of the state-locality decision rule (props vs. Context vs. store) —
the underlying rule is defined once, neutrally, in `ui-architecture`; this
file only adds the React-specific mechanics and re-render caveats.

## 3. Route to the right skill

Don't try to do everything in this skill. Once you've identified the zone or
concern involved, hand off to the specialist skill. Use this table (full
version with extra detail in `references/adapter-map.md`):

| User is asking about... | Route to |
|---|---|
| Scaffolding a new business domain / feature | `react-module-scaffold` |
| Calling an API, caching, or managing state | `react-data-layer` |
| Sharing state across a module's subtree without prop drilling | `react-module-context` |
| Adding navigation / a new route | `react-routing` |
| Writing unit or integration tests | `react-testing` |
| Starting a brand-new project | `react-project-bootstrap` |
| Naming a file, component, or hook | `react-naming-conventions` |
| Adding a generic UI primitive (button, dialog, dropdown) | `react-component-library` |
| Deciding whether to extract a shared component/hook or accept duplication | `react-component-composition` |
| Reviewing a component for correctness/performance hygiene | `react-best-practices` |

If a sibling `architecture-foundations` plugin's `existing-codebase-adoption`
skill recorded `"existing"` for this project, don't apply
`react-module-scaffold`'s seven-folder skeleton or `react-naming-conventions`'
case rules verbatim — read the project's current component/folder
organization and file-naming pattern first and match it instead.
`state-philosophy`'s server/client-state split and `react-best-practices`'
hooks hygiene still apply regardless of the decision, since those are
correctness concerns, not folder shape.

## 4. General rules to enforce everywhere

These are the React-specific instances of the neutral rules from
`ui-architecture` — restated here so this skill works standalone:

- Pages are thin composers: they call one hook, then render components. No
  business logic in a page.
- Components are dumb: they render props, they don't fetch, dispatch, or own
  state beyond local UI concerns (e.g. an input's own text before it's
  submitted).
- Hooks own the logic: data fetching, dispatch, derived state.
- If you find business logic inside `core/` or `shared/`, or a `modules/`
  folder reaching into another module's internals, flag it and propose moving
  it to the correct zone rather than leaving it in place.

---
_Last reviewed: 2026-08-17_
