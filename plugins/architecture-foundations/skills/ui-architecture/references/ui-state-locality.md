# Where does this piece of UI state live? (framework-neutral)

Apply this decision rule, in order, every time a new piece of state is
introduced in a UI app. Stop at the first rule that matches.

## 1. Global store — if it outlives the screen, or is needed app-wide

If the state needs to survive navigating away and back (server data cached
across screens, a shopping cart, "logged in user"), or multiple unrelated
modules need to read it, it belongs in the global state container. Data that
originated from a server response should flow through whatever caching
mechanism the framework/library provides for that (a dedicated data-fetching
cache, not a hand-written store slice) — a framework adapter names the
concrete mechanism.

## 2. Module-scoped shared state — if it's needed only within one module's subtree, by descendants several levels down

If the state is scoped to a single module (e.g. "which step of this module's
wizard are we on", "the active tab within this module's detail view") and
several components nested a few levels deep within that module need to read
or write it, use a module-scoped shared-state mechanism.

Do not reach for this just because passing two props feels mildly annoying.
Reach for it when the alternative is threading a value through three or more
intermediate components that don't otherwise need it.

**Critical caveat, true regardless of framework:** a module-scoped shared-state
mechanism is typically a *transport*, not a state manager — it does not, by
itself, prevent unnecessary re-computation or re-rendering among everything
that reads it. Reserve it for low-frequency state, back it with the
framework's local-state primitive, and memoize the value passed through it. A
framework adapter names the concrete re-render risk for that framework.

## 3. Direct parent-to-child passing — the default, the 80% case

If the parent already owns the data and the consumer is one or two levels
down, just pass it down directly. This is the default. Most state in a
well-modularized UI app should resolve here: a screen's logic layer owns the
data, and it flows down directly to presentation units.

## Quick test

Ask, in order:

1. Does this need to exist after the user navigates away, or do other modules
   need it too? → **Global store**.
2. Is this scoped to one module, and do deeply nested descendants within that
   module need it? → **Module-scoped shared state**.
3. Otherwise → **Direct parent-to-child passing**.
