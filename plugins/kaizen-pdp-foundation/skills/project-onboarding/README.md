# project-onboarding

Onboards a client engagement onto the Kaizen PDP folder structure — either scaffolding a
brand-new project (**greenfield**) or reorganising an existing messy project into a
PDP-compliant structure (**brownfield**).

It creates the 9 PDP folders (phases 0–8, where 7 is Project Governance and 8 is Quality),
drops a per-phase checklist `.xlsx` into each phase folder, builds the Project Report Card in
Project Governance, and seeds the Quality folder. For existing projects it also moves files
into the right folders (versioned, never overwriting), and the Report Card gains a **Gap
Analysis** sheet and a **Reorg Manifest** sheet tracking what moved where.

This is the companion to the read-only `kaizen-pdp-phases` reference: that skill *tells* you the
structure, this one *creates and enforces* it.

## Two modes (auto-detected)

| Mode | When | What it does |
|---|---|---|
| **Greenfield** | No PDP folders exist at the root | Scaffold 9 folders + per-phase checklists + Report Card + Quality seeds |
| **Brownfield** | Files already exist but aren't PDP-compliant | Propose a remap, move files (G1-versioned), regenerate all trackers, add Gap Analysis + Reorg Manifest |

All deterministic work (folder creation, Excel generation, file moves, manifest logging) is done
by `scripts/pdp_onboard.py`. The model provides the judgment: detecting the mode and classifying
which existing file maps to which deliverable. Never hand-write the Excel or move files by hand —
always drive the script.

## Layout

```
project-onboarding/
├── SKILL.md                                   # Full workflow the model follows (start here)
├── README.md                                  # This file
├── scripts/
│   └── pdp_onboard.py                         # All deterministic work (the CLI below)
└── templates/
    └── Project Report Card - TEMPLATE.xlsx    # Blank reference copy of the standardized card
```

## Script CLI (`scripts/pdp_onboard.py`)

| Command | Purpose |
|---|---|
| `scan` | Inventory existing files for classification (read-only; detects greenfield vs brownfield) |
| `scaffold` | Create the folder structure + tracking artifacts (greenfield) |
| `build-review` | Generate an editable Reorg Plan `.xlsx` from a mapping (brownfield) |
| `read-review` | Read the user's edited Reorg Plan back into `mapping.json` (brownfield) |
| `apply-reorg` | Move mapped files + regenerate artifacts; supports `--dry-run` (brownfield) |

Common flags: `--root` (project root), `--project-id`, `--engagement-type`
(`deliverable-based` | `capability-pod` | `managed-analytics` | `gcc`, default
`deliverable-based`), `--layout` (`full` default | `compact`).

### Typical greenfield run

```bash
python scripts/pdp_onboard.py scan     --root "<PROJECT_ROOT>" --out "<SCRATCH>/scan.json"
python scripts/pdp_onboard.py scaffold --root "<PROJECT_ROOT>" --project-id "<PROJECT_ID>" \
  --engagement-type deliverable-based
```

### Typical brownfield run

```bash
python scripts/pdp_onboard.py scan         --root "<PROJECT_ROOT>" --out "<SCRATCH>/scan.json"
# model classifies files → writes mapping.json
python scripts/pdp_onboard.py build-review --mapping "<SCRATCH>/mapping.json" \
  --out "<SCRATCH>/<PROJECT_ID> - Reorg Plan.xlsx" --project-id "<PROJECT_ID>" --engagement-type deliverable-based
# user edits the .xlsx dropdowns, saves in place
python scripts/pdp_onboard.py read-review  --xlsx "<SCRATCH>/<PROJECT_ID> - Reorg Plan.xlsx" --out "<SCRATCH>/mapping.json"
python scripts/pdp_onboard.py apply-reorg  --root "<PROJECT_ROOT>" --project-id "<PROJECT_ID>" \
  --mapping "<SCRATCH>/mapping.json" --dry-run          # preview first
python scripts/pdp_onboard.py apply-reorg  --root "<PROJECT_ROOT>" --project-id "<PROJECT_ID>" \
  --mapping "<SCRATCH>/mapping.json" --engagement-type deliverable-based
```

`apply-reorg` also runs a **reconciliation pass** that re-scans every phase folder (recursively)
and registers deliverable files already sitting there, so the Report Card reflects on-disk
reality — not just this run's moves. Re-running it (even with an empty mapping) is a safe way to
just refresh the Report Card.

## What gets generated

| Folder | Contents |
|---|---|
| `0.`–`6.` (phases) | Deliverables for that phase + a **Phase Checklist.xlsx** |
| `7. Project Governance` | RAID/RACI/Value Tracker/BCP/scorecard (D33–D37) + **Project Report Card.xlsx** (cross-phase dashboard, Gap Analysis, Reorg Manifest) |
| `8. Quality` | CSAT/Quality Plan/Metrics/Risk (D38–D41) + Placement & Naming Audit, Onboarding Audit Trail, Quality README |

## Requirements

- Python 3 with `openpyxl` (`pip install openpyxl --break-system-packages` if missing).

## See also

- `SKILL.md` — the full step-by-step workflow, guardrails, and error handling.
- `../guardrails` — shared guardrails (G1–G5) and file conventions (F1–F3).
- `../kaizen-pdp-phases` — read-only reference for the PDP structure and per-phase guidance.
