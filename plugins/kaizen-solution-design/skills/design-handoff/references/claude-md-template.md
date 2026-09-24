# CLAUDE.md template (design-handoff entry point)

Fill this template to produce `docs/CLAUDE.md`. Replace every `<…>` placeholder from the extracted
design content. Delete sections that have no source (e.g. no Front-end doc → drop its row). Keep it
skimmable: link to the detailed docs, don't paste them in. Everything here must be faithful to the
design artifacts — do not introduce technologies or decisions the source docs didn't make.

---

```markdown
# <Project Name> — Design Handoff

> This folder is the engineering handoff for <Project Name>. It re-expresses the signed-off design
> (technical design documents + data model) as Markdown a coding agent can read directly. Start
> here, then follow the links. The DDL in `data-model/schema.sql` and the requirement IDs in
> `requirements.md` are the sources of truth — honour them.

## What we're building
<One paragraph: the system, who uses it, the problem it solves, the shape of the solution.>

## Tech stack
| Tier | Technology | Version | Notes |
|---|---|---|---|
| Client | <React> | <18.x> | <web app> |
| Application | <FastAPI> | <0.11x> | <REST API> |
| Data | <PostgreSQL> | <16> | <operational store> |
| Infra | <AWS ECS / Terraform> | <…> | <hosting, IaC> |
<from the design decisions register / overview tech-stack table; exact versions where known>

## Architecture map
<2–4 sentences on how the pieces fit and the main request/data flow.> See the diagrams in
`diagrams/` and the detailed docs:

| Area | Doc |
|---|---|
| System overview & decisions | [architecture/overview.md](architecture/overview.md) |
| Back-end / services | [architecture/backend.md](architecture/backend.md) |
| Front-end / UI | [architecture/frontend.md](architecture/frontend.md) |
| API / interface contracts | [architecture/api.md](architecture/api.md) |
| Integration / external systems | [architecture/integration.md](architecture/integration.md) |
| Security & auth | [architecture/security.md](architecture/security.md) |
| Infrastructure & deployment | [architecture/infrastructure.md](architecture/infrastructure.md) |
| Processing / algorithms / ML | [architecture/processing.md](architecture/processing.md) |
<keep only the rows whose docs exist>

## Data model
Source of truth: [data-model/schema.sql](data-model/schema.sql) ·
column-level detail: [data-model/data-dictionary.md](data-model/data-dictionary.md) ·
narrative & relationships: [data-model/schema.md](data-model/schema.md).

Entities (summary):
- `<table_a>` — <one line: what it holds, its grain>
- `<table_b>` — <…>

## Requirements
Full list with IDs: [requirements.md](requirements.md). Build the **Must have** set first:
- <FR-001> — <short requirement>
- <FR-0xx> — <…>

## Where to look for…
| If you're building… | Read |
|---|---|
| a new API endpoint | `architecture/api.md` + `data-model/schema.sql` |
| business logic / a service | `architecture/backend.md` |
| a screen / UI component | `architecture/frontend.md` |
| auth / permissions | `architecture/security.md` |
| a data table / migration | `data-model/schema.sql` + `data-model/data-dictionary.md` |
| an external integration | `architecture/integration.md` |
| deploying / environments / CI | `architecture/infrastructure.md` |

## Conventions & constraints
- <naming conventions (e.g. snake_case tables, camelCase JSON)>
- <non-functional targets: p95 latency, throughput, availability>
- <hard constraints: compliance, data residency, tech mandates>

## Open items ([TO CONFIRM])
Resolve these with the architect/client before or during build:
- [ ] <open item> — <source doc / section>
- [ ] <open item> — <…>

---
_Generated from the design artifacts on <date>. If a design doc changes, re-run `design-handoff`
to refresh this folder._
```

---

## Notes for filling it

- **Links are relative** to `docs/` so they resolve when the folder is opened on its own.
- Pull the **tech stack** and **conventions** from the Technical Design Overview's tech-stack table
  and design decisions register; pull **non-functional targets** from the requirements' NFR section.
- The **"Where to look for…"** table is what makes the package useful to a coding agent — tailor its
  rows to the docs that actually exist.
- Gather **every `[TO CONFIRM]`** across all docs into the Open items list so nothing is silently
  guessed at build time.
- A coding agent cannot read `.drawio`; make sure `diagrams/index.md` describes each diagram in
  prose and CLAUDE.md's architecture section carries the key flow in words.
