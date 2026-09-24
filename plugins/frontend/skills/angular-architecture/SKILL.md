---
name: angular-architecture
description: >
  Thin architecture-routing adapter for Angular applications — confirms the
  project is genuinely Angular, routes greenfield vs. existing work to the
  right entry point, and applies the framework-neutral three-zone UI model
  (core/modules/shared) in Angular's own vocabulary. Deliberately thin: no
  Angular naming-convention, data-layer, testing, or bootstrap specialist
  skills exist yet in this plugin — this skill says so and asks rather than
  inventing them. Use when the user says things like "structure my Angular
  app", "where does this Angular code belong", "set up an Angular project",
  or "how should I organize this Angular codebase".
---

# Angular Architecture (thin adapter)

This skill exists so an Angular task reliably lands on *something* in this
plugin instead of falling through to nothing, or to advice borrowed from the
React adapter. It is intentionally minimal — a routing layer over the
framework-neutral model, not an Angular specialist. Deeper Angular-specific
skills (module scaffolding, naming, data layer, testing, bootstrap) are
future work, not yet written.

## 0. Consult the codebase map first

If a sibling `codebase-map` plugin is installed, ask its `codebase-map-sync`
skill for cached facts about this repo before checking anything below
yourself. If that plugin isn't installed, fall through to step 1's own live
check.

## 1. Confirm this is actually Angular

Look for `@angular/core` in `package.json` dependencies, or an `angular.json`
at the project root. If neither is present, say so and stop — this skill is
Angular-specific.

## 2. Greenfield vs. existing

- **Project doesn't exist yet** → route to a sibling `architecture-foundations`
  plugin's `project-kickoff` skill for the design-system sequencing, then
  scaffold the minimum framework skeleton by hand (there is no
  `angular-project-bootstrap` skill yet — say so plainly), asking the user
  for anything Step 1's answers don't already pin down.
- **Project exists and predates this plugin** → route to a sibling
  `architecture-foundations` plugin's `existing-codebase-adoption` skill
  first. It decides whether Kaizen's conventions or the existing structure
  govern before anything below gets applied.

## 3. Apply the neutral model, in Angular's vocabulary

A sibling `architecture-foundations` plugin's `ui-architecture` skill defines
the three zones in framework-neutral terms. Also record whether the project
uses standalone components (Angular 14+ default) or NgModules — that changes
where wiring lives, though not the zone mapping below:

| Neutral concept (`ui-architecture`) | Angular term |
|---|---|
| presentation unit | a presentational component (`@Input`/`@Output` only, no injected services beyond pure pipes) |
| composer | a routed/page component (injects the logic-layer service, renders child components) |
| logic layer | an injectable service (or a signal-based store) scoped to the feature |
| data-access layer | an `HttpClient`-based service, or a resource/query wrapper if one is installed |
| local state | signals or a component/service-level `BehaviorSubject`, feature-scoped |
| module-scoped shared-state mechanism | a service provided at the feature route/module level (Angular's DI scoping *is* this mechanism) |
| global store | NgRx/NGXS store if installed, otherwise a root-provided service |
| types/shapes | TypeScript interfaces/types |

Angular's DI hierarchy already gives "module-scoped shared state" a native
mechanism (`providedIn` at the route/module level) — don't reach for NgRx by
default just because the neutral model names a "module-scoped shared-state
mechanism"; that's the stack-independent concept, not a mandate for a specific
library.

## 4. What this skill does not yet cover

There is no Angular-specific naming-convention, data-layer, testing, or
bootstrap skill in this plugin. Don't invent folder skeletons, naming rules,
or testing setup patterns as if they were established convention — ask the
user what they'd like, or point at the closest neutral guidance
(`architecture-foundations`'s `state-philosophy` and `test-pyramid` skills
still apply, since they're concept-level, not Angular-specific).

## 5. Never assume

Per the `working-agreement` skill's rule 4: this adapter is thin by design, so
silent defaults here are more likely to be wrong than on the React adapter.
Check for existing project documentation first, and ask before picking a
state-management library, standalone-vs-NgModule structure, or component
library the project hasn't already committed to.

---
_Last reviewed: 2026-08-24_
