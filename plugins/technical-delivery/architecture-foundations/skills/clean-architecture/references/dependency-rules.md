# Dependency Rules, In Detail

## The one-way rule

Dependencies flow in exactly one direction:

```
core → modules → shared
```

Read the arrow as "depends on" / "is allowed to import from". Concretely:

- `core` may import from any module and from `shared`.
- A module may import from `shared`, and from its own internal files.
- A module may **not** import from another module.
- `shared` may not import from `modules` or `core` — not even one specific module for
  one specific edge case.

There is no exception carved out for "just this once" or "it's a small thing." The rule
exists so that each zone can be reasoned about, tested, and changed in isolation without
tracing a web of dependencies across the whole app.

## Why cycles are banned, full stop

A cycle is any path of imports that eventually loops back on itself — the classic case
being module A importing from module B while module B (directly or transitively)
imports from module A. Cycles are banned unconditionally because they:

- Make it impossible to reason about or test either side of the cycle in isolation —
  you cannot understand or unit test module A without also loading module B, and vice
  versa.
- Make it impossible to delete or replace one domain module without touching another,
  which defeats the entire purpose of drawing module boundaries.
- Often signal that the domain boundary itself is drawn wrong — the two "modules"
  are actually one domain that's been artificially split, or a genuinely shared concept
  hasn't been extracted yet.
- Can cause real technical failures depending on the runtime — circular imports, load-order
  bugs, or infinite construction loops — independent of the architectural concern.

This applies at every level: two modules must not cycle, and the three zones must not
cycle (i.e. `shared` must never import from `modules`, which would create
`modules → shared → modules`).

## How to detect a violation

When reviewing or writing code, check every new import statement against these
questions:

1. **Does a file under `shared` import anything from `modules` or `core`?** If yes, that
   is an immediate violation — `shared` must have zero dependencies on the layers above
   it.
2. **Does a file under one module (e.g. `modules/products`) import anything from another
   module's folder (e.g. `modules/billing`)?** If yes, that is a direct cross-module
   import and is banned regardless of how small the imported thing is.
3. **Does anything under `modules` or `shared` import from `core`?** If yes, that's a
   reversed arrow — `core` is supposed to depend on modules and shared, never the other
   way around.
4. **Trace transitively, not just directly.** A module can violate the rule indirectly —
   e.g. module A imports a "utility" from module B's folder, which itself imports
   something from module A. Check the full chain, not just the first hop.

If any of these show up, the code needs to be restructured before merging — this is not
a style nitpick, it's a structural defect that will compound as the app grows.

## What to do when two modules seem to need the same thing

This situation comes up constantly: module A and module B both seem to need the same
piece of logic, type, or data. There are exactly two acceptable resolutions, and "just
import it directly from the other module" is never one of them.

**Option 1 — Promote it to `shared`.**
Ask: does this piece of code have zero business logic once you strip away which module
is calling it? If a generic version with no domain-specific behavior would serve both
callers equally well, extract it into `shared`. Both modules then depend downward on
`shared`, and no cross-module edge is created.

Example: both `products` and `billing` need to format money the same way → extract a
generic currency-formatting helper into `shared`. Neither module needs to know the other
exists.

**Option 2 — Route it through a contract in `core`.**
Ask: does the shared need actually involve business logic or domain data that can't be
stripped out? If module A needs something that is genuinely `billing`'s business
concern (e.g. "the current discount rate for this customer"), don't let `products`
reach into `billing` to get it. Instead, define a narrow contract (an interface, a typed
event, or a well-defined data shape) that `core` wires up — `core` asks `billing` for the
value and hands it to `products`, or `core` subscribes `products` to an event `billing`
emits. Both modules stay ignorant of each other's internals; `core` is the only thing
that knows both exist.

What NOT to do: reach across with a direct import "just for this one type" or "just to
reuse this one function." That single import is how boundaries erode — the next
developer sees precedent and adds another, and within a few changes the two modules are
tangled together and neither can be modified or deleted independently.

If it's unclear whether something is "shared utility" or "domain contract," default to
routing it through `core` — it's easier to later promote a stable, business-logic-free
piece into `shared` than to untangle a direct cross-module import after the fact.

## Spotting duplication nobody consciously decided to create

The section above covers the case where two modules *know* they need the same thing.
Just as common, and easier to miss, is duplication that accumulates silently — nobody
sat down and decided to duplicate anything, it just happened one small change at a time.
When reviewing a module or adding a new one, actively check for:

- **Near-identical validation logic** in two modules' domain layers (e.g. both `orders`
  and `billing` independently re-implement "is this a valid postal code" slightly
  differently). Once spotted, apply the same promote-to-`shared`-or-contract decision
  from above — don't leave it duplicated just because it wasn't duplicated on purpose.
- **Near-identical DTO/type shapes** defined separately in two modules' `types/` folders
  instead of one shared type both import. This is a strong signal the two modules
  actually share a domain concept that hasn't been named yet.
- **The same sequence of steps** (fetch → transform → validate → persist) repeated with
  minor variations across two modules' services. If the variations are cosmetic, extract
  the shared sequence; if the variations encode real business differences, leave them
  separate — see the rule below.

**Apply a rule of three at the module level, not just the component level:** two modules
independently converging on similar logic is not automatically a problem — it can be
coincidence, and forcing a shared abstraction after only two occurrences risks the same
premature-abstraction trap that applies to components (see the `react-component-composition`
skill in a sibling `frontend` plugin for the component-level version of this same
principle). A third module converging on the same pattern is the stronger signal that a
real shared concept exists and is worth promoting to `shared` or a `core` contract.

**When NOT to de-duplicate across modules:** if two modules compute something that looks
the same today but is tied to business rules that are independently owned and expected to
diverge (e.g. `orders`' refund-eligibility check and `subscriptions`' cancellation-eligibility
check happen to both be "is this within 30 days" today), leave them separate. Merging them
into one shared rule creates a coupling that will hurt more than the duplication does the
moment either team changes their 30-day window independently. The dependency-inversion
question to ask before merging: "if I change this shared version for one caller's reason,
would the other caller be surprised or broken?" If yes, they were never really the same
rule — they just looked alike.
