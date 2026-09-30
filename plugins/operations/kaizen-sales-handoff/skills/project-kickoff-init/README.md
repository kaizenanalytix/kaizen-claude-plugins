# project-kickoff-init

Initialises the full project kickoff package in one pass. Reads the Phase 0 client documents from
`0. Sales Alignment/` and the KT Brief from `1. Sales Handoff & Transition/`, synthesises a unified
delivery context, and produces five deliverables.

**Prerequisite:** the `sales-handoff-brief` (KT Brief) must have been run and EL-approved.

## When to use it

The Engagement Lead (EL) wants to initialise the project kickoff package — the kickoff deck,
requirements review, project plan, project charter, and technical checklist together.

Trigger phrases:
- "project kickoff" / "kickoff init" / "initialise kickoff"
- "generate kickoff package" / "kickoff deck" / "create kickoff"
- "project kickoff init" / "kickoff setup"
- "generate kickoff PPT" / "create kickoff deck"
- "internal kickoff" / "project setup"
- "project charter" / "fill the charter" / "generate charter"

## Deliverables

| # | Deliverable | Format | Built by | Saved to |
|---|---|---|---|---|
| 1 | Internal Kickoff Deck | `.pptx` | kaizen-pptx-template (13-slide map) | `2. Plan/` |
| 2 | Requirements Document | `.docx` | Generated from scratch (gap analysis) | `2. Plan/` |
| 3 | Project Plan | `.xlsx` | **Populating the Kaizen Gantt template** | `2. Plan/` |
| 4 | Project Charter (D12) | `.docx` | **Populating the charter template** | `1. Sales Handoff & Transition/` |
| 5 | Technical Checklist (D13) | `.xlsx` | Generated from scratch (7 categories) | `1. Sales Handoff & Transition/` |

Files are named `<PROJECT_ID> - <deliverable>.<ext>`. Deliverables 3 and 4 are produced by
**filling the bundled templates** in `templates/`, not by regenerating structure from scratch.

## Layout

```
project-kickoff-init/
├── SKILL.md                              # Full workflow the model follows (start here)
├── README.md                             # This file
├── templates/
│   ├── Kaizen_Project_Plan_Template.xlsx # Deliverable 3 — Gantt (Architecture/ResourceList/Status)
│   └── Project_Charter_Template.docx     # Deliverable 4 — sectioned charter (D12)
└── references/                           # (currently empty)
```

## No economics

No deliverable may include TCV, hourly rates, investment breakdowns, commercial model details,
GM percentages, or billing terms. P3 Project Economics (D5) files are ignored; any economic data
found in source documents is skipped entirely. The charter has no budget row — keep it that way.

## Notes

- Builds the deck by invoking the **kaizen-pptx-template** skill and following its workflow
  (unpack → add slides → raw XML content edits → repack → QA). Falls back to the generic `pptx`
  skill if unavailable. Content is edited via raw slide XML, never the python-pptx placeholder API.
- The **Project Plan** and **Project Charter** are produced by copying the bundled templates to
  `/tmp/`, populating cells/fields, then saving to the destination — the templates are never
  edited in place. The plan's Gantt week-grid formulas and the charter's instructions table are
  left untouched.
- Binary source files (`.docx`/`.pptx`/`.xlsx`) are copied to `/tmp/` first to force OneDrive
  download; cloud-only stubs are flagged, never silently skipped.
- Dependencies: python-pptx, python-docx, openpyxl.

## See also

- `../sales-handoff-brief` — produces the KT Brief this skill consumes (run first).
- `../project-backlog-init` — suggested next step: stands up the epic backlog.
- `../raid-raci-setup` — sets up the RAID Log and RACI Chart.
