# project-backlog-init

Creates an initial project backlog at the **epic level only**, grouped by functional area of the
solution (not by PDP phase). Reads the SOW/scope from `0. Sales Alignment/` and the KT Brief from
`1. Sales Handoff & Transition/`, generates an Excel workbook for EL review, and pushes to Jira
**only after explicit EL approval**.

**Prerequisite:** the `sales-handoff-brief` (KT Brief) must have been run and EL-approved.

## When to use it

The Engagement Lead (EL) wants to create an initial epic-level backlog for a Kaizen PDP engagement.

Trigger phrases:
- "set up backlog" / "create project backlog" / "project backlog setup"
- "generate epics" / "build epic backlog" / "epic planning"
- "plan the backlog" / "create epics in Jira"
- "initial backlog setup" / "set up project epics"

## What it does

| Step | Action |
|---|---|
| 0 | Locate source documents (SOW in `0. Sales Alignment/`, KT Brief in `1. Sales Handoff & Transition/`) |
| 1 | Extract scope and solution context into a solution scope summary |
| 2 | Derive functional epics — mutually exclusive, every SOW deliverable maps to exactly one epic |
| 3 | Generate the Epic Backlog `.xlsx` (Sheet 1: Epic Backlog, Sheet 2: Project Setup), saved to `2. Plan/` |
| 4 | **GATE** — wait for explicit EL approval before pushing anything |
| 5 | Push epics to Jira via the Atlassian MCP connector, after approval only |

Two cross-cutting epics are always included regardless of solution: **Project Governance** and
**Environment & Infrastructure**.

## Layout

```
project-backlog-init/
├── SKILL.md                       # Full workflow the model follows (start here)
├── README.md                      # This file
└── references/
    └── epic-format.md             # Reference format for epic definitions
```

## Approval gate

The skill never pushes to Jira without explicit EL sign-off. Accepted approval phrases include
"approved", "push to Jira", "push it", "go ahead", "looks good", "create in Jira". On "cancel" /
"stop" nothing is pushed and the Excel remains in `2. Plan/`.

## Jira integration

Pushing uses the **Atlassian Jira MCP connector**. If the connector is unavailable the skill saves
the Excel only and advises the user to reconnect Atlassian and retry. On push it creates the Jira
project (if needed) and all epics in priority order, labelling each `pdp-backlog` for traceability.

## Notes

- No CLI script — the Excel is generated inline with openpyxl.

## See also

- `../sales-handoff-brief` — produces the KT Brief this skill consumes (run first).
- `../project-kickoff-init` — produces the kickoff package; run before or alongside backlog setup.
- `../raid-raci-setup` — sets up the RAID Log and RACI Chart.
