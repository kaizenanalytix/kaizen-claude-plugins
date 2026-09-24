---
name: design-handoff
description: >
  Use this skill when an Architect or Tech Lead wants to package the completed design — the design
  documents plus the data model files — into a clean `docs/` folder of Markdown with a root
  CLAUDE.md, ready to hand to a downstream build team or a full-stack coding plugin / Claude Code
  session. Trigger on: "design handoff", "handoff package", "handoff to engineering", "handoff to
  build", "prepare the design for claude code", "generate the docs folder", "create claude.md from
  the design", "package the design docs", "developer handoff", "build handoff", "convert the design
  to markdown". Reads the design documents (.docx) and the data model (ERD / DDL / data dictionary),
  converts them into a structured `docs/` folder of Markdown files plus a CLAUDE.md entry point, and
  saves it under the project folder.
---

# design-handoff Skill

Turn the finished **design artifacts** (the technical design documents and the data model) into a
self-contained **`docs/` folder of Markdown** with a **root `CLAUDE.md`** — the package a full-stack
build plugin or a Claude Code session opens to understand the architecture that was designed here
and start building from it.

The design artifacts in this plugin are authored as `.docx` / `.xlsx` / `.sql` / `.drawio` (great
for review and sign-off, opaque to a coding agent). This skill re-expresses them as clean,
link-navigable Markdown that a coding agent can read directly, indexed by a CLAUDE.md that tells the
agent what exists, where it is, and how to use it.

> **Guardrails:** Before writing anything, show the proposed `docs/` tree and get the user's
> confirmation. Never overwrite an existing handoff — if `docs/` already exists, write to a new
> version (`docs v2/`) or ask. Preserve the design's technology choices, requirement IDs, and data
> definitions **verbatim** — this is a faithful re-expression, not a redesign. Carry `[TO CONFIRM]`
> markers across unchanged; never invent decisions the source docs didn't make.

---

## Step 0 — Locate the working folder

Find the connected/working **project folder**. If none is connected, ask the user to connect or
point to it. The handoff is written to a `docs/` subfolder under it.

## Step 1 — Inventory the design artifacts

Search the project folder and list what design output exists (these are typically produced by the
sibling skills `technical-design`, `data-model`, `dataflow-diagrams`, `e2e-diagrams`,
`business-requirements`):

| Artifact | Typical source | Becomes |
|---|---|---|
| Technical Design Overview (.docx) | `design/` | `docs/architecture/overview.md` |
| Back-end / Front-end / API / Integration / Security / Infrastructure / Processing Design (.docx) | `design/` | `docs/architecture/<name>.md` |
| Business Requirements (.docx) | `requirements/` | `docs/requirements.md` |
| ERD (.drawio / .png) | `data-model/` | referenced in `docs/data-model/schema.md` + copied to `docs/diagrams/` |
| DDL (.sql) | `data-model/` | copied to `docs/data-model/schema.sql` and summarised in `schema.md` |
| Data Dictionary (.xlsx) | `data-model/` | `docs/data-model/data-dictionary.md` (Markdown tables) |
| Solution overview / data-flow diagrams (.drawio / .png) | `diagrams/` | referenced in `docs/architecture/overview.md` + copied to `docs/diagrams/` |

If little or nothing is found, tell the user which artifacts are missing and offer to run the skills
that produce them first. Proceed with whatever exists — the package is best-effort and notes gaps.

## Step 2 — Extract the content

Read each source artifact and extract its content using an appropriate reader for its file type
(text from `.docx`; sheet rows from `.xlsx`; raw SQL from `.sql`; the title/labels or a rendered
`.png` from `.drawio`). Keep headings, tables, requirement IDs (`FR-###` / `NFR-###`), technology
names and versions, and the design decisions register intact.

## Step 3 — Build the `docs/` tree

Create this structure (include only the parts that have source content):

```
docs/
├── CLAUDE.md                     ← entry point / index for the coding agent (see Step 4)
├── README.md                     ← short human-facing orientation (same summary, prose)
├── requirements.md               ← functional + non-functional requirements (with IDs)
├── architecture/
│   ├── overview.md               ← system summary, tech-stack table, component map, decisions register
│   ├── backend.md
│   ├── frontend.md               ← (only if a Front-end Design exists)
│   ├── api.md                    ← endpoints, contracts, auth
│   ├── integration.md            ← (only if an Integration Design exists)
│   ├── security.md
│   ├── infrastructure.md         ← environments, hosting, CI/CD, deployment
│   └── processing.md             ← (only if a Processing/Algorithm/ML Design exists)
├── data-model/
│   ├── schema.md                 ← narrative: entities, relationships, keys, grain; links the DDL
│   ├── schema.sql                ← the DDL, copied verbatim
│   └── data-dictionary.md        ← per-table column tables (from the Data Dictionary xlsx)
└── diagrams/
    ├── <diagram>.drawio / .png   ← copied editable + rendered diagrams
    └── index.md                  ← one line per diagram: what it shows + the file
```

For each design `.docx`, write a Markdown file that preserves its section structure, converts its
tables to Markdown tables, and keeps the traceability (requirement IDs). Convert the Data Dictionary
sheets into Markdown tables (one section per table). Copy the DDL `.sql` verbatim into
`data-model/schema.sql` and reference it from `schema.md`. Copy the diagram files into
`docs/diagrams/` and describe each in `diagrams/index.md` (a coding agent can't read a `.drawio`, so
the prose description matters; include the `.png` where one exists).

## Step 4 — Write CLAUDE.md (the entry point)

`docs/CLAUDE.md` is the file a full-stack plugin / Claude Code session reads first. Build it from
`references/claude-md-template.md`. It must give a coding agent, concisely and with links:

1. **What this is** — one-paragraph summary of the system and its purpose.
2. **Tech stack** — the decided technologies per tier (from the design decisions register / overview
   tech-stack table), exact versions where known.
3. **Architecture map** — the components and how they fit, each linking to its detailed doc under
   `architecture/`.
4. **Data model** — a one-line-per-entity summary and links to `data-model/schema.sql` (the source
   of truth for tables) and `data-model/data-dictionary.md`.
5. **Requirements** — where the functional/NFR requirements live (`requirements.md`) and the highest-
   priority "Must have" items to build first.
6. **Where to look for X** — a task → doc routing table ("building an endpoint → `architecture/api.md`
   + `data-model/schema.sql`; auth → `architecture/security.md`; deploying → `architecture/infrastructure.md`").
7. **Conventions & constraints** — naming, non-functional targets, and any hard constraints the
   build must honour.
8. **Open items** — every `[TO CONFIRM]` gathered from the docs, so the build team resolves them
   before/while coding.

Keep CLAUDE.md skimmable (links over prose dumps) — it routes the agent to the detailed docs rather
than restating them.

## Step 5 — Present & save

Show the proposed `docs/` tree and a one-line summary of each file, then confirm before writing.
On confirmation, create `docs/` under the project folder (versioning instead of overwriting) and
share the CLAUDE.md and the tree with the user.

```
✅ Design handoff package generated: docs/
   • CLAUDE.md  +  README.md
   • architecture/ : N docs   • data-model/ : schema.md, schema.sql, data-dictionary.md
   • requirements.md   • diagrams/ : N files

Open items carried into CLAUDE.md: N  ([TO CONFIRM] markers)
Hand this docs/ folder to the build team or point a full-stack plugin / Claude Code at it.
```

---

## Error handling

| Situation | Action |
|---|---|
| No design docs or data model found | List what's missing; offer to run `technical-design` / `data-model` first; package what exists |
| A source `.docx` won't extract | Note it in CLAUDE.md's open items; link the original file; continue |
| `.drawio` can't be rendered to PNG | Copy the `.drawio` and write a prose description in `diagrams/index.md` |
| `docs/` already exists | Don't overwrite — write `docs v2/` or ask the user |
| Data dictionary xlsx missing but DDL present | Build `schema.md` from the DDL; note the dictionary is absent |
| No project folder connected | Ask the user to connect or point to it |

_Last reviewed: 2026-08-27_
