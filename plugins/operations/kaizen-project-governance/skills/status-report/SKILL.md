---
name: status-report
description: >
  Use this skill when the Engagement Lead (EL) or Project Manager (PM) wants to draft the
  weekly or periodic Status Report (D16, Mandatory) for a Kaizen PDP engagement.
  Trigger on: "draft status report", "generate status report", "create status report",
  "weekly status update", "project status report", "status deck", "status PPT",
  "generate the status report", "D16 status report", and on requests to build the status
  report from recent updates like "status report from this week's emails/meeting/MoM".
  This skill reads the project plan and Jira progress data, and can also incorporate recent
  updates from emails, Teams meeting transcripts, Minutes of Meeting, or any PDP document the
  user supplies. It generates a Status Report (.pptx) and saves it to "2. Plan".
---

# status-report Skill

Generate the periodic Status Report (D16, Mandatory) from the project plan and Jira sprint
progress. Output: a branded .pptx saved to `2. Plan`. The same status data feeds the cross-phase
governance scorecard (D37) kept current in `7. Project Governance`.

**The report MUST follow the bundled Kaizen Status Report template**, located at
`template/Kaizen Status Report Template.pptx` (relative to this skill). Do not invent your own
slide structure — copy this template and fill in its regions. The template is a compact,
single-page status dashboard preceded by a title slide, plus a worked SAMPLE slide (slide 3)
you can reference for tone and formatting and then delete from the final file.

The template contains three slides:
1. **Title slide** — "Status Report", reporting date, `[Project Name]`, and a client-logo placeholder.
2. **Status dashboard (the one-pager)** — all status content on a single 16:9 slide (see Step 3 for its regions).
3. **SAMPLE** — a fully filled-in example of the dashboard for reference; delete before delivery.

Dependencies: read_jira_progress (shared MCP tool), read_phase_docs (shared MCP tool),
write_deliverable (shared MCP tool), kaizen-pptx-template skill (for PPTX rendering),
Atlassian/Jira connector (mcp__claude_ai_Atlassian__searchJiraIssuesUsingJql,
mcp__claude_ai_Atlassian__getJiraIssue).

> **Guardrails:** This skill follows the shared guardrails (G1–G5) defined in the `guardrails`
> skill of shared-foundation-plugin. See that skill for version-not-overwrite, confirmation
> gates, verbatim financial data, deterministic finance, and approval gate rules.

---

## Step 0 — Locate the Project Root

Find the folder containing `2. Plan/`.

If no workspace folder is connected, use `mcp__cowork__request_cowork_directory` to request one.
If the project root is ambiguous, ask the user to confirm the path before proceeding.

Extract the `PROJECT_ID` from `.kaizen-project.json` if present, or parse the workspace folder
name. If neither is available, ask the user.

---

## Step 1 — Gather Status Inputs

Collect data from the three baseline sources below. In addition, the report can incorporate
recent narrative updates the user supplies (§1.4) — useful when the week's real story lives in
emails and meetings, not just Jira.

### 1.1 Project Plan
Read the project plan from `2. Plan/`:
```bash
find "<PROJECT_ROOT>/2. Plan/" -type f \( -name "*plan*" -o -name "*schedule*" -o -name "*timeline*" \) | sort
```

Extract:
- Current phase / sprint
- Key milestones and their target dates
- Planned deliverables for this period

### 1.2 Jira Progress
Pull current sprint and backlog status using the Jira connector:

```
Use read_jira_progress("<PROJECT_KEY>") to get:
  - Current sprint name and dates
  - Stories: total, completed, in progress, not started
  - Story points: planned vs completed
  - Blocked items
  - Burndown trend (if available)
```

If the Jira connector is not available, ask the user to provide sprint status verbally:
> "I can't connect to Jira. Please tell me: current sprint, stories completed vs remaining,
> and any blocked items."

### 1.3 RAID Log Updates
Read the RAID Log from `7. Project Governance/` (or wherever it lives, if it exists):
```bash
find "<PROJECT_ROOT>" -iname "*RAID*Log*.xlsx" | sort
```

Extract any open risks, actions, or issues to include in the status report.

### 1.4 Additional Sources (optional — emails, transcripts, MoMs, docs)

If the user wants the report built from recent updates, ingest the source(s) they name. **Read
`references/source-ingestion.md` for the extraction protocol** — especially the scoping rules,
which are strict:

| Source | How it reaches the skill |
|---|---|
| **Outlook emails** | Scoped search only — ask for the Outlook **category/tag** first; if none, ask for a **subject**. Never scan the whole mailbox. |
| **Teams transcripts** | Ask for the **meeting name** first, then search transcripts for that meeting only (or read a transcript file/path the user provides). Never search all transcripts blindly. |
| **Minutes of Meeting (MoM)** | A file the user provides in chat or points to in a PDP folder. |
| **Any other PDP document** | Any file the user points at in the PDP folders. |

Distil each source into the status regions (accomplishments, next priorities, risks, discussion
topics/decisions, milestone slippage). These narrative sources **supplement** Jira and the RAID
Log — they don't override them; surface any conflict rather than silently resolving it. Confirm
the concrete source(s) with the user before extracting so scope stays tight.

---

## Step 2 — Synthesise Status Content

From all gathered data, populate the regions of the template's status dashboard. Each region maps
directly to a box on the one-pager (see Step 3 for placement). Keep entries short and scannable —
these are boxes on a single slide, not full paragraphs.

### 2.1 Project Status (RAG)
- Overall RAG status: **Green** (on track), **Amber** (at risk), **Red** (off track)
- Rendered as the "Project Status:" badge / status dot in the top-right of the dashboard
- Determine RAG based on: milestone adherence, scope changes, blockers, resource availability

### 2.2 Key Accomplishments
- Top 3–4 achievements this period (the template's left column allows ~4 items)
- Deliverables completed or advanced; client sign-offs obtained

### 2.3 Next Sprint: Top Priorities
- The top ~3 "To Do" items planned for the next sprint / period
- Key activities and deliverables expected next

### 2.4 Project Risks
- Top ~3 open risks, issues, or blockers (with mitigation status where space allows)
- Items requiring escalation; new items added since last report

### 2.5 Discussion Topics
- ~2 topics to raise with the client or leadership, including **decisions needed**
- For each decision, note the deadline and impact level (e.g. "Impact: High/Medium/Low"), as in
  the SAMPLE slide
- Note: discussion topics often warrant additional pages appended after the dashboard for deeper
  discussion — add extra slides as needed

### 2.6 Timeline: Upcoming Milestones
Populate the milestone table at the bottom of the dashboard. Columns (exactly as in the template):

| Column | Content |
|---|---|
| Milestone | Milestone / deliverable name |
| Status | RAG status dot (Green / Amber / Red) |
| Target Date | Originally planned date |
| FCST Date | Current forecast date |
| Comments | Slippage reason or notes (e.g. "Delayed by 1 week due to XYZ") |

Per G4 (Deterministic Finance): do NOT include budget burn, cost tracking, or financial
metrics. Status reports cover delivery progress only. If the EL needs financial status, refer
them to the P3 economics document.

---

## Step 3 — Map Content to the Template

Do NOT design a new deck. Copy the bundled `template/Kaizen Status Report Template.pptx` and fill
in its placeholders. The template's slides and regions map to the Step 2 content as follows.

### Slide 1 — Title Slide
| Placeholder | Fill with |
|---|---|
| "Status Report" | Keep as-is |
| "Month XX, 2022" | Reporting date (e.g. this report's date) |
| "[Project Name]" | Project name |
| "Insert client logo here" | Client logo image, or remove the placeholder |

### Slide 2 — Status Dashboard (the one-pager)
All status content lives on this single slide. Fill each region:

| Region (template label) | Position | Fill with |
|---|---|---|
| "[Project Name] Status Report" (title) | Top | Project name + "Status Report" |
| Date textbox | Top, under title | Reporting date |
| "Project Status:" + status dot | Top-right | Overall RAG (§2.1) — colour the dot Green/Amber/Red |
| "Key Accomplishments" | Upper-left | ~4 accomplishments (§2.2) |
| "Next Sprint: Top Priorities" | Upper-right | ~3 To-Do items (§2.3) |
| "Project Risks" | Mid-left | ~3 risks/issues (§2.4) |
| "Discussion Topics" | Mid-right | ~2 topics incl. decisions needed w/ impact (§2.5) |
| "Timeline: Upcoming Milestones" table | Bottom | Milestone rows (§2.6) with per-row status dots |

### Additional Discussion Pages (optional)
The template notes that discussion items "often have additional pages as needed for deeper
discussion." Append extra slides after the dashboard when a topic (e.g. a data-needs breakdown or
a timeline chart) warrants its own page.

### RAG Status Formatting
Use the template's oval/badge shapes. Colour by status:
- **Green:** on track
- **Amber:** at risk, mitigation in progress
- **Red:** off track, escalation needed

Apply the same colour scheme to the per-row status dots in the milestone table (the `Oval` shapes
in the Status column).

---

## Step 4 — Build the Deck

Build from the bundled template, not from scratch:

1. Copy `template/Kaizen Status Report Template.pptx` to your working directory.
2. Unpack it (it is already Kaizen-branded — no need to re-apply the kaizen-pptx-template theme).
3. Edit the slide XML directly (not the python-pptx DOM): replace each placeholder string with the
   synthesised content, following the region map in Step 3.
4. Fill the milestone table rows as raw OOXML; set each Status-column oval's fill to the correct
   RAG colour.
5. Duplicate the SAMPLE slide's formatting for any additional discussion pages, then **delete the
   SAMPLE slide** before delivery.
6. Repack and QA (open the file, confirm every placeholder is replaced and no "[Project Name]",
   "To Do #", "Accomplishment #", "Risk #", or "SAMPLE" text remains).

If the bundled template file is missing, fall back to the kaizen-pptx-template skill and rebuild
the layout described in Step 3. See the project-kickoff-init skill (Step 3) for the detailed
XML-edit build sequence.

---

## Step 5 — Save the Output

Present the proposed file to the user (per guardrail G2):
```
Proposed file:
  <PROJECT_ROOT>/2. Plan/<PROJECT_ID> - Status Report [YYYY-MM-DD].pptx

Reply "save" to write this file, or "revise" to make changes.
```

Note: Status reports are periodic, so include the date in the filename. Each report is a new
file, not a version of the previous one.

Check for existing files with the same date (per guardrail G1).

After saving, present the file using `mcp__cowork__present_files`.

---

## Step 6 — Summary in Chat

```
✅ Status Report generated: 2. Plan/<PROJECT_ID> - Status Report [YYYY-MM-DD].pptx

Report summary:
  • Overall RAG: [Green/Amber/Red]
  • Reporting date: [YYYY-MM-DD]
  • Key accomplishments: N
  • Next-sprint priorities: N
  • Open risks: N
  • Discussion topics / decisions needed: N
  • Upcoming milestones: N

Slides produced:
  1. Title Slide
  2. Status Dashboard (RAG, Accomplishments, Top Priorities, Risks,
     Discussion Topics, Upcoming Milestones)
  [+ N additional discussion pages, if any]

Suggested next: Share the status report with stakeholders. Say "what's next" to check your
PDP phase status.
```

---

## Error Handling

| Situation | Action |
|---|---|
| No project plan found | Generate report from Jira data only; note missing plan |
| Jira connector not available | Ask user for sprint status verbally; proceed with manual data |
| No RAID Log found | Omit risks slide or ask user for current risks |
| User asks to search email with no category | Ask for the Outlook category/tag; if none, ask for a subject. Never scan the whole mailbox |
| User asks to pull a transcript with no meeting name | Ask for the meeting name first; never search all transcripts blindly |
| Email/transcript connector not authorized | Say so; fall back to a user-supplied file/pasted text |
| Narrative source conflicts with Jira/RAID | Surface the discrepancy in the report or flag it; don't silently pick one |
| Project root ambiguous | Ask user to confirm path |
| Bundled template file missing | Fall back to kaizen-pptx-template skill; rebuild Step 3 layout |
| kaizen-pptx-template skill not available | Fall back to generic pptx skill |
| RAG status unclear | Default to Amber; ask user to confirm |

---

_Last reviewed: 2026-07-13_
