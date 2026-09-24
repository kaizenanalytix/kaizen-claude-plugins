# sales-handoff-brief

Synthesises all Phase 0 Sales Alignment documents into a structured Sales-to-Delivery Knowledge
Transfer (KT) Brief for the Kaizen delivery team. Reads everything in `0. Sales Alignment/` and
writes a formatted `.docx` to `1. Sales Handoff & Transition/`.

This is the **first** skill in the Sales Handoff flow — the KT Brief it produces is the
prerequisite input for the other three skills in the plugin.

## When to use it

The Engagement Lead (EL) wants to generate the KT Brief from the Phase 0 sales documents.

Trigger phrases:
- "generate handoff brief"
- "create KT brief"
- "sales handoff summary"
- "knowledge transfer brief"
- "generate sales brief"
- "handoff to delivery team"
- "create the brief"
- "run the KT brief"
- "sales to delivery handoff"

## Layout

```
sales-handoff-brief/
├── SKILL.md                       # Full workflow the model follows (start here)
├── README.md                      # This file
└── references/
    └── brief-template.md          # Reference structure for the KT Brief
```

## What it does

| Step | Action |
|---|---|
| 0 | Locate the project root (folder with `0. Sales Alignment/` and `1. Sales Handoff & Transition/`) and derive `PROJECT_ID` |
| 1 | Inventory and classify every Phase 0 document (SOW, proposal, solution overview, NDA, MSA, P3, data request, scope/estimation, DRC) |
| 2 | Extract text from each file (PDF via `pdftotext`; DOCX/PPTX/XLSX via python-docx / python-pptx / openpyxl / pandas) |
| 3 | Populate structured fields — deal summary, scope, solution approach, data requirements, risks, commercial terms, team, open items |
| 4 | Generate the KT Brief `.docx` (10 sections incl. Phase 0 checklist status and recommended Phase 1 next steps) |
| 5 | Save to `1. Sales Handoff & Transition/<PROJECT_ID> - KT Brief.docx` |
| 6 | Present a chat summary flagging follow-up fields and risks |

The brief is a summary, not a reproduction: it must be skimmable in under 10 minutes. Missing
fields are highlighted orange ("Not specified — confirm with sales lead"); penalty clauses and
SLA commitments are highlighted yellow.

## Notes

- Reads the shared `docx` skill before generating the document.
- No CLI script — extraction and generation are done inline with Python (python-docx, python-pptx,
  openpyxl, pandas, poppler-utils).

## See also

- `../project-kickoff-init` — next step: builds the kickoff deck, requirements review, project
  plan, and technical checklist from this brief.
- `../project-backlog-init` — stands up the epic backlog (requires this brief).
- `../raid-raci-setup` — sets up the RAID Log and RACI Chart (requires this brief).
