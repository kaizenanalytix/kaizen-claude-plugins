# Breaking Change Policy

This is the classification `scripts/diff_schema.py` implements. Use it as
the reference when explaining *why* the script flagged (or didn't flag)
something, or when a manual judgment call is needed for a change the script
can't fully automate.

## Breaking changes (fail the diff gate)

- **Removed field** from a response or request schema. Any consumer reading
  that field breaks.
- **Changed field type** (e.g. `string` → `integer`, or narrowing
  `string | null` → `string`). Even "safely-looking" widenings like
  `integer` → `number` are treated as breaking by default because a
  strictly-typed consumer (e.g. generated TS expecting `number` from
  `integer` semantics) may rely on integer-only values.
- **New required field** added to a request body. Existing clients that
  don't send it will now fail validation.
- **Removed endpoint** (a path, or a method on a path, that existed in
  `previous` and is gone in `current`).
- **Renamed endpoint** — modeled as a remove + add, which is indistinguishable
  from an unrelated removal plus an unrelated addition, so it is always
  flagged as breaking (a rename is never "free"; the old path must be
  deprecated through the normal versioning process, not silently swapped).
- **Narrowed enum** — a value removed from an existing `enum` list. Consumers
  that could previously send/receive that value break.
- **Changed response status code semantics** for an existing operation (e.g.
  an operation that returned `200` now returns `201` for the same case) —
  treated as breaking because clients often branch on status code.

## Additive changes (pass silently)

- **New endpoint** (new path, or new method on an existing path).
- **New optional field** added to a request or response schema (not in
  `required`).
- **New enum value**, *provided* consumers are documented to ignore unknown
  enum values (this is a contract-level convention — state it explicitly in
  the contract's README/changelog so consuming teams write forward-compatible
  switch/match statements with a default case).
- **New response schema for a status code that didn't previously have a
  documented schema** (e.g. documenting a `404` shape that was previously
  undocumented but already returned) — clarifying, not breaking.
- **Widening a field from required to optional** (removing it from
  `required` while keeping the property) — strictly loosens the contract for
  producers; a defensible additive change since existing consumers that
  already handle the field's presence are unaffected, though the script logs
  it explicitly so a reviewer can double check.

## Required process when a breaking change is unavoidable

1. **Do not apply it to the current version's `openapi.json`.** Per
   `versioning-strategy.md`, breaking changes ship as the next version
   (`v1` → `v2`), never as an in-place edit.
2. **Bump the version** in the URL path and in the schema's `info.version`.
3. **Add a changelog entry** describing exactly what changed and why, in the
   contract's changelog file (e.g. `CHANGELOG.md` alongside the committed
   `openapi.json` artifacts), including the migration path for consumers.
4. **Ensure the consuming team is subscribed** to that changelog — e.g. via a
   PR review requirement, a notification hook, or a shared channel — so the
   breaking change is a coordinated event, not a surprise discovered at
   runtime.
5. **Re-run `diff_schema.py`** for the new version's first commit to confirm
   it captures the intended breaking changes only (no accidental extra
   breakage slipped in alongside the intentional one).

Only after all of the above should `--allow-breaking` be used to let a diff
gate run pass in CI — and only for the PR that performs this exact version
bump + changelog process, never as a blanket override.
