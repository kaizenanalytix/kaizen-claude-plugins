# Domain Modules, In Detail

## What makes a good domain module boundary

A module boundary should align with a real business domain, not with a technical layer
or a UI screen. Good boundaries share these traits:

- **Named after a business concept, not a technical pattern.** `products`, `billing`,
  `notifications`, `users` — not `handlers`, `services`, `utils-2`.
- **Self-contained.** Everything needed to fulfill that domain's responsibility — its
  logic, its data access, its types — lives inside the module's folder. A developer
  should be able to open one module folder and understand that entire slice of the
  business without jumping into other modules.
- **Independently changeable.** A change to how `billing` calculates tax should never
  require touching `products` code. If it does, the boundary is probably wrong, or a
  cross-module dependency has crept in that should have gone through `shared` or a
  contract in `core` instead.
- **Independently deletable/replaceable.** As a thought experiment: could this module be
  deleted and rebuilt from scratch (keeping only its public contract) without other
  modules noticing beyond that contract? If not, the boundary is leaking.
- **Stable in scope over time.** The domain's core responsibility ("things related to
  orders") shouldn't need renaming or splitting every few sprints. Frequent boundary
  churn is a sign the domain was cut along the wrong lines the first time.

## Checklist: is this one domain or two?

When it's unclear whether something is a single module or should be split into two,
work through these questions:

1. **Do the two halves change for different reasons?** If "reason to change A" and
   "reason to change B" are usually unrelated business events, they are probably two
   domains. If they almost always change together, they are probably one domain.
2. **Does one half make sense without the other?** If you could ship one half and
   delete the other and the remaining one would still be a coherent business capability,
   they're likely two domains.
3. **Would a non-technical stakeholder describe them as separate things?** If a product
   manager naturally talks about "orders" and "shipping" as different concerns with
   different owners, don't force them into one module just because the code is small
   today.
4. **Is the only connection between them a shared piece of data, not shared behavior?**
   Shared data alone (e.g. both reference a "customer ID") is not a reason to merge
   modules — it's a reason to make sure the data's shape lives somewhere both can depend
   on (typically `shared`, or a contract), while behavior stays separate.
5. **Watch for a module that's grown a lot of unrelated internal folders.** If a single
   module folder has accumulated several sub-areas that don't interact with each other
   and are never touched by the same change, that's a signal it's actually multiple
   domains wearing one folder.

When genuinely unsure, prefer starting with fewer, coarser modules and splitting later
once usage reveals the real seams — it's easier to split a module than to unwind a web of
cross-module imports created by cutting boundaries too finely up front.

## The frontend/backend mirroring principle

A module boundary set on the backend should mirror the module boundary set on the
frontend: same business domain, same name, same conceptual scope — even though the two
are physically separate codebases with no code-level dependency between them.

Why this matters:
- **Cognitive alignment.** A developer moving between the frontend `products` module and
  the backend `products` module should recognize it as "the same slice of the business,"
  even though nothing is shared at the code level.
- **Easier contract design.** When the frontend's `orders` module and the backend's
  `orders` module map 1:1, the API contract between them is simpler to reason about —
  there's no translation layer reconciling mismatched boundaries.
- **Consistent ownership.** Teams (or a single developer wearing both hats) can own "the
  orders domain end to end" instead of owning a fragment of several different technical
  layers.

This mirroring is a naming/conceptual convention, not a code dependency — the frontend's
`modules/products` and the backend's `modules/products` never import from each other and
never need to. They stay physically independent, deployable independently, and testable
independently. The alignment lives in the shared understanding of what the domain is
called and what it's responsible for, established once (e.g. in a design doc or through
consistent naming convention) and then applied on both sides. If the backend introduces
a new domain module, check whether the frontend needs a correspondingly named module —
and vice versa — even though no import will ever connect them.
