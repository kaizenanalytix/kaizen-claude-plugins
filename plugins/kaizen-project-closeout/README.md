# PDP Closure

Helps delivery teams wrap up a Kaizen PDP project cleanly. It prepares the ongoing support plan
for handoff, captures formal client sign-off, writes the project up as a case study, and closes
things out with a lessons-learned summary and a properly archived project.

This plugin covers the **project closeout / wrap-up phase** of the Kaizen PDP — the deliverables
that land in `6. Deploy` (D29–D32) plus the T40 archive that ends the project lifecycle.

Version **1.0.0** · Kaizen Analytix LLC.

## Skills

| Skill | What it does |
|---|---|
| [support-plan](skills/support-plan/README.md) | Drafts the Support Plan (component of D29) — post-go-live support, SLAs, escalation, and hypercare. |
| [project-signoff](skills/project-signoff/README.md) | Prepares the Project Sign-Off (D30) for formal client acceptance of the delivered solution. |
| [case-study](skills/case-study/README.md) | Creates the branded Kaizen Case Study (D32) from the full engagement record. |
| [closeout-archive](skills/closeout-archive/README.md) | Generates the Project Closeout (D31) and archives all deliverables (T40) — the final PDP skill. |

## Typical flow

`support-plan` (D29) → `project-signoff` (D30) → `case-study` (D32) →
`closeout-archive` (D31 + T40).

All four skills read the engagement record via the shared `read_phase_docs` MCP tool, write
their deliverable to `6. Deploy` via `write_deliverable`, and follow the shared guardrails
(**G1–G5**) defined in the `guardrails` skill of shared-foundation-plugin.
