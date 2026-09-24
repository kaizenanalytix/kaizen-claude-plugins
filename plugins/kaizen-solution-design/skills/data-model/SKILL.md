---
name: data-model
description: >
  Generate data models — conceptual, logical, physical, and/or dimensional — for an
  engagement, including an ERD, runnable DDL, and a data dictionary. Trigger on: "generate/create
  data model", "logical model", "physical model", "ERD", "entity relationship diagram", "star
  schema", "dimensional model", "fact table", "data dictionary", "generate schema", "table
  design", "DDL", "reverse engineer this schema", and requests to update an existing data model
  from a meeting, email, or document. Also use when the user shares existing DDL, a schema file,
  or an ERD to document or model (brownfield case). Reads the Business Requirements document,
  solution overview, and technical design if present, plus scoped meeting/email sources, and
  writes an ERD (.drawio + PNG), a DBML `.erd` model, DDL, and a Data Dictionary (.xlsx) to a `data-model/` folder.
---

# data-model Skill

Generate (or extend) a data model for an engagement. Output: an ERD, DDL script(s) for
one or more target platforms, and a Data Dictionary — saved to a `data-model/` folder under the
working project folder. This is a standalone artifact.

This skill covers four modeling stages — conceptual, logical, physical, and dimensional — and two
generation modes — inferring a model from project sources, or taking structured input directly
from the user. Both are supported; use whichever fits, and confirm with the user when it's unclear
which one they want.

---

## Step 0 — Locate the Working Folder and Scope

Work inside a single connected/working project folder. If no folder is connected, ask the user to
connect or point to the project folder. If the working folder is ambiguous, ask the user to
confirm the path.

Check for an existing model in the `data-model/` subfolder:

```bash
find "<PROJECT_FOLDER>/data-model/" -type f 2>/dev/null | sort
```

- **No existing model** → this is a fresh build.
- **A model already exists** → this is likely an update (new requirement, brownfield refinement,
  or extending scope e.g. logical → physical). Read the existing files first so you extend rather
  than overwrite — modify in place, don't silently discard prior work.

Ask the user which stage(s) they want **every run** — don't assume the full pipeline. A short
question like "Just the conceptual/logical model, or do you want physical DDL and dimensional
modeling too?" is enough; see `references/conventions.md` for how the stages build on each other.

Also confirm — or infer from the Business Requirements / solution overview — whether the
engagement is **OLTP-style** (transactional system) or **analytics/BI-style** (reporting,
dashboards, data warehouse). This decides whether a dimensional layer is relevant at all.

**Guardrails**: before writing any file, show the proposed path and get confirmation; never
overwrite an existing file — version instead (" v2", " v3", …); keep any financial figures
verbatim.

---

## Step 1 — Gather Inputs

### 1A. Baseline project documents

Search the working project folder recursively for the source documents; if a needed input can't be
found or its location is ambiguous, ask the user to point at the file(s):

```bash
find "<PROJECT_FOLDER>" -type f | sort
```

| Source | Purpose |
|---|---|
| Business Requirements document | Entities, business rules, data volume/frequency hints |
| Solution overview / technical design | System boundaries, source systems, integration points |
| Existing technical design, if present | Existing architecture decisions the model must align with |

### 1B. Meeting notes and email — scoped sourcing

The model is a living artifact — new requirements surface in emails and meetings throughout
design and even build. Use a scoped-search discipline so this never turns into an unbounded
mailbox or transcript trawl:

| Source | How it reaches the skill |
|---|---|
| **Outlook emails** | Ask for the Outlook category/tag first; if none, ask for a subject to search. Never scan the whole mailbox. |
| **Teams transcripts** | Ask for the meeting name first, then search that meeting only (or read a transcript file/path the user provides). Never search all transcripts blindly. |
| **Minutes of Meeting (MoM)** | A file the user provides in chat or points to in the project folder. |
| **Any other project document** | Any file the user points at. |

Confirm the concrete source(s) with the user before extracting. Full extraction protocol and the
signal/noise distinction: `references/source-ingestion.md` — **read this before pulling entities
or attributes out of a meeting/email source**, it defines what counts as a firm requirement versus
a passing mention.

### 1C. Brownfield / reverse-engineering

If the user provides existing DDL, a schema file, sample data, or an existing ERD/diagram: read it
directly and reverse-engineer the conceptual/logical structure from it rather than starting blank.
This skill does not connect to live databases in this version — ask the user to export/share a
schema file, DDL dump, or diagram instead.

---

## Step 2 — Build the Model

Work through whichever stages the user asked for in Step 0:

1. **Conceptual** — entities and relationships in business language only, no keys or types yet.
2. **Logical** — attributes, primary/foreign keys, cardinality, normalization (3NF default for
   OLTP entities — see `references/conventions.md`).
3. **Physical** — platform-specific DDL: types, indexes, partitioning/clustering keys,
   constraints. See `references/ddl-dialects.md` for the type mappings and syntax differences
   across Snowflake, SQL Server, PostgreSQL, and SAP HANA.
4. **Dimensional** (only if the engagement is analytics/BI-style or the user asks) — star vs.
   snowflake decision, fact table grain, SCD type per dimension, conformed dimensions.

All naming, typing, SCD, and metadata-column conventions are in `references/conventions.md` —
apply them as you build, don't wait until the end to retrofit them.

### Weak-signal call-out

While extracting from meeting/email sources (Step 1B), keep two buckets:

- **Clear requirements** ("we need to track X," "must store Y," an explicit client ask) → build
  directly into the model.
- **Passing mentions** (an aside, something said in passing with no clear decision behind it) →
  do **not** silently add these. Hold them and surface as a call-out at the end of the run:
  > "I also noticed these mentioned in passing — want me to add them to the model?
  > • [item] (from [source])"

This applies a dry-run-then-approve pattern to weak signals instead of every extracted item —
clear requirements don't need a gate, ambiguous ones do.

---

## Step 3 — Self-Review Against Best Practices

Before presenting anything to the user, check the model against the checklist in
`references/best-practices.md` (BP-1 through BP-10 — naming, key integrity, normalization
correctness, SCD flagging, no unbounded text, no float currency, metadata columns, explicit fact
grain, bridge tables for M:M, and data-dictionary completeness).

This is a **self-check, not a separate review pass** — just work through the checklist and fix
anything that fails, silently, before generating outputs. Only surface a question to the user if a
fix requires a judgment call you can't make alone (e.g. an ambiguous fact grain with no clear
answer in the sources).

---

## Step 4 — Generate Outputs

All outputs save to a `data-model/` subfolder under the working project folder (create it if
missing).

### ERD — `.drawio` + PNG preview

Build a JSON spec of entities (name, attributes with PK/FK flags, types) and relationships, then
render it:

```bash
python "<SKILL_DIR>/scripts/render_erd.py" --spec spec.json --out "data-model/ERD.drawio"
```

This produces an editable `.drawio` (table-shaped entities, relationship connectors) and a PNG
preview when Pillow is available. See the script's `--help` and docstring for the exact spec
shape. This renderer is specific to this skill (not shared with `dataflow-diagrams` or
`e2e-diagrams` — it evolves independently).

### ERD as DBML — `.erd` (portable text model)

From the **same JSON spec**, also emit the model as DBML — a portable, text-based ER source that
round-trips with dbdiagram.io and the `@dbml/cli` toolchain (`dbml2sql` / `sql2dbml`) and diffs
cleanly in git:

```bash
python "<SKILL_DIR>/scripts/build_dbml.py" --spec spec.json --out "data-model/ERD.erd"
```

The file carries `.erd` (per the house convention) but its **contents are DBML** — `Table` blocks
with column settings (`pk`, `not null`, FK `ref:`, and a `note:` holding the business definition,
SCD type, and source system), explicit `Ref:` lines with cardinality, and `TableGroup`s by kind
(facts / dims / bridges). Foreign keys are defined once (no duplicate references). If a downstream
tool insists on the `.dbml` extension, rename the file — the content is unchanged.

### DDL — one `.sql` file per requested platform

Using the type/naming mappings in `references/ddl-dialects.md`, write runnable DDL:
`data-model/DDL (<platform>).sql`. Default to Snowflake if the user hasn't
specified a platform. Generate additional files if more than one platform was requested.

### Data Dictionary — `.xlsx`, one tab per table

```bash
python "<SKILL_DIR>/scripts/build_data_dictionary.py" --spec spec.json \
  --out "data-model/Data Dictionary.xlsx"
```

Produces a workbook with one sheet per table (columns: Table Name, Column Name, Data Type,
PK/FK, Nullable, Business Definition, Source System, SCD Type, Sample Value, Notes) plus a summary
**Index** sheet listing every table with a jump-link. See the script's docstring for the JSON
spec shape (it's the same spec used for the ERD and the DBML file — build it once, feed all three scripts).

### Source-to-target mapping — only if this model feeds an ETL/ELT build

A simple `.xlsx` in the same folder — `data-model/Source-to-Target Mapping.xlsx`: source
system/table/column → target table/column, with any transformation notes. Only produce this if the user says the model is feeding a data
integration/migration build.

---

## Step 5 — Save and Present

```
Proposed files in "data-model/":
  1. ERD.drawio (+ .png preview)
  2. ERD.erd  (DBML text model)
  3. DDL (<platform>).sql  [one per platform requested]
  4. Data Dictionary.xlsx
```

Share the file(s) with the user. If updating an existing model, note what changed rather than
re-presenting everything as new.

---

## Step 6 — Summary in Chat

```
✅ Data model generated: data-model/

Stages covered: [conceptual / logical / physical / dimensional — whichever applied]
Tables: N   Relationships: N   [Fact tables: N, Dimensions: N — if dimensional]

Best-practices check: passed (or) fixed automatically: [what was corrected]

Mentioned in passing, not yet added — want these included?
  • [item] (source: [meeting/email])
```

---

## Error Handling

| Situation | Action |
|---|---|
| No BRD or Solution Overview found | Ask the user to supply entities directly (structured intake mode), or run those skills first |
| User asks to search email with no category | Ask for the Outlook category/tag; if none, ask for a subject. Never scan the whole mailbox |
| User asks to pull a transcript with no meeting name | Ask for the meeting name first; never search all transcripts blindly |
| Email/transcript connector not authorized | Say so; fall back to a user-supplied file/pasted text |
| Brownfield source is a live DB connection request | Not supported in this version — ask for an exported schema/DDL file instead |
| An extracted item is ambiguous (requirement vs. passing mention) | Default to the passing-mention bucket — surface it for approval rather than guessing it in |
| A best-practice check fails and the fix is ambiguous | Ask the user rather than guessing (e.g. unclear fact grain) |
| `openpyxl` not installed | `pip install openpyxl --break-system-packages` |
| Pillow not installed | Skip PNG preview; `.drawio` still generated |
| Project root ambiguous | Ask the user to confirm the path |

---

_Last reviewed: 2026-08-27_
