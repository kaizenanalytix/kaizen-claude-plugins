---
name: ui-architecture
description: >
  Applies the three-zone model (core/modules/shared) specifically to a UI
  application, in framework-neutral terms — no React, Vue, Angular, or any
  other library vocabulary. Use for a UI codebase whose framework is unknown,
  not yet chosen, or has no adapter skill in this suite, when the user asks
  things like "how should I organize this UI app", "what's the right shape for
  a frontend", or "structure this app without assuming a framework". For a
  project already confirmed to be React, use that framework's adapter skill
  instead — this skill defines the neutral shape the adapter translates.
---

# UI Architecture (Framework-Neutral)

This is the `clean-architecture` three-zone model (core/modules/shared), applied
specifically to the shape a *UI application* takes — as opposed to a generic
service or library. It contains no framework vocabulary on purpose: no "hooks",
no "components" in any framework-specific sense, no JSX, no Redux. A concrete
framework adapter (e.g. a `frontend` plugin's `frontend-architecture` skill for
React) restates the one relevant rule from here and translates it into that
framework's real vocabulary — read this skill first, then let the adapter do
the translation.

## Why a UI app needs a layer between "any app" and "a specific framework"

`clean-architecture` (a sibling skill in this plugin) applies to any codebase,
frontend or backend. It doesn't mention "pages" or "presentation" at all,
because a backend service doesn't have those concepts. A UI app does — every
UI framework, regardless of vocabulary, ends up needing something that
composes a screen, something that renders presentation, and something that
owns the logic behind that presentation. This skill names those three things
in neutral terms so that a React adapter, a Vue adapter, or any other
framework adapter is translating the same underlying shape, not inventing
three different shapes that happen to look similar.

## The three zones, for a UI app

- **`core/`** — app bootstrap only: navigation/routing setup, the global
  state-container setup, and top-level cross-cutting wrappers (theming, an
  app-wide data-fetching client, top-level auth). Imported only by the
  application's entrypoint. Contains no business logic.
- **`modules/`** — one folder per business domain. Each module owns:
  - **presentation units** — dumb, render-only pieces; given the same input,
    they always produce the same output; no fetching, no dispatching, no
    business logic.
  - **composers** — thin, screen-level assemblies; a composer calls the
    module's logic layer once, then arranges presentation units. No business
    logic in a composer.
  - **a logic layer** — owns data-fetching, derived values, and dispatch; this
    is where a screen's "brain" lives, decoupled from how it renders.
  - **a data-access layer** — talks to the API for this domain.
  - **a local state container** — client/UI-only state for this domain
    (filters, selection, wizard step); never a place to hand-store a fetched
    server response.
  - **an optional module-scoped shared-state mechanism** — for state that
    needs to reach several nested descendants within this module's subtree,
    without going all the way to the global store.
  - **type/shape definitions** — the domain's entities and request/response
    shapes.
- **`shared/`** — reusable code with zero business logic: generic
  presentation primitives, generic reusable logic units, formatting helpers.
  The moment a "shared" piece needs to know what a domain entity is, it isn't
  shared anymore.

Read `references/ui-layering.md` for the full folder-level walkthrough and a
worked example.

## Where a piece of state lives

Apply this decision rule, in order, every time new state is introduced:

1. **Global store** — if it outlives the current screen, or other modules
   need it too.
2. **Module-scoped shared state** — if it's needed only within one module's
   subtree, by descendants several levels down.
3. **Direct parent-to-child passing** — the default, the 80% case; if the
   parent already owns the data and the consumer is one or two levels down,
   just pass it down directly.

Read `references/ui-state-locality.md` for the full decision rule and the
caveats around each option (in particular: a module-scoped shared-state
mechanism is usually a transport, not a state manager — it doesn't avoid
re-computation or re-rendering by itself, so reserve it for low-frequency
state).

## Handing off to a framework adapter

This skill stops at the neutral shape. Once a framework is known (check for
that framework's manifest/dependency file — e.g. `react` in `package.json`),
hand off to that framework's adapter skill (e.g. `frontend-architecture` in a
sibling `frontend` plugin), which restates the relevant rule above in one or
two sentences and then translates every zone and concept into that
framework's real vocabulary: presentation units become that framework's
component primitive, composers become route-level components/pages, the logic
layer becomes that framework's data/state hooks or equivalent, and so on. Do
not translate into framework-specific terms here — that translation is the
adapter's job, and keeping it out of this skill is what lets a second
framework adapter (e.g. Vue) reuse this same neutral shape without a rewrite.

---
_Last reviewed: 2026-08-05_
