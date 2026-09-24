# sprint-review

Generates a Sprint Review (T32) or Monthly Kaizen Project Review (T33) deck for a Kaizen PDP
engagement — reading Jira sprint data, synthesising the review content, and producing a branded
`.pptx` saved to `5. Develop`. Both deliverables are Mandatory. The review cycle also produces and
maintains the Sprint Log (D25, Mandatory).

## When to use it

Use this skill when a PM wants to generate a sprint or monthly project review deck. Trigger phrases:

- "generate sprint review", "create sprint review", "sprint review deck", "sprint review presentation"
- "monthly review", "monthly project review", "Kaizen project review"
- "T32 sprint review", "T33 monthly review"

Step 0 asks (or infers from the trigger) whether the run is a **Sprint Review (T32)** or a
**Monthly Kaizen Project Review (T33)**. Monthly reviews aggregate the last 4–5 sprints and add
progress, quality, and team/resource slides.

## What it produces

- Sprint Review deck (6 slides): summary, what we delivered, metrics, blockers, next sprint plan.
- Monthly Review deck (adds slides for monthly progress, quality metrics, and open RAID/actions).
- Output saved as `5. Develop/<PROJECT_ID> - Sprint [N] Review.pptx` or
  `5. Develop/<PROJECT_ID> - Monthly Review [YYYY-MM].pptx`.

## Integrations and dependencies

- **Jira** via the Atlassian connector (`mcp__claude_ai_Atlassian__searchJiraIssuesUsingJql`) and
  the shared `read_jira_sprint` / `read_jira_progress` MCP tools for sprint, velocity, burndown,
  and blocker data. If Jira is unavailable, the skill collects sprint data from the user verbally.
- **`write_deliverable`** (shared MCP tool) for writing the output file.
- **`kaizen-pptx-template`** skill for PPTX rendering (falls back to a generic pptx skill if absent).
- Reads the RAID Log and prior status reports from the project folder for context.

## Guardrails

Follows the shared guardrails (G1–G5) from the `guardrails` skill of shared-foundation-plugin:
version-not-overwrite, confirmation gates before saving, verbatim financial data, deterministic
finance (G4 — budget burn, cost metrics, and financial projections are excluded from reviews), and
approval gates.

## See also

- `SKILL.md` — the full step-by-step workflow, slide mapping, and error handling.
- `../../README.md` — the PDP Delivery plugin overview.
