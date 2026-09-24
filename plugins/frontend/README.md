# frontend

Tier 2 plugin for building maintainable, domain-modular UI applications.
Ships one deep framework adapter (the `react-*` skills), two thin ones
(`vue-architecture`, `angular-architecture` — stack detection and zone
routing only, no specialist depth yet), and a framework-neutral
build-tooling group (the `vite-*` skills) any adapter can reference without
rewriting. Next.js needs no adapter of its own — it's a React meta-framework
`frontend-architecture` already profiles.

## Overview

This plugin teaches Claude how to structure, scaffold, and extend a React +
TypeScript application using a three-zone module architecture, a clean
server-state/client-state split, module-scoped context, typed lazy-loaded
routing, a full test pyramid, an installable component library, and naming
and best-practice conventions — plus, separately, how to configure and use
Vite (the build tool), written with zero framework assumptions since Vite
itself doesn't care which UI framework sits on top of it.

## What stack this assumes — read this before adopting

`react-project-bootstrap` builds one specific stack, and several skills are
written against it:

| Concern | Assumed | Skill that assumes it |
|---|---|---|
| Build tool | Vite | `react-project-bootstrap` |
| Routing | React Router **library mode** (a central route table) | `react-routing` |
| Server state | RTK Query | `react-data-layer` |
| Primitives | shadcn/ui | `react-component-library` |
| Testing | Vitest + RTL + MSW | `react-testing` (browser-driven tests are a sibling `e2e-testing` plugin's job, at any depth — not this skill's, not even a smoke check) |
| Styling | Tailwind **v4** (`@theme` in `app.css`) | a sibling `design-system` plugin |

**That is a default for new projects, not a requirement for existing ones.**
Having `react` in `package.json` says almost nothing — Next.js apps, React Router
framework-mode apps, and Remotion video projects all have it and all need
different advice.

So each of the skills above opens by checking what the project *actually* uses
and adapting: the architectural rules (server vs. client state, thin pages, dumb
components, one hook per page) are stack-independent and always apply; the
library-specific mechanics get translated to whatever is installed.
`frontend-architecture` profiles the stack once — meta-framework, router,
server-state layer — and routes on that, rather than on a yes/no React check.

**None of these skills will propose migrating a working app** to RTK Query,
React Router, or shadcn because a skill mentions them. If a migration is wanted,
it's its own task.

It conceptually depends on a sibling `architecture-foundations` plugin — most
directly its `ui-architecture` skill, which `frontend-architecture` here is a
thin React-specific translation of, plus the three-zone model, test-pyramid
philosophy, its `existing-codebase-adoption` skill (decides Kaizen-vs-existing
conventions before any structural skill below applies), and a sibling
`api-contract` plugin's generated DTO types — but every skill here works
standalone. It restates the one relevant rule in a single sentence rather
than assuming those plugins' files are physically present.
`frontend-architecture` also optionally consults a sibling `codebase-map`
plugin for cached, checkpointed codebase facts before doing its own live
stack detection, if that plugin is installed.

## Layout

```
skills/
├── frontend-architecture/       # foundation/orchestrator — applies the three-zone model, routes below
├── react-module-scaffold/       # ─┐
├── react-data-layer/             # │
├── react-module-context/         # │
├── react-routing/                # ├─ React adapter — everything React-specific
├── react-testing/                # │
├── react-project-bootstrap/      # │
├── react-naming-conventions/     # │
├── react-component-library/      # │
├── react-component-composition/  # │
├── react-best-practices/        # ─┘
├── vite-config-basics/          # ─┐
├── vite-env-variables/           # │
├── vite-dev-proxy/               # ├─ framework-neutral — no React/Vue/etc. content
├── vite-plugins/                 # │
├── vite-build-output/           # ─┘
├── vue-architecture/             #  ─ thin adapter — stack detection + zone routing only
└── angular-architecture/        #  ─ thin adapter — stack detection + zone routing only
```

Skills are grouped by name prefix, not by folder. Every skill sits directly at
`skills/<name>/SKILL.md`, which is the only depth Claude Code discovers: a
skill nested one level deeper (e.g. `skills/react/react-testing/`) still
auto-triggers off its `description`, but loses its namespaced
`/frontend:<skill>` invocation form entirely. Keep this layout flat — if a
future adapter (`vue/`, `svelte/`) is added, distinguish it by prefix
(`vue-module-scaffold`) rather than by directory.

## Components

| Skill | Purpose |
|---|---|
| `frontend-architecture` | Thin React adapter: profiles the stack (meta-framework / router / server-state / is-it-even-a-web-app), translates a sibling `architecture-foundations` plugin's framework-neutral `ui-architecture` skill into React vocabulary, and routes to the skills below on what it found. Gates on that same plugin's `existing-codebase-adoption` skill first, on a non-greenfield project. |
| `react-module-scaffold` | Scaffolds a new business-domain module and wires it into the store and router. |
| `react-data-layer` | RTK Query (server state) vs. Redux slice (client state), composed by a custom hook. |
| `react-module-context` | The props → module-context → store decision rule, with a safe context factory. |
| `react-routing` | Lazy-loaded, typed, auth-protected routes with path constants. |
| `react-testing` | Vitest (unit), RTL + MSW (integration). No browser-driven tests at all — a sibling `e2e-testing` plugin owns every Playwright test in this marketplace, regardless of depth. Lists the intended cases in plain language and waits for confirmation before writing any test code. |
| `react-project-bootstrap` | Greenfield Vite + React + TypeScript setup, with Tailwind and the `app.css` theme wired in from the first commit. Normally reached through a sibling `architecture-foundations` plugin's `project-kickoff` skill, which runs the design system first. |
| `react-naming-conventions` | File/folder/identifier naming standards for every module subfolder. |
| `react-component-library` | Standardizes on shadcn/ui for generic UI primitives, composed into domain components. |
| `react-component-composition` | When to extract a shared component/hook vs. accept duplication (rule of three), composition vs. render props, and spotting silent duplication across modules. |
| `react-best-practices` | Component-level hygiene: Rules of Hooks, memoization, list keys, accessibility, error boundaries. |
| `vite-config-basics` | The general shape of `vite.config.ts` — plugins array, path aliases, dev server basics — framework-neutral. |
| `vite-env-variables` | `.env`/`.env.[mode]` file conventions, the `VITE_` prefix, `import.meta.env` typing, and why secrets never go in a `VITE_` variable. |
| `vite-dev-proxy` | Configuring `server.proxy` to forward API calls to a local backend during dev without CORS setup. |
| `vite-plugins` | Deciding whether something needs a Vite plugin at all, vs. a regular dependency. |
| `vite-build-output` | What `vite build` produces, the `base` option for subpath deployments, and what a deploy step picks up. |
| `vue-architecture` | Thin Vue.js adapter: stack detection, greenfield/existing routing, and the three-zone model translated into Vue vocabulary (SFCs, composables, Pinia). No naming/data-layer/testing/bootstrap skills yet — asks rather than invents. |
| `angular-architecture` | Thin Angular adapter: stack detection, greenfield/existing routing, and the three-zone model translated into Angular vocabulary (components, injectable services, DI scoping). No naming/data-layer/testing/bootstrap skills yet — asks rather than invents. |

## Setup

No setup beyond having (or creating, via `react-project-bootstrap`) a React +
TypeScript project. Tailwind CSS is now part of that scaffold's own dependency
baseline rather than something `shadcn init` installs as a side effect, so the
theme file exists before the first component — see a sibling `design-system`
plugin for what goes in it.

## Usage

- "This project already has a frontend" / "should I follow this repo's conventions or Kaizen's" → a sibling `architecture-foundations` plugin's `existing-codebase-adoption` skill, gated via `frontend-architecture`
- "Structure my frontend" / "where does this UI code belong" → `frontend-architecture`
- "Add a new products module" → `react-module-scaffold`
- "Call the API and cache the results" / "add a Redux slice" → `react-data-layer`
- "Share state across this module without prop drilling" → `react-module-context`
- "Add a protected, lazy-loaded route" → `react-routing`
- "Write tests for this hook/component/slice" → `react-testing`
- "Set up a new React project" → `react-project-bootstrap` (or a sibling `architecture-foundations` plugin's `project-kickoff` skill, which sequences the design system, this scaffold, and the architecture skeleton in the right order)
- "What should I name this file/component/hook?" → `react-naming-conventions`
- "Add a button/dialog/dropdown component" / "set up shadcn" → `react-component-library`
- "Should I extract this into a component" / "this looks duplicated" / "DRY this up" → `react-component-composition`
- "Review this component" / "why is this re-rendering" → `react-best-practices`
- "Set up vite.config" / "add a path alias" → `vite-config-basics`
- "Environment variables in Vite" / "config for dev/qa/prod" → `vite-env-variables`
- "Proxy API calls" / "CORS in local dev" → `vite-dev-proxy`
- "Do I need a Vite plugin for this" → `vite-plugins`
- "What does vite build produce" / "vite build base path" → `vite-build-output`
- "Structure my Vue app" / "where does this Vue code belong" → `vue-architecture`
- "Structure my Angular app" / "where does this Angular code belong" → `angular-architecture`
