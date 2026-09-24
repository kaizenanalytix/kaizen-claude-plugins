---
name: sprint-review
description: >
  Use this skill when the PM wants to generate a Sprint Review or Monthly Kaizen Project
  Review deck (T32 sprint review, Mandatory; T33 monthly review, Mandatory) for a Kaizen
  PDP engagement.
  Trigger on: "generate sprint review", "sprint review deck", "monthly review",
  "monthly project review", "create sprint review", "Kaizen project review",
  "sprint review presentation", "T32 sprint review", "T33 monthly review".
  This skill reads Jira sprint data, generates a Sprint / Monthly Review presentation (.pptx),
  and saves it to "5. Develop".
---

# sprint-review Skill

Generate a Sprint Review or Monthly Kaizen Project Review deck (T32/T33, both Mandatory) from
Jira sprint data. Output: a branded .pptx saved to `5. Develop`. This review cycle also produces
and maintains the Sprint Log (D25, Mandatory) — the running record that the team has adhered to
sprint discipline.

Dependencies: read_jira_sprint (shared MCP tool), read_jira_progress (shared MCP tool),
write_deliverable (shared MCP tool), kaizen-pptx-template skill (for PPTX rendering),
Atlassian/Jira connector (mcp__claude_ai_Atlassian__searchJiraIssuesUsingJql).

> **Guardrails:** This skill follows the shared guardrails (G1–G5) defined in the `guardrails`
> skill of shared-foundation-plugin. See that skill for version-not-overwrite, confirmation
> gates, verbatim financial data, deterministic finance, and approval gate rules.

---

## Step 0 — Locate the Project Root and Determine Review Type

Find the folder containing `5. Develop/`.

Ask the user (or infer from trigger phrase):
> "Is this a Sprint Review (T32) or a Monthly Kaizen Project Review (T33)?
> Reply 'sprint' or 'monthly'."

Extract the `PROJECT_ID`.

---

## Step 1 — Gather Sprint / Review Data

### 1.1 From Jira
```
Use read_jira_sprint("<PROJECT_KEY>") to get:
  - Sprint name, start date, end date
  - Sprint goal
  - Stories: completed, in progress, not started, removed
  - Story points: committed vs completed
  - Velocity (current sprint vs average)
  - Burndown data (if available)
  - Blocked items with blockers
  - Carry-over from previous sprint
```

For monthly reviews, pull data across the last 4–5 sprints (or the past month).

If Jira is not available, ask the user for sprint data verbally.

### 1.2 From Project Folder
Read the RAID Log and previous status reports for context:
```bash
find "<PROJECT_ROOT>/1. Sales Handoff & Transition/" -name "*RAID*" | sort
find "<PROJECT_ROOT>/2. Plan/" -name "*Status*" | sort
```

---

## Step 2 — Synthesise Review Content

### For Sprint Review (T32):

#### 2.1 Sprint Summary
- Sprint name, dates, sprint goal
- Goal achievement: Met / Partially Met / Not Met

#### 2.2 What Was Delivered
- Completed stories (grouped by epic or functional area)
- Demos / features ready to show
- Deliverables produced

#### 2.3 Sprint Metrics
- Story points: committed vs completed
- Velocity comparison (this sprint vs rolling average)
- Carry-over items (stories not completed)
- Defects found and fixed

#### 2.4 Blockers & Issues Encountered
- Items that blocked progress
- How they were resolved (or escalation needed)

#### 2.5 Retrospective Highlights
- What went well
- What to improve
- Action items from retro

#### 2.6 Next Sprint Plan
- Sprint goal
- Key stories planned
- Dependencies and risks

### For Monthly Review (T33):

Include everything above aggregated across the month, plus:

#### 2.7 Monthly Progress Overview
- Sprints completed this month
- Cumulative velocity trend
- Milestone tracker (planned vs actual dates)
- PDP phase progress

#### 2.8 Quality Metrics
- Defects opened vs closed (trend)
- Test coverage (if tracked)
- Code review turnaround

#### 2.9 Team & Resource Update
- Team changes (if any)
- Capacity utilisation

Per G4 (Deterministic Finance): exclude budget burn, cost metrics, or financial projections.

---

## Step 3 — Map Content to Slides

### Sprint Review Slides

| Slide | Title | Content | Recommended Layout |
|---|---|---|---|
| 1 | Title Slide | Project name, "Sprint [N] Review", dates | `0_Title Slide` (slideLayout1) |
| 2 | Sprint Summary | Sprint goal, RAG, one-line outcome | `6_Title, Subtitle, and Content` (slideLayout14) |
| 3 | What We Delivered | Completed stories grouped by epic | `6_Title, Subtitle, and Content` (slideLayout14) |
| 4 | Sprint Metrics | Velocity table, committed vs completed | `3_Title Only + Blank Space` (slideLayout8) |
| 5 | Blockers & Issues | Issues table with resolution status | `3_Title Only + Blank Space` (slideLayout8) |
| 6 | Next Sprint Plan | Planned stories and sprint goal | `6_Title, Subtitle, and Content` (slideLayout14) |

### Monthly Review Slides (additional)

| Slide | Title | Content | Recommended Layout |
|---|---|---|---|
| 7 | Monthly Progress | Cumulative metrics, milestone tracker | `3_Title Only + Blank Space` (slideLayout8) |
| 8 | Quality Metrics | Defect trend, test coverage | `3_Title Only + Blank Space` (slideLayout8) |
| 9 | Risks & Actions | Open RAID items | `3_Title Only + Blank Space` (slideLayout8) |

---

## Step 4 — Build the Deck

Invoke the kaizen-pptx-template skill and follow its PPTX build workflow.

---

## Step 5 — Save the Output

Present the proposed file to the user (per guardrail G2):
```
Proposed file:
  <PROJECT_ROOT>/5. Develop/<PROJECT_ID> - Sprint [N] Review.pptx
  or
  <PROJECT_ROOT>/5. Develop/<PROJECT_ID> - Monthly Review [YYYY-MM].pptx

Reply "save" to write this file, or "revise" to make changes.
```

Check for existing files (per guardrail G1).

After saving, present the file using `mcp__cowork__present_files`.

---

## Step 6 — Summary in Chat

```
✅ [Sprint/Monthly] Review generated: 5. Develop/<PROJECT_ID> - [filename].pptx

Review summary:
  • Sprint: [Sprint Name] ([Start] – [End])
  • Goal: [Met / Partially Met / Not Met]
  • Velocity: N committed / N completed story points
  • Carry-over: N stories
  • Blockers: N (N resolved, N open)

Slides produced (N):
  [list slides]

Suggested next: Present the review to stakeholders. Say "what's next" to check your
PDP phase status.
```

---

## Error Handling

| Situation | Action |
|---|---|
| Jira connector not available | Ask user for sprint data verbally; generate from manual input |
| No sprint data found | Ask user which sprint to review; provide sprint name/dates |
| RAID Log not found | Omit risks slide for sprint review; required for monthly |
| kaizen-pptx-template skill not available | Fall back to generic pptx skill |
| Project root ambiguous | Ask user to confirm path |
| Review type unclear | Default to sprint review; ask to confirm |

---

_Last reviewed: 2026-07-07_
