# generate-report-card

Scans an already-onboarded Kaizen PDP project (the numbered phase folders on disk) and
(re)generates the **Project Report Card** — a Dashboard of per-phase completion plus the full
D1–D41 Deliverables tracker. A fast, **read-only** re-scan for an up-to-date status snapshot: it
never moves, renames, deletes, or creates files or phase folders.

It is the lightweight companion to `project-onboarding`. That skill *sets up* the PDP structure
and builds the first Report Card; this one *re-scans* an already-compliant (or mostly-compliant)
project and refreshes the Report Card to match what's actually on disk. Because the output
filename and location match exactly, running it after `project-onboarding` simply refreshes the
same file with a leaner sheet set (Dashboard + Deliverables only — no Tasks, Gap Analysis, Reorg
Manifest, per-phase checklists, or Quality audit files).

## When to use it

Trigger phrases:

- "refresh / regenerate / update the report card"
- "rescan the project" / "scan the project folders"
- "how compliant is this project" / "project health check"
- "status snapshot" / "check deliverable completion" / "what's missing"
- "is this project up to date"

If the project isn't onboarded yet (no numbered phase folders), or the user wants folders
scaffolded or files reorganised, use `project-onboarding` instead.

## Layout

```
generate-report-card/
├── SKILL.md                          # Full workflow the model follows (start here)
├── README.md                         # This file
└── scripts/
    └── generate_report_card.py       # All scanning + Excel generation (the CLI below)
```

## Script CLI (`scripts/generate_report_card.py`)

A single command (no subcommands) that walks the 9 phase folders that exist, matches files to
deliverables, and writes the Report Card.

| Flag | Required | Purpose |
|---|---|---|
| `--root` | yes | Project root folder (contains the numbered phase folders) |
| `--project-id` | no | Project ID (F1). Default: `.kaizen-project.json`, else the root folder name |
| `--engagement-type` | no | `deliverable-based` (default) \| `capability-pod` \| `managed-analytics` \| `gcc` — drives mandatory/gate math. Default: `.kaizen-project.json`, else `deliverable-based` |
| `--out` | no | Explicit output `.xlsx` path. Default: `<root>/7. Project Governance/<PROJECT_ID> - Project Report Card.xlsx` if that folder exists, else `<root>/<PROJECT_ID> - Project Report Card.xlsx` |

```bash
python "<SKILL_DIR>/scripts/generate_report_card.py" --root "<PROJECT_ROOT>" \
  --engagement-type deliverable-based
```

The script prints a JSON summary to stdout (output path, folders found vs. total, missing
folders, mandatory totals, and any unclassified files per phase) — the model translates that into
a plain-language status summary.

Matching is conservative on purpose: a file only counts if it matches the F3 name exactly or
contains every significant word of the deliverable name. Near-misses are left **unclassified**
rather than mis-attributed, and are never renamed or moved.

## Requirements

- Python 3 with `openpyxl` (`pip install openpyxl --break-system-packages` if missing).

## See also

- `SKILL.md` — the full step-by-step workflow, notes, and error handling.
- `../project-onboarding` — first-time setup, brownfield reorg, and the richer Report Card.
- `../guardrails` — shared guardrails (G1–G5) and file conventions (F1–F3) this scan relies on.
- `../kaizen-pdp-phases` — read-only reference for the PDP structure and the D1–D41 taxonomy.
