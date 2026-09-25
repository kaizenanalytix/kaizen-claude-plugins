# PDP Sales Handoff

Helps delivery teams pick up a newly sold project from sales and get it off the ground. It turns
the sales materials into a knowledge-transfer brief for the delivery team, prepares the kickoff
deck and initial project plan, stands up the project backlog (and pushes it to Jira), and sets up
the RAID log and RACI chart that keep roles and risks clear from day one.

This plugin covers the **sales-to-delivery handoff / project startup phase** of the Kaizen PDP —
the transition from Phase 0 (Sales Alignment) through Phase 1 (Sales Handoff & Transition) into
the Plan and Project Governance phases.

**Version:** 3.0.0 · **Author:** Kaizen Analytix LLC

## Skills

| Skill | What it does |
|---|---|
| [sales-handoff-brief](skills/sales-handoff-brief/README.md) | Generates a Sales-to-Delivery Knowledge Transfer Brief (`.docx`) from the Phase 0 sales documents. |
| [project-kickoff-init](skills/project-kickoff-init/README.md) | Initialises the kickoff package in one pass — kickoff deck, requirements review, project plan, and technical checklist. |
| [project-backlog-init](skills/project-backlog-init/README.md) | Creates an initial epic-level project backlog for EL review, and pushes it to Jira after explicit approval. |
| [raid-raci-setup](skills/raid-raci-setup/README.md) | Sets up the RAID Log (D33) and RACI Chart (D34) so roles and risks are clear from day one. |

## Typical flow

The KT Brief comes first — it is the prerequisite input for the other three skills:

```
sales-handoff-brief   →   project-kickoff-init
(KT Brief)                project-backlog-init
                          raid-raci-setup
```

1. **sales-handoff-brief** reads `0. Sales Alignment/` and writes the KT Brief to
   `1. Sales Handoff & Transition/`.
2. **project-kickoff-init** synthesises the kickoff package into `2. Plan/`.
3. **project-backlog-init** derives functional epics into `2. Plan/` and pushes to Jira on approval.
4. **raid-raci-setup** produces the RAID Log and RACI Chart into `7. Project Governance/`.
