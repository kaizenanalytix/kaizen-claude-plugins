# Where does this piece of state live? (React mechanics)

The decision rule itself is defined once, neutrally, in a sibling
`architecture-foundations` plugin's `ui-architecture` skill
(`references/ui-state-locality.md` there). This file only adds the React-
specific mechanics and re-render caveats for each option.

## 1. Store — if it outlives the screen, or is needed app-wide

If the state needs to survive navigating away and back (e.g. server data
cached across pages, a shopping cart, "logged in user"), or multiple unrelated
modules need to read it, it goes in the Redux store. Server-response data in
particular always goes through RTK Query's cache, never through a hand-written
slice — see `react-data-layer` for the server-state vs. client-state split
within the store.

## 2. Module Context — if it's needed only within one module's subtree, by descendants several levels down

If the state is scoped to a single module (e.g. "which step of this module's
wizard are we on", "the active tab within this module's detail view") and
several components nested a few levels deep within that module's page need to
read or write it, use a module-scoped React Context. See `react-module-context`
for the implementation pattern and its caveats (Context is a transport, not a
state manager — every consumer re-renders on change).

Do not reach for Context just because passing two props feels mildly annoying.
Reach for it when the alternative is threading a value through three or more
intermediate components that don't otherwise need it.

## 3. Props — the default, the 80% case

If the parent already owns the data and the consumer is one or two levels
down, just pass it as a prop. This is the default. Most state in a
well-modularized app should resolve here: a page's hook owns the data, and it
flows down through props to dumb components.

## Quick test

Ask, in order:

1. Does this need to exist after the user navigates away, or do other modules
   need it too? → **Store**.
2. Is this scoped to one module, and do deeply nested descendants within that
   module need it? → **Module Context**.
3. Otherwise → **Props**.
