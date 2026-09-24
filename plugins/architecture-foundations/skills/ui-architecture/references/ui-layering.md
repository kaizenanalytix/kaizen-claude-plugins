# The three-zone model, applied to a UI app (framework-neutral)

This expands the SKILL.md summary with a full folder-level walkthrough. No
framework vocabulary is used here on purpose — a framework adapter maps each
concept below onto that framework's real primitives.

## Top-level layout

```
src/
  core/                  # app bootstrap — imported only by the entrypoint
    navigation/          # top-level route/screen tree
    state-container/     # the global state container's setup and wiring
    providers/           # theming, an app-wide data client, top-level auth
  modules/
    products/            # one folder per business domain
      presentation/      # dumb, render-only units
      composers/         # thin, screen-level assemblies
      logic/             # the domain's "brain" — data-fetching, derived state
      data-access/       # the API layer for this domain
      local-state/        # client/UI-only state for this domain
      shared-state/       # optional — module-scoped shared state mechanism
      types/             # domain entity + request/response shapes
    orders/
      ...
  shared/                # zero business logic
    presentation/
    logic/
    utils/
```

A framework adapter typically renames these folders to that framework's
convention (e.g. a React adapter uses `components/`, `pages/`, `hooks/`,
`services/`, `store/`, `context/`, `types/`) but the underlying seven
responsibilities per module stay the same regardless of what they're called.

## What lives in `core/`

- **`navigation/`** — the top-level screen/route tree, composed from the
  navigation each module contributes.
- **`state-container/`** — the setup and wiring for the app's global state
  mechanism (whatever that is in the chosen framework/library), including
  registering each module's slice of that state.
- **`providers/`** — theming, an app-wide data-fetching client, top-level auth
  context. This is the *only* place app-wide cross-cutting wrappers should
  mount. Module-scoped shared-state mechanisms do not belong here.

`core/` is imported only by the application's entrypoint. No module should
ever import from `core/` except to register itself (e.g. exporting its slice
of state for `core/` to wire in).

## What lives in `modules/<name>/`

Every business domain gets these seven responsibilities, even if some start
empty:

- **presentation** — dumb, render-only. No fetching, no dispatching, no
  business logic. Given the same input, always produces the same output.
- **composers** — thin, screen-level. A composer calls the module's logic
  layer once to get data and handlers, then arranges presentation units. No
  business logic in a composer — if you're writing a conditional that isn't
  about "is this loading / did this error", it's probably logic that belongs
  in the logic layer instead.
- **logic** — owns data-fetching and dispatch logic. This is where a screen's
  "brain" lives, decoupled from how it renders.
- **data-access** — the API layer for this domain.
- **local-state** — client/UI state only for this domain (filters, selection,
  wizard step). Never a place to hand-store a fetched server response — that's
  what the data-access layer's own caching mechanism is for.
- **shared-state** (optional) — a module-scoped shared-state mechanism, for
  state that needs to reach several nested descendants within this module's
  subtree but doesn't belong in the global store.
- **types** — domain entity types and request/response shapes. If a
  contract-generation mechanism (e.g. a sibling `api-contract` plugin) has
  generated these, import them instead of hand-writing; otherwise define them
  locally and note they should be replaced once generated types exist.

## What lives in `shared/`

Anything reusable that has *zero* business logic: generic presentation
primitives (a button, a modal, a form field), generic reusable logic units (a
debounce utility, a media-query watcher), formatting helpers. The moment a
"shared" piece needs to know what a domain entity is, it isn't shared — move
it into the owning module (or, if genuinely needed by two-plus modules,
reconsider whether it's really domain-agnostic first).
