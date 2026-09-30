---
name: vue-architecture
description: >
  Thin architecture-routing adapter for Vue.js applications — confirms the
  project is genuinely Vue, routes greenfield vs. existing work to the right
  entry point, and applies the framework-neutral three-zone UI model
  (core/modules/shared) in Vue's own vocabulary. Deliberately thin: no Vue
  naming-convention, data-layer, testing, or bootstrap specialist skills
  exist yet in this plugin — this skill says so and asks rather than
  inventing them. Use when the user says things like "structure my Vue app",
  "where does this Vue code belong", "set up a Vue project", or "how should I
  organize this Vue codebase".
---

# Vue Architecture (thin adapter)

This skill exists so a Vue task reliably lands on *something* in this plugin
instead of falling through to nothing, or to advice borrowed from the React
adapter. It is intentionally minimal — a routing layer over the
framework-neutral model, not a Vue specialist. Deeper Vue-specific skills
(module scaffolding, naming, data layer, testing, bootstrap) are future work,
not yet written.

## 0. Consult the codebase map first

If a sibling `codebase-map` plugin is installed, ask its `codebase-map-sync`
skill for cached facts about this repo before checking anything below
yourself. If that plugin isn't installed, fall through to step 1's own live
check.

## 1. Confirm this is actually Vue

Look for `vue` in `package.json` dependencies, `.vue` files, or a
`vite.config.*` importing `@vitejs/plugin-vue`. If none of these are present,
say so and stop — this skill is Vue-specific.

## 2. Greenfield vs. existing

- **Project doesn't exist yet** → route to a sibling `architecture-foundations`
  plugin's `project-kickoff` skill. It sequences the design system before any
  component exists, then hands back here (or to whatever bootstrap step it
  has) for the framework skeleton. There is no `vue-project-bootstrap` skill
  yet — say so plainly and scaffold the minimum needed (Vite + Vue, a
  `core/modules/shared` skeleton) by hand, asking the user for anything not
  already pinned down by Step 1's answers.
- **Project exists and predates this plugin** → route to a sibling
  `architecture-foundations` plugin's `existing-codebase-adoption` skill
  first. It decides whether Kaizen's conventions or the existing structure
  govern before anything below gets applied.

## 3. Apply the neutral model, in Vue's vocabulary

A sibling `architecture-foundations` plugin's `ui-architecture` skill defines
the three zones in framework-neutral terms. Translate directly — Vue has no
meta-framework ambiguity comparable to React's (no Vue equivalent of
Next.js/Remix to profile first, though Nuxt is one and changes file-based
routing conventions; if `nuxt` is present, say so and ask before assuming
Vite/Vue Router conventions apply):

| Neutral concept (`ui-architecture`) | Vue term |
|---|---|
| presentation unit | a "dumb" SFC (renders props, no side effects) |
| composer | a route-level view SFC (calls the logic layer, renders components) |
| logic layer | a composable (`use*.ts`) |
| data-access layer | a composable wrapping fetch/API calls, or a Pinia store action |
| local state | `ref`/`reactive` inside a composable, or a Pinia store for module-scoped state |
| module-scoped shared-state mechanism | `provide`/`inject`, scoped to the module |
| global store | a Pinia store |
| types/shapes | TypeScript types/interfaces |

State which of these the project already uses (Pinia vs. Vuex vs. plain
composables) before applying this table — don't assume Pinia just because
it's the modern default.

## 4. What this skill does not yet cover

There is no Vue-specific naming-convention, data-layer, testing, or bootstrap
skill in this plugin. Don't invent folder skeletons, naming rules, or testing
setup patterns as if they were established convention — ask the user what
they'd like, or point at the closest neutral guidance
(`architecture-foundations`'s `state-philosophy` and `test-pyramid` skills
still apply, since they're concept-level, not Vue-specific).

## 5. Never assume

Per the `working-agreement` skill's rule 4: this adapter is thin by design, so
silent defaults here are more likely to be wrong than on the React adapter.
Check for existing project documentation first, and ask before picking a
router, state library, or component-library choice the project hasn't
already made.

---
_Last reviewed: 2026-08-24_
