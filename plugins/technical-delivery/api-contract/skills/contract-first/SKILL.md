---
name: contract-first
description: >
  Defines and enforces the API contract that sits between a frontend and a
  backend service — a single OpenAPI schema that both sides generate typed
  code from so they can evolve independently without drifting apart. Covers
  backend-first-vs-schema-first strategy, generated types, breaking-change
  classification, versioning, and a CI diff gate. Use this skill when asked
  to "define the API contract", "generate API types", "sync frontend and
  backend types", "check for breaking API changes", or "set up a CI diff
  gate for the API schema".
---

# Contract-First API Development

## Purpose

The API contract is the seam between a `frontend` plugin/app and a `backend`
plugin/app. Neither side should ever import the other's source code — they
only depend on generated types produced from one shared OpenAPI schema. This
skill keeps that contract authoritative, generates types for both sides, and
prevents silent drift with a CI diff gate.

## Step 1: Decide the contract direction

Two valid approaches — recommend **backend-first with an enforced diff gate**
as the default, but pick based on context:

- **Backend-first + diff gate (default recommendation).** The backend (e.g.
  FastAPI) is the source of truth: it emits its own OpenAPI schema via
  `app.openapi()` / the `/openapi.json` endpoint as part of the build. That
  emitted `openapi.json` is committed to version control as a build artifact.
  Types for both sides are generated from it. Good default because the schema
  can never drift from the actual implementation — it's generated FROM the
  code, not maintained alongside it.
- **Schema-first.** A human hand-authors the OpenAPI file (e.g. in Stoplight
  or Swagger Editor) before either side writes code. Use this instead when
  the API shape must be agreed upon before implementation starts — multi-vendor
  integrations, public/partner APIs, or contract negotiations with an external
  team. The hand-authored file becomes the contract; both frontend and backend
  implementations are then generated/validated against it.

See `references/openapi-source-of-truth.md` for the full comparison and the
generation pipeline diagram.

## Step 2: Generate types for both sides

When the user wants to actually produce contract types (not just discuss
them), run the script — don't hand-write the types yourself:

```bash
python3 scripts/generate_types.py --input openapi.json --out ./generated/types
```

This reads every schema under `components.schemas` in the given
`openapi.json` and writes one `.ts` file per schema, each carrying an
`// AUTO-GENERATED — do not edit` header. Never hand-edit generated files —
if a type is wrong, fix the OpenAPI schema (or the backend model that
produces it) and regenerate. Generated files ARE checked into version
control precisely so a PR diff shows exactly what changed in the contract.

For a backend that needs to consume types from other federated services'
schemas (Pydantic-compatible), see `references/type-generation.md` for the
same pipeline applied in the other direction.

## Step 3: Check for breaking changes before merging

When the user wants to verify a schema change is safe (or you're wiring CI),
run:

```bash
python3 scripts/diff_schema.py --previous old_openapi.json --current new_openapi.json
```

This diffs `paths` and `components.schemas` between the two files, classifies
every change as additive or breaking, prints a human-readable report, and
exits non-zero if any breaking change is found — unless `--allow-breaking` is
passed. Recommend wiring this as a concrete CI step on every backend PR:

```yaml
# .github/workflows/api-contract.yml (excerpt)
- name: Regenerate OpenAPI schema
  run: python backend/scripts/export_openapi.py --out openapi.new.json
- name: Diff against committed contract
  run: python3 scripts/diff_schema.py --previous openapi.json --current openapi.new.json
```

Additive changes (new endpoint, new optional field, new enum value if
consumers are documented to ignore unknown values) pass silently. Breaking
changes (removed field, changed field type, new required field, removed or
renamed endpoint) fail the build unless the PR also bumps the API version and
adds a changelog entry. See `references/breaking-change-policy.md` for the
exact classification rules and the required process when a breaking change
is genuinely unavoidable.

## Step 4: Version deliberately

Recommend URL-based versioning (`/api/v1/...`, `/api/v2/...`) as the default:
old and new contracts can run side by side during a client migration, and a
breaking change never mutates an existing version in place — it ships as the
next version instead. See `references/versioning-strategy.md` for deprecation
timelines and how long to keep an old version alive after a new one ships.

## What belongs in the contract vs what stays on one side

Contract-visible (must cross the seam, so changes require coordinated
updates on both sides):
- Request/response schemas (bodies, query/path params)
- HTTP status codes and the error response shape
- Auth token claim shape (what the frontend can read out of a JWT, etc.)
- The versioning scheme itself

Stays internal (never put in the contract; changing it on one side should
never force a code change on the other):
- Domain entities and internal service composition on the backend
- Repository/ORM internals (table structure, query patterns)
- Frontend session/UI store shape (Redux/Zustand/Pinia state, etc.)

Rule of thumb: **if changing it on one side should never require a code
change on the other, it doesn't belong in the contract.** When in doubt, ask
whether a DTO/serializer already translates the internal shape into
something contract-visible — if yes, only the DTO's shape belongs here.

## Reference files

- `references/openapi-source-of-truth.md` — backend-first vs schema-first in
  depth, and the full generation pipeline from FastAPI app to committed
  frontend types.
- `references/type-generation.md` — how `generate_types.py` maps OpenAPI
  types to TypeScript, and how each side is expected to import the output.
- `references/versioning-strategy.md` — URL versioning mechanics and
  deprecation timelines.
- `references/breaking-change-policy.md` — the precise additive-vs-breaking
  classification and the required version-bump/changelog process.

---
_Last reviewed: 2026-08-05_
