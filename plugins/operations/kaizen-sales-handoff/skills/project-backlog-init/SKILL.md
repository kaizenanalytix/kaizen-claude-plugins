---
name: project-backlog-init
description: >
  Use this skill when the Engagement Lead (EL) wants to create an initial project backlog at the
  epic level for a Kaizen PDP engagement.
  Trigger on: "set up backlog", "create project backlog", "generate epics", "build epic backlog",
  "project backlog setup", "plan the backlog", "create epics in Jira", "epic planning",
  "initial backlog setup", "set up project epics".
  This skill reads the SOW/scope from "0. Sales Alignment" and the KT Brief from
  "1. Sales Handoff & Transition", derives functional epic groupings specific to the solution,
  generates an Excel file for EL review, and ONLY pushes to Jira after explicit EL approval.
  Never push without approval.
  Prerequisite: sales-handoff-brief (KT Brief) must have been run and EL-approved.
last_reviewed: 2026-07-07
---

# project-backlog-init Skill

Create an initial project backlog at the **epic level only**. Epics are grouped by functional area
of the solution — not by PDP phase. Generate an Excel workbook for EL review, then push to Jira
only after explicit approval.

---

## Step 0 — Locate Source Documents

Find the project root and confirm source documents exist:

1. SOW or scope documents in `0. Sales Alignment/`
2. KT Brief in `1. Sales Handoff & Transition/`

```bash
find "<PROJECT_ROOT>/0. Sales Alignment/" -type f | sort
find "<PROJECT_ROOT>/1. Sales Handoff & Transition/" -type f -name "*KT*" -o -name "*Brief*" | sort
```

If neither exists, stop and guide the user:
> "To set up the project backlog I need the KT Brief from '1. Sales Handoff & Transition'.
> Please run the sales-handoff-brief skill first."

---

## Step 1 — Extract Scope & Solution Context

**From the SOW (in `0. Sales Alignment/`):**
- Project objectives and business outcomes
- Solution components and deliverables
- Timeline and milestones
- Delivery model (fixed-price / T&M / retainer)

**From the KT Brief (in `1. Sales Handoff & Transition/`):**
- Solution overview and architecture
- Functional scope (what the solution does)
- Data sources and integrations
- Technology stack
- Client stakeholders and their concerns

Combine into a **solution scope summary** that captures what the solution does functionally — this
drives the epic groupings.

---

## Step 2 — Derive Functional Epics

### 2.1 Grouping Principle

Epics must be grouped by **function of work**, not by PDP phase or timeline. Each epic represents
a distinct functional area of the solution being delivered.

**How to identify functional groupings:**
- Read the solution components from the SOW and KT Brief
- Identify distinct functional domains (e.g., data ingestion, transformation, reporting, access control)
- Each epic should represent a cohesive body of work that a sub-team could own
- Epics should be mutually exclusive — no overlapping scope between epics
- Every deliverable in the SOW must map to exactly one epic

### 2.2 Epic Structure

For each epic, define:

| Field | Description |
|---|---|
| **Epic Name** | Short, descriptive name of the functional area |
| **Epic Key** | Abbreviated identifier (e.g., `DATA-ING`, `RPT`, `INFRA`) |
| **Summary** | One-line description of what this epic covers |
| **Scope** | Bullet list of the specific deliverables and work included |
| **SOW Mapping** | Which SOW deliverables / line items this epic addresses |
| **Acceptance Criteria** | High-level conditions that define "done" for this epic |
| **Priority** | Highest / High / Medium / Low — based on dependency order and business value |
| **Estimated Duration** | Rough duration in sprints (not story points — this is epic level) |

### 2.3 Mandatory Epics

In addition to solution-specific epics, always include these two cross-cutting epics:

1. **Project Governance** — Status reporting, RAID log, RACI, steering committee, change requests.
   Present on every engagement.
2. **Environment & Infrastructure** — Environment provisioning, access management, CI/CD setup,
   deployment pipelines. Present on every engagement.

### 2.4 Example (for illustration only — always derive from actual scope)

For a data analytics platform engagement, functional epics might be:

| # | Epic Name | Summary |
|---|---|---|
| 1 | Data Ingestion | Source system connectivity, extraction, and landing zone |
| 2 | Data Transformation | Cleansing, business rules, dimensional modelling |
| 3 | Reporting & Dashboards | BI layer, dashboards, self-service analytics |
| 4 | Data Quality & Governance | Validation rules, lineage, cataloguing |
| 5 | Environment & Infrastructure | Cloud infra, CI/CD, access management |
| 6 | Project Governance | Status reporting, RAID, RACI, steering |

The actual epics for a given engagement will differ based on the solution. A CRM migration will
have different epics than a data platform. Always derive from the SOW and KT Brief.

---

## Step 3 — Generate Epic Backlog Excel

Generate an Excel workbook (`.xlsx`) with the proposed epic backlog. Save it to `2. Plan/`.

### 3.1 Workbook Structure

**Sheet 1: "Epic Backlog"**

| Column | Content |
|---|---|
| A — Epic # | Sequential number |
| B — Epic Name | Functional area name |
| C — Epic Key | Short identifier |
| D — Summary | One-line description |
| E — Scope | Deliverables included (semicolon-separated) |
| F — SOW Mapping | SOW references this epic addresses |
| G — Acceptance Criteria | High-level done conditions |
| H — Priority | Highest / High / Medium / Low |
| I — Est. Duration (Sprints) | Rough sprint estimate |
| J — Dependencies | Other epic keys this depends on |

**Sheet 2: "Project Setup"**

| Field | Value |
|---|---|
| Project Name | `<CLIENT>.<YEAR>.<Solution>` |
| Project Key | Abbreviated key |
| Board Type | Scrum or Kanban (from delivery model) |
| Sprint Length | 2 weeks (default) |
| Total Epics | Count |

### 3.2 Generation

```python
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

wb = openpyxl.Workbook()

# --- Sheet 1: Epic Backlog ---
ws_epics = wb.active
ws_epics.title = "Epic Backlog"

headers = [
    "Epic #", "Epic Name", "Epic Key", "Summary", "Scope",
    "SOW Mapping", "Acceptance Criteria", "Priority",
    "Est. Duration (Sprints)", "Dependencies"
]

header_font = Font(bold=True, color="FFFFFF")
header_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")

for col, header in enumerate(headers, 1):
    cell = ws_epics.cell(row=1, column=col, value=header)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = Alignment(horizontal="center", wrap_text=True)

for i, epic in enumerate(epics_data, 2):
    ws_epics.cell(row=i, column=1, value=epic["number"])
    ws_epics.cell(row=i, column=2, value=epic["name"])
    ws_epics.cell(row=i, column=3, value=epic["key"])
    ws_epics.cell(row=i, column=4, value=epic["summary"])
    ws_epics.cell(row=i, column=5, value=epic["scope"])
    ws_epics.cell(row=i, column=6, value=epic["sow_mapping"])
    ws_epics.cell(row=i, column=7, value=epic["acceptance_criteria"])
    ws_epics.cell(row=i, column=8, value=epic["priority"])
    ws_epics.cell(row=i, column=9, value=epic["duration_sprints"])
    ws_epics.cell(row=i, column=10, value=epic["dependencies"])

for col in ws_epics.columns:
    max_len = max(len(str(cell.value or "")) for cell in col)
    ws_epics.column_dimensions[col[0].column_letter].width = min(max_len + 4, 50)

# --- Sheet 2: Project Setup ---
ws_setup = wb.create_sheet("Project Setup")
setup_fields = [
    ("Project Name", project_name),
    ("Project Key", project_key),
    ("Board Type", board_type),
    ("Sprint Length", sprint_length),
    ("Total Epics", len(epics_data)),
]
for i, (field, value) in enumerate(setup_fields, 1):
    ws_setup.cell(row=i, column=1, value=field).font = Font(bold=True)
    ws_setup.cell(row=i, column=2, value=value)

ws_setup.column_dimensions["A"].width = 20
ws_setup.column_dimensions["B"].width = 40

output_path = "<PROJECT_ROOT>/2. Plan/<PROJECT_KEY>_Epic_Backlog.xlsx"
wb.save(output_path)
```

After saving, present the summary in chat:

```
📋 Epic Backlog Proposal for <PROJECT_NAME>

Saved to: 2. Plan/<PROJECT_KEY>_Epic_Backlog.xlsx

Project: <PROJECT_NAME> | Key: <PROJECT_KEY> | Board: <TYPE> | Sprint: 2 weeks

EPICS (<N> total):
  1. <Epic Name> — <Summary> [Priority] [Est. N sprints]
  2. <Epic Name> — <Summary> [Priority] [Est. N sprints]
  ...

Please review the Excel file and confirm:
  → "approved" / "push to Jira" — to create these epics in Jira
  → "revise" — to request changes before pushing
```

---

## Step 4 — Wait for EL Approval (GATE)

**Do not proceed to Step 5 until the EL explicitly approves.**

Accepted approval phrases:
- "approved"
- "push to Jira"
- "push it"
- "go ahead"
- "looks good"
- "create in Jira"

If the EL requests changes:
1. Update the epic definitions
2. Regenerate the Excel file (overwrite the previous version)
3. Re-present the summary in chat
4. Wait for approval again

If the EL says "cancel" or "stop":
> "Understood — nothing has been pushed to Jira. The Excel file is saved in '2. Plan/' for
> reference. Say 'push to Jira' whenever you're ready."

---

## Step 5 — Push Epics to Jira (Only After Approval)

After explicit approval, use the Atlassian Jira MCP connector to create the backlog.

**Check that the Atlassian MCP connector is available.** If not:
```
Use ToolSearch with query "atlassian jira" to find and load the Jira connector tools.
```

If the connector is unavailable:
> "The Atlassian connector is not available in this session. The Excel backlog is saved in
> '2. Plan/' — you can import it manually or reconnect Atlassian and say 'push to Jira'."

### 5.1 Push Order

1. **Create the Jira project** (if it doesn't already exist)
   - Project name, key, board type from the Project Setup sheet
2. **Create all epics** in priority order
   - Set summary, description (from scope + acceptance criteria), priority, and labels
   - Label each epic with `pdp-backlog` for traceability

### 5.2 Post-Push Confirmation

```
✅ Project backlog created in Jira: <PROJECT_KEY>

Created:
  • Jira project: <PROJECT_NAME> (<PROJECT_KEY>)
  • <N> epics pushed

Epic Summary:
  1. <JIRA_EPIC_KEY> — <Epic Name> [Priority]
  2. <JIRA_EPIC_KEY> — <Epic Name> [Priority]
  ...

Jira project URL: [link if available from API response]

📁 Excel backlog saved at: 2. Plan/<PROJECT_KEY>_Epic_Backlog.xlsx

Suggested next steps:
  → Open Jira and verify the board and epic structure
  → Break down epics into stories when sprint planning begins
  → Run project-kickoff-init if not already done
```

---

## Error Handling

| Situation | Action |
|---|---|
| SOW and KT Brief both missing | Stop; ask user to run sales-handoff-brief first |
| KT Brief missing but SOW available | Proceed with SOW only; warn that epic groupings may be less precise |
| Atlassian connector unavailable | Save Excel only; advise user to connect Atlassian MCP and retry |
| Push fails partway | Report which epics were created and which failed; do not retry automatically |
| EL has not approved | Never push; always wait for explicit approval |
| Board type unclear | Default to Scrum; note the assumption in the proposal |
| openpyxl not installed | Run `pip install openpyxl` and retry |
| Project already exists in Jira | Ask EL whether to add epics to existing project or create new |
