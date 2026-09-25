---
name: project-onboarding
description: >
  Use this skill to onboard a client engagement onto the Kaizen PDP folder structure — either
  scaffolding a brand-new project or reorganising an existing messy project into a PDP-compliant
  structure. It creates the 9 PDP folders (phases 0–8, where 7 is Project Governance and 8 is
  Quality), drops a
  per-phase checklist .xlsx into each phase folder, builds the Project Report Card in Project
  Governance, and seeds the Quality folder. For existing projects it also moves files into the
  right folders (versioned, never overwriting), and the Report Card gains a Gap Analysis sheet
  and a Reorg Manifest sheet tracking what moved where.
  Trigger on: "onboard project", "set up PDP folders", "create project structure",
  "new engagement setup", "scaffold PDP", "reorganize project folders", "make this PDP compliant",
  "fix the folder structure", "organize this project", "set up the project report card",
  "onboard this client", "PDP folder setup".
  This skill GENERATES folders and files. 
---

# project-onboarding Skill

Onboards a client engagement onto the Kaizen PDP structure. The companion to the read-only
`kaizen-pdp-phases` reference: that skill *tells* you the structure, this one *creates and
enforces* it.

Two modes, auto-detected:

| Mode | When | What it does |
|---|---|---|
| **Greenfield** | No PDP folders exist at the root | Scaffold 9 folders + per-phase checklists + Report Card + Quality seeds |
| **Brownfield** | Folders/files already exist but aren't PDP-compliant | Propose a remap, move files (G1-versioned), regenerate all trackers, add Gap Analysis + Reorg Manifest |

> **Guardrails:** This skill follows the shared guardrails (G1–G5) and file conventions (F1–F3)
> defined in the `guardrails` skill of kaizen-pdp-foundation. See that skill for
> version-not-overwrite, confirmation gates, verbatim financial data, deterministic finance,
> approval gates, the folder structure, and the file naming convention.

All deterministic work (folder creation, Excel generation, file moves, manifest logging) is done
by `scripts/pdp_onboard.py`. **You** (the model) provide the judgment: detecting the mode and
classifying which existing file maps to which deliverable. Never hand-write the Excel or move
files yourself — always drive the script.

---

## Step 0 — Locate the Project Root & Project ID

1. Identify the project root (the folder that should contain the numbered phase folders).
   - If a workspace folder is connected, use it. If ambiguous, ask the user to confirm the path.
   - If no folder is connected, use `mcp__cowork__request_cowork_directory`.
2. Determine `PROJECT_ID` per F1: read `.kaizen-project.json` (`PROJECT_ID`) if present, else use
   the root folder name (`[Client Familiar Name] [Timing] [Project Name]`). If neither looks valid, ask the user to
   confirm the Project ID before proceeding.
3. Determine the **engagement type** — it drives which deliverables are mandatory and the gate
   math on the Report Card. One of:
   `deliverable-based` (default), `capability-pod`, `managed-analytics`, `gcc`. If it isn't
   obvious from the SOW / project context, ask the user. Pass it through as `--engagement-type`.
4. **Layout** — the standardized card is the **`full`** layout (default): a Stakeholders column
   plus one column per engagement type (Deliverable-based / Capability Pod / Managed Analytics /
   GCC), with the active type marked `▶` and driving the gate math. A blank reference copy lives
   at `templates/Project Report Card - TEMPLATE.xlsx`. A `compact` layout (single Mandatory
   column) remains available via `--layout compact` if a project wants the leaner sheet, but
   `full` is the firm standard — you normally omit `--layout`.

---

## Step 1 — Detect Mode (Scan)

Always run a scan first — it is read-only and tells you greenfield vs brownfield:

```bash
python "<SKILL_DIR>/scripts/pdp_onboard.py" scan --root "<PROJECT_ROOT>" --out "<SCRATCH>/scan.json"
```

Read `scan.json`. Decide:

- **`is_greenfield: true`** (no compliant folders AND no stray files worth reorganising) → **Greenfield path** (Step 2A).
- **Files exist** (whether or not some compliant folders are present) → **Brownfield path** (Step 2B).
  - Edge case: compliant folders already exist but loose files also sit outside them → still
    brownfield; only the loose/misplaced files get a mapping.

Tell the user which mode you detected and why (e.g. "Found 14 files in `docs/` and `contracts/`,
none in PDP folders → brownfield reorganisation").

---

## Step 2A — Greenfield Scaffold

1. Confirm with the user (G2):
   > "I'll create the 9 PDP folders under `<PROJECT_ROOT>` for project `<PROJECT_ID>`, with a
   > phase checklist in each phase folder, the Project Report Card in `7. Project Governance`,
   > and Quality seeds in `8. Quality`. Reply 'go ahead' to proceed."
2. On approval:

```bash
python "<SKILL_DIR>/scripts/pdp_onboard.py" scaffold --root "<PROJECT_ROOT>" --project-id "<PROJECT_ID>" \
  --engagement-type "<deliverable-based|capability-pod|managed-analytics|gcc>"
```

(Layout defaults to `full` — the standardized card. Add `--layout compact` only if a project
explicitly wants the leaner single-Mandatory sheet.)

3. Report the JSON summary (folders created, files written, engagement type, layout). Skip to Step 3.

---

## Step 2B — Brownfield Reorganisation

This is the judgment-heavy path. Work in five sub-steps.

### 2B.1 — Classify each file

For every file in `scan.json["files"]`, decide which PDP deliverable (if any) it satisfies. Use:

- **Filename + extension signals** ("SOW" → D10, "NDA" → D1, "kickoff*.pptx" → D11, "P3"/"economics"
  → D5, "RAID" → D33, "technical design" → D21, "status*" → D16, etc.).
- **The `taxonomy_hint`** included in the scan (id → name / phase / folder / mandatory).
- **Content** when the name is ambiguous — read the file (Read / extract) before guessing.

Map each file to one of:
- A deliverable ID + phase (0–8) → it will be moved (and optionally renamed to F3).
- Phase `7` or `8` → governance / quality artifacts.
- `null` → genuinely not a deliverable (leave in place, flagged as unclassified in Gap Analysis).

> **You do not need to force-move files that are already in the correct phase folder** (including
> ones tucked in a subfolder like `2. Plan/status reports/…`). After the moves run, a
> reconciliation pass re-scans every phase folder and registers any deliverable file it finds — by
> exact F3 name or by matching the deliverable's key words — so already-correctly-placed files show
> up on the Report Card as Present with their filename in `Actual File(s)`. Only map a file that
> actually needs relocating or renaming.

**Do not guess when unsure.** If a file is plausibly a deliverable but you can't tell which,
leave `deliverable_id: null` with a clear reason and let it surface in Gap Analysis for the EL.

### 2B.2 — Build `mapping.json`

Write a mapping file to scratch:

```json
{
  "moves": [
    {"src": "contracts/Signed SOW final.pdf", "phase": 0, "deliverable_id": "D10",
     "new_name": "<PROJECT_ID> - SOW.pdf", "reason": "Executed SOW"},
    {"src": "P3 model.xlsx", "phase": 0, "deliverable_id": "D5",
     "reason": "P3 economics (kept original name — finance file, do not rename)"},
    {"src": "random/lunch menu.txt", "phase": null, "deliverable_id": null,
     "reason": "Not a project deliverable"}
  ]
}
```

Rules for mapping entries:
- `src` is the relpath exactly as it appears in the scan.
- `new_name` is optional. Include it to rename to the F3 convention (`<PROJECT_ID> - <Name>.<ext>`)
  when you are confident. Omit it to keep the original filename (safer for finance/contract files).
- Multiple files may map to the same deliverable — the script versions them (`… v2`) per G1.
- `phase: null` / `deliverable_id: null` → leave in place, log as unclassified.

### 2B.3 — Mapping review (editable Excel)

Instead of asking the user to eyeball a text table, hand them an **editable Reorg Plan
spreadsheet** so they can correct assignments themselves before anything moves. Generate it from
the mapping:

```bash
python "<SKILL_DIR>/scripts/pdp_onboard.py" build-review \
  --mapping "<SCRATCH>/mapping.json" --out "<SCRATCH>/<PROJECT_ID> - Reorg Plan.xlsx" \
  --project-id "<PROJECT_ID>" --engagement-type "<...>"
```

Present the `.xlsx` (`present_files` in Cowork, or just tell the user the path). One row per
proposed move, with Excel dropdowns:
- **Proposed Phase** — `0. Sales Alignment` … `8. Quality`, or `— Leave in place —` (keep the file
  where it is; logged as unclassified).
- **Proposed Deliverable** — every D-id; mandatory ones for the chosen engagement type are marked
  `*`. Picking a deliverable is authoritative — its phase wins on read-back.
- **Exclude?** — `Y` drops the file from the move set entirely.
- **Reason** — free text, prefilled.

Ask the user to edit the dropdowns and **save the file in place**. When they say they're done,
read it back into the mapping:

```bash
python "<SKILL_DIR>/scripts/pdp_onboard.py" read-review \
  --xlsx "<SCRATCH>/<PROJECT_ID> - Reorg Plan.xlsx" --out "<SCRATCH>/mapping.json"
```

`read-review` overwrites `mapping.json` with the user's edits (this is the source of truth now);
then proceed to the dry-run (2B.4). Everything stays local — no web artifact, no copy-paste.

This step is recommended but optional — if the user prefers, skip straight to the text dry-run.

### 2B.4 — Dry-run preview + confirmation gate (G2)

Always preview before moving anything:

```bash
python "<SKILL_DIR>/scripts/pdp_onboard.py" apply-reorg --root "<PROJECT_ROOT>" \
  --project-id "<PROJECT_ID>" --mapping "<SCRATCH>/mapping.json" --dry-run
```

Present the planned moves and gaps to the user as a table:
```
Proposed reorganisation for <PROJECT_ID>:
  contracts/Signed SOW final.pdf  →  0. Sales Alignment/<PROJECT_ID> - SOW.pdf   (D10)
  docs/Kickoff Deck v3.pptx       →  1. Sales Handoff & Transition/...           (D11)
  random/lunch menu.txt           →  (left in place — unclassified)
Missing mandatory deliverables: D4, D5, D9, ...
Reply "go ahead" to perform the moves, or tell me what to reclassify.
```
Wait for explicit approval. If the user reclassifies anything, edit `mapping.json` and re-run the
dry-run. (If they did the reclassifying in the 2B.3 artifact, `mapping.json` already reflects it.)

### 2B.5 — Apply

```bash
python "<SKILL_DIR>/scripts/pdp_onboard.py" apply-reorg --root "<PROJECT_ROOT>" \
  --project-id "<PROJECT_ID>" --mapping "<SCRATCH>/mapping.json" \
  --engagement-type "<...>"
```

> Pass the same `--engagement-type` on both the dry-run and the apply so the preview matches the
> generated card. Layout defaults to `full`; add `--layout compact` to both runs if needed.

The script moves files (G1-versioned), then runs a **reconciliation pass** that re-scans every
phase folder (including subfolders) and registers any deliverable files already sitting there so
the Report Card's `Present?` / `Actual File(s)` columns reflect what is actually on disk — not
just this run's moves. It then prunes emptied non-compliant folders, regenerates every checklist,
and rebuilds the Report Card with **Gap Analysis** and **Reorg Manifest** sheets (the manifest
logs both moves and files registered in place), plus the Quality placement audit and onboarding
audit trail. Reconciliation is read-only on the filesystem, so re-running `apply-reorg` (even with
an empty mapping) is a safe way to just **refresh the Report Card** after files change.

---

## Step 3 — Present Results & Summarise

Present the written files with `mcp__cowork__present_files`, then summarise in chat:

```
✅ <PROJECT_ID> onboarded (<greenfield|brownfield>)

Folders: 9 PDP folders ready (0–8 phases; 7 Project Governance, 8 Quality)
Checklists: one per phase folder (deliverables + tasks for that phase)
Report Card: 7. Project Governance/<PROJECT_ID> - Project Report Card.xlsx
  • Dashboard — per-phase completion & gate status (for the chosen engagement type)
  • Deliverables / Tasks — full D1–D41 / T1–T40 tracker, with a Stakeholders column and all 4
    engagement-type applicability columns (active type marked ▶, drives the gate)
  • Gap Analysis — N missing mandatory items, M unclassified files   (brownfield only)
  • Reorg Manifest — K files moved                                    (brownfield only)
Quality: Placement & Naming Audit + Onboarding Audit Trail + README of recommended checks

Next steps:
  • Review unclassified files: [list]
  • Mandatory gaps to close: [top items]
  • Say "what's next" to use the kaizen-pdp-phases reference for phase guidance.
```

---

## What Goes in Each Folder (reference)

| Folder | Contents |
|---|---|
| `0.`–`6.` (phases) | Deliverables for that phase + a **Phase Checklist.xlsx** listing them |
| `7. Project Governance` | RAID Log/RACI Chart/Value Tracker/BCP/Governance scorecard (D33–D37) + **Project Report Card.xlsx** (cross-phase dashboard + gap/manifest) |
| `8. Quality` | CSAT/Quality Plan/Metrics/Risk (D38–D41) + Placement & Naming Audit, Onboarding Audit Trail, Quality README |

The full taxonomy (D1–D41, T1–T40, mandatory flags, **and per-engagement-type applicability**)
lives in `scripts/pdp_onboard.py` (`PHASES`), kept in sync with
`kaizen-pdp-phases/references/pdp-checklist.md`. The applicability matrix mirrors the
engagement-type columns of `PDP Deliverables June222026.xlsx` (the source sheet).

### Report Card template

The generated Report Card **is** the standardized template — there is one firm standard:
`templates/Project Report Card - TEMPLATE.xlsx` (a blank reference copy). Its Deliverables sheet
carries a **Stakeholders** column plus all four engagement-type columns (Deliverable-based /
Capability Pod / Managed Analytics / GCC); the active engagement type is marked `▶` and drives the
Mandatory/gate math. The `Stakeholders` and `Notes` columns are intentionally left blank for the
team to fill per project.

The leaner single-Mandatory `compact` layout is still selectable (`--layout compact`) but is not
the standard, so no compact template ships in `templates/`.

### Mapping-review spreadsheet (brownfield)

The Step 2B.3 editor is an Excel file generated by `build-review` and read back by `read-review`
(both in `scripts/pdp_onboard.py`). Its dropdown options (phases, deliverables with mandatory `*`)
are built from the canonical `PHASES` and the active engagement type, so the plan always matches
the standardized Report Card. The two commands are a matched pair — the `Reorg Plan` sheet name,
header row, and data-start row are shared constants; change them in lockstep if you edit either.

---

## Quality Folder

Seeded on day 0:
- **Folder Placement & Naming Audit** — verifies every file is in the correct phase folder (F2)
  and matches the F3 naming convention. Auto-populated during brownfield reorg.
- **Onboarding Audit Trail** — record of what onboarding created and moved.
- **Quality - README.md** — lists recommended additions to build as the project matures
  (Phase-Gate Exit Checklist, Peer Review / QA Sign-off Log, Definition of Done, Version-Control /
  Change Log, Data Quality Validation Log, Test & UAT Evidence Index).

---

## Notes & Known Issues

- **Mandatory count is engagement-dependent.** The taxonomy has 41 deliverables; for the
  baseline `deliverable-based` type, 33 are mandatory (per the PDP checklist summary). Other
  engagement types are narrower — e.g. `managed-analytics` ≈ 23 mandatory — because the source
  sheet marks fewer deliverables as required for them. The Report Card's gate math always
  reflects the engagement type it was generated with.
- Phase 8 Quality items D39–D41 (Quality Plan, Project Metrics, Risk assessment Sheet) are
  encoded as non-mandatory for every engagement type because the source sheet leaves their
  applicability blank; update their codes in `PHASES` if the firm defines them.
- **Tracking artifacts vs deliverables:** the script refreshes its own checklists/Report Card in
  place on re-run (they are tool-generated trackers). G1 versioning protects *user* deliverables
  on move — it never overwrites a client file.
- **Report Card reflects on-disk reality (reconciliation):** `Present?` / `Actual File(s)` are no
  longer derived only from the move manifest. After moves, `reconcile_existing()` walks each phase
  folder (recursively) and registers any file that maps to a deliverable — via exact F3-name match
  or a conservative token-subset match against that phase's deliverable names — so pre-placed files
  and files in subfolders (e.g. `2. Plan/status reports/…`) are correctly marked Present. Matching
  works off deliverable names in `PHASES`, so it needs no changes when the D-numbering changes. It
  is non-destructive (registers, never moves/renames) and conservative: a file that doesn't clearly
  match a deliverable in its phase is left unregistered rather than guessed. If a correctly-placed
  file isn't picked up, check that its name contains the deliverable's key words, or rename it to
  the F3 convention.
- The script encodes the taxonomy directly. If `pdp-checklist.md` changes, update `PHASES` to match.

---

## Error Handling

| Situation | Action |
|---|---|
| Project root ambiguous / not connected | Ask user to confirm path; use `request_cowork_directory` |
| `PROJECT_ID` not derivable | Ask the user before scaffolding |
| Engagement type unclear from context | Ask the user; default to `deliverable-based` only if they confirm |
| `openpyxl` not installed | `pip install openpyxl --break-system-packages` |
| A file's deliverable is unclear | Leave `deliverable_id: null` with a reason; surface in Gap Analysis — never guess |
| File cannot be read for classification | Report it; leave unclassified; never silently skip |
| Destination filename collision | Script applies G1 (`v2`, `v3`, …) automatically |
| Compliant folders already exist | Idempotent — folders aren't recreated; only loose files get mapped |
| User wants to keep originals (no move) | Re-run with copies instead, or set entries to leave-in-place; confirm intent first |

---

_Last reviewed: 2026-07-07 — added on-disk reconciliation so the Report Card reflects
already-placed files (incl. nested subfolders and non-F3 names), not just this run's moves._
