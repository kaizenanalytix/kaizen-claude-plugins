# status-report

Drafts the weekly or periodic **Status Report (D16, Mandatory)** for a Kaizen PDP engagement,
pulling from the project plan and live Jira sprint progress — and optionally from recent updates
in emails, Teams meeting transcripts, Minutes of Meeting, or any PDP document — then rendering a
branded `.pptx` saved to `2. Plan`. The same status data feeds the cross-phase governance
scorecard (D37) kept current in `7. Project Governance`.

## When to use it

For the Engagement Lead (EL) or Project Manager (PM) producing a periodic status update.
Trigger phrases include:

- "draft status report", "generate status report", "create status report"
- "weekly status update", "project status report"
- "status deck", "status PPT"
- "generate the status report", "D16 status report"

## Layout

```
status-report/
├── SKILL.md                                    # Full workflow the model follows (start here)
├── README.md                                   # This file
├── references/
│   └── source-ingestion.md                     # How to ingest emails/transcripts/MoMs/docs
└── template/
    └── Kaizen Status Report Template.pptx      # Bundled, pre-branded status template
```

The report **must** follow the bundled template — do not invent a slide structure. The template
holds three slides: a title slide, a single-page status dashboard (the one-pager), and a worked
SAMPLE slide (slide 3) for reference that is deleted before delivery.

## The status dashboard

All status content lives on one 16:9 slide, synthesised from the plan, Jira, RAID log, and any
supplied narrative sources into these regions:

| Region | Content |
|---|---|
| Project Status (RAG) | Overall Green / Amber / Red badge and status dot |
| Key Accomplishments | ~4 achievements this period |
| Next Sprint: Top Priorities | ~3 upcoming To-Do items |
| Project Risks | ~3 open risks / issues / blockers |
| Discussion Topics | ~2 topics incl. decisions needed with impact level |
| Timeline: Upcoming Milestones | Milestone table (Milestone, Status, Target Date, FCST Date, Comments) |

Per guardrail G4, status reports cover delivery progress only — no budget burn, cost tracking,
or financial metrics (refer financial status to the P3 economics document).

## Inputs and integrations

- **Project plan** — read from `2. Plan/` for phase, milestones, and planned deliverables.
- **Jira** — current sprint and backlog via the Atlassian/Jira connector
  (`mcp__claude_ai_Atlassian__searchJiraIssuesUsingJql`,
  `mcp__claude_ai_Atlassian__getJiraIssue`) and the shared `read_jira_progress` tool. If Jira is
  unavailable, the skill asks the user for sprint status verbally.
- **RAID Log** — read from `7. Project Governance/` for open risks, actions, and issues.
- **Narrative sources (optional)** — recent updates from Outlook emails, Teams meeting
  transcripts, MoMs, or any PDP document. Scoped ingestion only: email search asks for an Outlook
  category/tag (subject fallback) and transcript search asks for the meeting name first — never a
  whole-mailbox or all-transcripts scan. These supplement Jira and the RAID Log rather than
  overriding them. See `references/source-ingestion.md`.
- **Governance scorecard (D37)** — the same status data feeds the cross-phase governance
  scorecard in `7. Project Governance`.

Shared dependencies: `read_jira_progress`, `read_phase_docs`, `write_deliverable`, and the
`kaizen-pptx-template` skill for PPTX rendering.

## Guardrails

Follows the shared guardrails (G1–G5) defined in the `guardrails` skill of
shared-foundation-plugin: version-not-overwrite, confirmation gates, verbatim financial data,
deterministic finance, and approval gate rules. Reports are periodic — each report is a new
dated file, not a version of the previous one.

## See also

- `SKILL.md` — the full step-by-step workflow, region map, and error handling.
