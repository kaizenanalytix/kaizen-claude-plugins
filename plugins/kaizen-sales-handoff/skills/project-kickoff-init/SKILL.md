---
name: project-kickoff-init
description: >
  Use this skill when the Engagement Lead (EL) wants to initialise the project kickoff package
  for a Kaizen PDP engagement — the kickoff deck, requirements review, project plan, project
  charter, and technical checklist in one pass.
  Trigger on: "project kickoff", "kickoff init", "initialise kickoff", "generate kickoff package",
  "kickoff deck", "create kickoff", "project kickoff init", "kickoff setup",
  "generate kickoff PPT", "create kickoff deck", "internal kickoff", "project setup",
  "project charter", "fill the charter", "generate charter".
  This skill reads the Phase 0 client documents from "0. Sales Alignment" and KT Brief from
  "1. Sales Handoff & Transition", then produces five deliverables:
    1. Internal Kickoff PPT (branded deck)
    2. Requirements Document (critical review with gap analysis)
    3. Project Plan Excel (Kaizen Gantt template populated from the delivery context)
    4. Project Charter (D12, the Kaizen charter template populated section-by-section)
    5. Technical Checklist Excel (D13, technical readiness items)
  Deliverables 1, 2, 3 are saved to "2. Plan/". The Project Charter (D12) and Technical Checklist
  (D13) are saved to "1. Sales Handoff & Transition/", their PDP home. Deliverables 3 and 4 are
  produced by populating the bundled templates in templates/, NOT by generating from scratch.
  Prerequisite: sales-handoff-brief (KT Brief) must have been run and EL-approved.
last_reviewed: 2026-07-14
---

# project-kickoff-init Skill

Initialise the full project kickoff package in one pass. Reads Phase 0 sales documents and the
KT Brief, synthesises the delivery context, and produces five deliverables:

| # | Deliverable | Format | Built by | Saved to |
|---|---|---|---|---|
| 1 | Internal Kickoff Deck | .pptx | kaizen-pptx-template | `2. Plan/` |
| 2 | Requirements Document | .docx | Generated from scratch | `2. Plan/` |
| 3 | Project Plan | .xlsx | **Populating the bundled Kaizen Gantt template** | `2. Plan/` |
| 4 | Project Charter (D12) | .docx | **Populating the bundled charter template** | `1. Sales Handoff & Transition/` |
| 5 | Technical Checklist (D13) | .xlsx | Generated from scratch | `1. Sales Handoff & Transition/` |

### Bundled templates

Two deliverables are produced by filling ready-made Kaizen templates that ship with this skill —
never regenerate their structure from scratch, only populate the cells/fields:

```
project-kickoff-init/templates/
├── Kaizen_Project_Plan_Template.xlsx   # Deliverable 3 — Gantt (Architecture / ResourceList / Status)
└── Project_Charter_Template.docx       # Deliverable 4 — sectioned charter (Project Detail … Sign-off)
```

Always copy the template to `/tmp/` first, populate the copy, then save the populated file to the
destination folder. Never edit the template in place.

**IMPORTANT — No Economics:** No deliverable may include TCV, hourly rates, investment breakdowns,
commercial model details, GM percentages, or billing terms. If economic data appears in source
documents, skip it entirely. The charter's budget/financing wording is satisfied with a
non-commercial statement (e.g., "Resourcing per approved SOW") or left as `[TO BE CONFIRMED]` —
never insert figures.

---

## Step 0 — Locate the Project Root

Find the folder containing `0. Sales Alignment/` and `1. Sales Handoff & Transition/`.

If no workspace folder is connected, use `mcp__cowork__request_cowork_directory` to request one.
If the project root is ambiguous, ask the user to confirm the path.

Extract `PROJECT_ID` by parsing the workspace folder name
(`[Client Familiar Name] [Timing] [Project Name]` convention). If the name does not follow the convention, ask
the user for the project identifier.

---

## Step 1 — Inventory & Extract Source Documents

### 1.1 Inventory

List all files in both source folders:

```bash
find "<PROJECT_ROOT>/0. Sales Alignment/" -type f | sort
find "<PROJECT_ROOT>/1. Sales Handoff & Transition/" -type f | sort
```

Classify each file:

| Filename keyword | Document type |
|---|---|
| SOW, statement-of-work | Statement of Work (D10) |
| proposal, client-proposal | Client Proposal (D7) |
| solution-overview, solution_overview | Solution Overview Diagram (D4) |
| NDA, non-disclosure | NDA (D1) |
| opportunity, ask, problem-statement | Opportunity summary (D2) |
| MSA, master-service | MSA (D9) |
| data-request, data_request | Data Request Document (D8) |
| scope, estimation, estimate | Project Scope & Estimation Summary (D3) |
| review-committee, DRC | Deal Review Committee Submission (D6) |
| KT, Brief | KT Brief (from sales-handoff-brief skill) |

> P3 Project Economics (D5) files must be ignored.

If both folders are empty, stop:
> "The source folders are empty. Please add Phase 0 documents to '0. Sales Alignment' and run
> the sales-handoff-brief skill first."

### 1.2 Extraction Strategy (two-tier)

**Tier 1 — Read tool for native formats:** `.md`, `.txt`, `.pdf`

**Tier 2 — For binary formats (.docx, .pptx, .xlsx):**

Copy files to `/tmp/` first (forces OneDrive download for cloud-only stubs):

```bash
pip install python-docx python-pptx openpyxl --break-system-packages -q
cp "<workspace_mount_path>/1. Sales Handoff & Transition/<filename>" /tmp/<filename>
```

Then extract with python-docx / python-pptx / openpyxl from the `/tmp/` copy.

### 1.3 Detecting Cloud-Only Failures

If `cp` succeeds but extraction returns empty or throws `BadZipFile` / `PackageNotFoundError`:
1. Note the file as unreadable in the extraction log
2. Continue with other documents
3. In the final summary, include:
   > "Could not read [filename] — it appears to be a cloud-only file on OneDrive.
   > Please right-click the file in Explorer -> 'Always keep on this device', then re-run."

Do NOT silently skip files.

Label each extracted block: `[SOW]`, `[PROPOSAL]`, `[KT_BRIEF]`, `[SCOPE]`, etc.

---

## Step 2 — Synthesise the Delivery Context

From all extracted content, build a unified delivery context. This single synthesis feeds all
five deliverables. Mark any missing field as `[TO BE CONFIRMED — field name]`.

### 2.1 Project Summary
Client Name, Project Name, Project Code, Proposed Start Date, Proposed End Date, Total Duration.

### 2.2 Scope, Objectives & Deliverables
- Project Objectives (3–5 bullets — business outcomes)
- In-Scope items (from SOW)
- Out-of-Scope items (explicit exclusions)
- Key Deliverables (numbered list with descriptions)
- Success / Acceptance Criteria

### 2.3 Proposed Solution — What We Are Building
- Solution Summary (3–5 plain-English sentences, end-to-end)
- Key Technologies & Tools (every technology: languages, platforms, cloud, databases, frameworks)
- Data Sources & Integrations (feeds, systems, volumes)
- Architecture Principles / Constraints
- Data Requirements (what we need from client, delivery dates, access, sensitivity)

### 2.4 Project Plan — Timeline, Phases & Deadlines
- Phases / Sprints with specific date ranges
- Per phase: name, week range, key activities, deliverables produced
- Key Milestones with target dates
- Overall cadence: sprint length, total sprints, total duration
- Build a phase table:

| Phase / Sprint | Weeks | Key Activities | Deliverables | Milestone & Date |
|---|---|---|---|---|
| Kickoff & Discovery | W1–2 | Requirements, data ingestion, env setup | Data model doc, requirements | Kickoff: [Date] |
| Sprint 1 | W3–4 | Core build, initial model | Working prototype | Data Sign-Off: [Date] |
| ... | ... | ... | ... | ... |

### 2.5 Project Team & Responsibilities
**Kaizen Delivery Team:** Role, Name, Responsibilities, FTE, Window
**Client Team & Stakeholders:** Role, Name, Title, Commitment Expected

Extract every named person from source docs. List unnamed roles as `[TBD]`.

### 2.6 Agile Approach & Governance
Sprint cadence, meeting cadence table, governance model (RAID, escalation, status reporting).

### 2.7 Risks & Assumptions
All risks, assumptions, dependencies, open questions from sales:

| # | Description | Type | Owner | Mitigation / Status |
|---|---|---|---|---|
| 1 | [Risk] | Risk | [Owner] | [Mitigation] |

### 2.8 Technology Stack & Environment
- Programming languages, frameworks, cloud platforms, databases, BI tools, ML tools, ETL tools
- Development / staging / production environments
- VPN / SSO / network access requirements
- Client infrastructure constraints, approved tool lists, security policies
- Data sensitivity classification (PII, PHI, HIPAA, GDPR, SOC2)

### 2.9 Immediate Next Steps
Concrete actions for the first 2–4 weeks, grouped by timeframe.

---

## Step 3 — Deliverable 1: Internal Kickoff Deck (.pptx)

### 3.1 Slide Map

| Slide | Title | Source | Layout | Format |
|---|---|---|---|---|
| 1 | Title Slide | Project name, client, date | `0_Title Slide` (slideLayout1) | Title + subtitle |
| 2 | Agenda | Topic list | `1_Agenda` (slideLayout5) | Numbered list |
| 3 | Project Overview | 2.1 + 2.2 Objectives | `2_Title, Subtitle, and Blank Space` (slideLayout6) | Bullets |
| 4 | Scope & Deliverables | 2.2 In/Out-of-Scope | `6_Title, Subtitle, and Content` (slideLayout14) | Bullets |
| 5 | Proposed Solution | 2.3 Solution detail | `6_Title, Subtitle, and Content` (slideLayout14) | Paragraph + bullets |
| 6 | Data Requirements | 2.3 Data requirements | `3_Title Only + Blank Space` (slideLayout8) | OOXML table |
| 7 | Project Plan & Timeline | 2.4 Full phased plan | `3_Title Only + Blank Space` (slideLayout8) | OOXML table |
| 8 | Kaizen Delivery Team | 2.5 Kaizen table | `3_Title Only + Blank Space, Grey` (slideLayout9) | OOXML table |
| 9 | Client Team | 2.5 Client table | `3_Title Only + Blank Space` (slideLayout8) | OOXML table |
| 10 | Working Together | 2.6 Agile approach | `6_Title, Subtitle, and Content, Grey` (slideLayout15) | Bullets |
| 11 | Meeting Cadence | 2.6 Meeting table | `3_Title Only + Blank Space` (slideLayout8) | OOXML table |
| 12 | Risks & Assumptions | 2.7 Top items (<=8) | `3_Title Only + Blank Space` (slideLayout8) | OOXML table |
| 13 | Next Steps | 2.9 Immediate actions | `6_Title, Subtitle, and Content` (slideLayout14) | Bullets |

Split any slide with >8 table rows or >10 bullets across two slides (e.g., "Project Plan (1/2)").

### 3.2 Build Process

Invoke the **kaizen-pptx-template** skill and follow its workflow exactly:

1. **Setup** — `pip install python-pptx`, copy template from skill assets
2. **Unpack** — `unpack.py` to extract template XML
3. **Remove example slides** — delete from `<p:sldIdLst>` and slide files
4. **Add slides** — `add_slide.py` per layout from the table above
5. **Add explicit positions** — copy `<a:xfrm>` from layout XML into each placeholder's `<p:spPr>`
6. **Edit content** — Edit tool on raw slide XML (`<a:t>` elements), preserve `<a:rPr>` formatting
7. **Inject tables** — raw `<a:tbl>` OOXML into `<p:graphicFrame>` elements
8. **Clean & repack** — `clean.py` then `pack.py`
9. **QA** — extract text, convert to images, visually inspect every slide

**CRITICAL:** Do NOT use python-pptx placeholder API to edit content — it strips shapes and
produces blank slides. Use raw XML editing only.

### 3.3 Save

```
<PROJECT_ROOT>/2. Plan/<PROJECT_ID> - Internal Kickoff.pptx
```

---

## Step 4 — Deliverable 2: Requirements Document (.docx)

Generate an elaborated requirements document that critically reviews the kickoff deck content,
identifies gaps, and suggests missing approaches or ideas. This is not a rubber-stamp of the
SOW — it is an independent analytical review.

### 4.1 Document Structure

**Section 1: Executive Summary**
- One-paragraph summary of the engagement
- Key findings from this review (2–3 sentences)

**Section 2: Scope Analysis**
- Restate in-scope and out-of-scope items from the SOW
- **Gap Analysis:** Identify scope items that are vague, ambiguous, or missing detail
- **Recommendations:** Suggest clarifications or additions the EL should raise with the client

**Section 3: Solution Review**
- Summarise the proposed solution from the kickoff deck
- **Architectural Gaps:** Are there components implied by the scope but not addressed in the
  solution? (e.g., monitoring, alerting, DR, performance testing)
- **Alternative Approaches:** For each major solution component, briefly note alternative
  technologies or approaches worth considering, with trade-offs
- **Scalability & Performance:** Does the proposed solution account for data growth, concurrency,
  and performance requirements? Flag if not addressed.

**Section 4: Data Requirements Review**
- List all data sources identified
- **Missing Data:** Are there data sources implied by the scope but not listed?
- **Data Quality Risks:** Based on the source types and volumes, what data quality issues should
  the team anticipate?
- **Data Governance:** Are there compliance or privacy requirements not yet addressed?

**Section 5: Timeline & Resource Review**
- Summarise the proposed timeline from the kickoff deck
- **Timeline Risks:** Are any phases unrealistically short given the scope?
- **Resource Gaps:** Are there skill sets required by the solution but not represented in the team?
- **Dependency Risks:** Are there external dependencies (client data, access, approvals) that
  could delay the timeline?

**Section 6: Risk Register Enhancement**
- Include all risks from section 2.7
- **Additional Risks:** Identify risks not captured in the SOW or kickoff deck, derived from
  the solution analysis above
- Categorise: Technical / Data / Resource / Client / Compliance / Timeline

**Section 7: Recommendations Summary**
- Numbered list of all recommendations from sections 2–6
- Each recommendation: description, priority (High / Medium / Low), suggested owner

### 4.2 Generation

```python
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document()

style = doc.styles['Normal']
style.font.name = 'Calibri'
style.font.size = Pt(11)

# Title
title = doc.add_heading(f'{project_name} — Requirements Review', level=0)

# Subtitle
subtitle = doc.add_paragraph()
subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = subtitle.add_run(f'Prepared by Kaizen Analytix | {date}')
run.font.size = Pt(10)
run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

doc.add_page_break()

# Table of Contents placeholder
doc.add_heading('Table of Contents', level=1)
doc.add_paragraph('[Update field after final edits]')
doc.add_page_break()

# Sections 1–7: populate from synthesis + critical analysis
# For each section:
#   doc.add_heading('Section Title', level=1)
#   doc.add_heading('Subsection', level=2)
#   doc.add_paragraph('Content...')
#   For tables: doc.add_table(rows, cols)

output_path = "<PROJECT_ROOT>/2. Plan/<PROJECT_ID> - Requirements Review.docx"
doc.save(output_path)
```

### 4.3 Critical Review Guidelines

When generating sections 3–6, apply these analytical lenses:

- **Completeness:** Does the scope cover all the work implied by the objectives?
- **Feasibility:** Can the proposed solution be delivered within the stated timeline and team?
- **Ambiguity:** Are there terms or deliverables that could be interpreted multiple ways?
- **Missing non-functionals:** Security, performance, monitoring, disaster recovery, training,
  documentation, handoff — are these addressed?
- **Industry best practices:** Based on the solution type (data platform, ML model, CRM migration,
  etc.), are there standard components or approaches that are missing?

Be constructive, not adversarial. Frame gaps as "consider adding" or "recommend clarifying", not
"this is wrong". The goal is to strengthen the delivery plan before work begins.

---

## Step 5 — Deliverable 3: Project Plan (.xlsx) — POPULATE THE TEMPLATE

**Do NOT build a workbook from scratch.** Populate the bundled Kaizen Gantt template:
`templates/Kaizen_Project_Plan_Template.xlsx`. It is a formula-driven Gantt whose week grid and
task bars are computed automatically from the dates you enter — your only job is to fill
workstreams, tasks, dates, statuses and the resource list. The template has three sheets:

- **Architecture** — the Gantt. `H3` is the Project Start Date (it drives the whole week grid).
  There are **nine** pre-built workstream blocks, each = one header row + 20 task rows:

  | Workstream | Header cell (col C) | Task rows |
  |---|---|---|
  | 1 | C5 | 6–25 |
  | 2 | C26 | 27–46 |
  | 3 | C47 | 48–67 |
  | 4 | C68 | 69–88 |
  | 5 | C89 | 90–109 |
  | 6 | C110 | 111–130 |
  | 7 | C131 | 132–151 |
  | 8 | C152 | 153–172 |
  | 9 | C173 | 174–193 |

  Per task row, fill only these columns: **D** = task name, **E** = Status, **F** = Assigned To,
  **G** = Secondary, **H** = Start Date, **I** = End Date. Columns **J onward are the week-grid
  formulas — never write to them, and never touch rows 2–4 or the `D3:D4` / `E3:G3` merges.**
- **ResourceList** — `B` = Organization (Kaizen / Client), `C` = Name, `D` = Role, from row 3 down.
- **Status** — legend of allowed Status values; do not edit. Use exactly one of:
  `On Track`, `Complete`, `On Hold`, `Needs Attn`.

### 5.1 Map the delivery context onto the template

Map from synthesis §2.4 (plan) and §2.5 (team):

- Each functional workstream / phase / sprint → one **workstream block** (rename the col-C header).
  Use as many of the nine blocks as you need; clear the rest.
- Each key activity / task under it → one **task row** (col D), with its Start/End dates (§2.4) and
  owner (§2.5). Default Status to `On Track` unless the context implies otherwise. Keep ≤20 tasks
  per workstream (the block size); split across blocks if a workstream has more.
- Set `H3` to the Proposed Start Date (§2.1). Use real `datetime`/`date` objects for all dates so
  the Gantt grid computes — never date strings.
- Clear every unused placeholder `TASK` row (set col D to `None`) and every unused workstream
  header so the sheet shows no empty rows.

### 5.2 Population script

```python
import shutil, datetime
import openpyxl

SKILL_DIR = "<this skill's folder>"   # .../skills/project-kickoff-init
tpl = f"{SKILL_DIR}/templates/Kaizen_Project_Plan_Template.xlsx"
work = "/tmp/project_plan.xlsx"
shutil.copy(tpl, work)                 # always work on a copy, never the template

wb = openpyxl.load_workbook(work)      # keep formulas (do NOT pass data_only=True)
arch = wb["Architecture"]
res  = wb["ResourceList"]

# Nine workstream blocks: (header_row, first_task_row, last_task_row)
BLOCKS = [(5,6,25),(26,27,46),(47,48,67),(68,69,88),(89,90,109),
          (110,111,130),(131,132,151),(152,153,172),(173,174,193)]
STATUS = {"complete":"Complete","on hold":"On Hold","at risk":"Needs Attn","on track":"On Track"}

# CRITICAL openpyxl gotcha: ws.cell(r, c, value=None) is a NO-OP (it only assigns when
# value is not None), so it will NOT clear a placeholder. To clear a cell you MUST assign
# to .value:
def clear(ws, r, c):
    ws.cell(row=r, column=c).value = None

# Project start date drives the whole week grid
arch["H3"] = start_date                # a datetime.date / datetime.datetime

# workstreams = [{"name": str, "tasks": [ {name, status, owner, secondary, start, end}, ... ]}, ...]
for (hdr, r0, r1), ws in zip(BLOCKS, workstreams):
    arch.cell(row=hdr, column=3, value=ws["name"])          # col C header
    row = r0
    for t in ws["tasks"][: (r1 - r0 + 1)]:
        arch.cell(row=row, column=4, value=t["name"])       # D task
        arch.cell(row=row, column=5, value=STATUS.get(t.get("status","on track").lower(),"On Track"))
        arch.cell(row=row, column=6, value=t.get("owner"))   # F Assigned To
        if t.get("secondary"):
            arch.cell(row=row, column=7, value=t["secondary"])
        arch.cell(row=row, column=8, value=t["start"])       # H Start (date obj)
        arch.cell(row=row, column=9, value=t["end"])         # I End (date obj)
        row += 1
    for empty in range(row, r1 + 1):                         # clear leftover TASK rows
        clear(arch, empty, 4)

# Clear any unused workstream blocks entirely (header + task rows)
for (hdr, r0, r1) in BLOCKS[len(workstreams):]:
    clear(arch, hdr, 3)
    for rr in range(r0, r1 + 1):
        clear(arch, rr, 4)

# ResourceList — team from §2.5 (Kaizen + Client), from row 3
r = 3
for m in team_members:            # [{"org": "Kaizen"|"Client", "name": str, "role": str}, ...]
    res.cell(row=r, column=2, value=m["org"])
    res.cell(row=r, column=3, value=m["name"])
    res.cell(row=r, column=4, value=m["role"])
    r += 1
for rr in range(r, 13):           # clear leftover placeholder resource rows
    clear(res, rr, 2); clear(res, rr, 3); clear(res, rr, 4)

wb.save("<PROJECT_ROOT>/2. Plan/<PROJECT_ID> - Project Plan.xlsx")
```

> **Note on fidelity:** openpyxl preserves the Gantt's conditional-formatting bars and cell
> formulas, but may drop the Status dropdown's extended data-validation on save. That is
> cosmetic — the typed Status values remain valid. Keep edits confined to the cells above; do not
> restructure sheets, rows, or the week grid. Remember `ws.cell(r, c, value=None)` does **not**
> clear — always use the `clear()` helper above.

---

## Step 6 — Deliverable 4: Project Charter (.docx) — POPULATE THE TEMPLATE

**Do NOT build a document from scratch.** Populate the bundled Kaizen charter template:
`templates/Project_Charter_Template.docx`. It is a single sectioned table (`doc.tables[0]`) plus a
second instructions table (`doc.tables[1]`) — **leave the instructions table untouched.** Fill the
data cells of table 0 from the synthesis. The charter (D12) is saved to
`1. Sales Handoff & Transition/`, NOT `2. Plan/`.

### 6.1 Cell map (table 0, 41 rows)

Rows are section headers or data rows. Fill only the data cells below each header:

| Section | Fill target | Source |
|---|---|---|
| 1 Project Detail | R2 → Project Name; R3 → Sponsor | §2.1; Sponsor from SOW/KT (else `[TO BE CONFIRMED]`) |
| 2 Project Team | R6 = Program/Project Manager; R7–R11 = management team | §2.5 Kaizen team. Cols: Name, Department, Activity Area, Role, Telephone/E-mail |
| 3 Key Stakeholders | R13–R15 (one per row) | §2.5 client stakeholders |
| 4 Scope — Purpose | R18 | §2.2 objectives / project purpose |
| 4 — High-level Objectives | R20 | §2.2 objectives |
| 4 — Key Deliverables | R22 | §2.2 key deliverables |
| 4 — Scope (by phase) | R24 (replace the "Phase 1/2/3" template text) | §2.2 in/out-of-scope, §2.4 phases |
| 4 — Project Key Milestones | R26 (replace template text) | §2.4 milestones + dates |
| 4 — Major High-level Risks | R28 | §2.7 (rate High/Med/Low) |
| 4 — Major Constraints | R30 | §2.7 assumptions/constraints |
| 4 — Internal/External Dependencies | R32 | §2.7 dependencies |
| 5 Communication Strategy | R34 | §2.6 meeting/governance cadence |
| 6 Sign-off | R37 = Sponsor (Name & Position); R38 = Project Manager | §2.5; leave Signature/Date blank |
| 7 Comments | R40 | Any EL notes, else leave blank |

Merged cells repeat, so target *unique* underlying cells. For single-column data rows (R13–R15,
R18, R20, R22, R24, R26, R28, R30, R32, R34, R40) write to `row.cells[0]`. For the team and
sign-off rows use the `unique_cells()` helper below and index into it.

### 6.2 Population script

```python
import shutil
from docx import Document

SKILL_DIR = "<this skill's folder>"   # .../skills/project-kickoff-init
tpl = f"{SKILL_DIR}/templates/Project_Charter_Template.docx"
work = "/tmp/project_charter.docx"
shutil.copy(tpl, work)                 # work on a copy, never the template

doc = Document(work)
t = doc.tables[0]                      # section table; doc.tables[1] = instructions (leave alone)

def unique_cells(row):
    out, seen = [], None
    for c in row.cells:
        if c._tc is not seen:
            out.append(c); seen = c._tc
    return out

def set_cell(cell, text):
    p = cell.paragraphs[0]
    for extra in cell.paragraphs[1:]:  # collapse to one paragraph
        extra._element.getparent().remove(extra._element)
    if p.runs:
        p.runs[0].text = text
        for r in p.runs[1:]:
            r.text = ""
    else:
        p.add_run(text)

# --- Section 1: Project Detail (2nd unique cell is the data cell) ---
set_cell(unique_cells(t.rows[2])[1], project_name)
set_cell(unique_cells(t.rows[3])[1], sponsor or "[TO BE CONFIRMED — Sponsor]")

# --- Section 2: Project Team --- cols: [role-label, Name, Department, Activity Area, Role, Tel/Email]
def fill_team_row(row_idx, member):
    u = unique_cells(t.rows[row_idx])          # 6 unique cells
    set_cell(u[1], member.get("name",""))
    set_cell(u[2], member.get("department",""))
    set_cell(u[3], member.get("activity",""))
    set_cell(u[4], member.get("role",""))
    set_cell(u[5], member.get("contact",""))

fill_team_row(6, project_manager)              # R6 "Program/Project Manager:"
for i, m in enumerate(management_team[:5]):     # R7–R11
    fill_team_row(7 + i, m)

# --- Section 3: Key Stakeholders (R13–R15, one merged cell each) ---
for i, s in enumerate(key_stakeholders[:3]):
    set_cell(t.rows[13 + i].cells[0], s)        # e.g. "Name — Title, Organization"

# --- Section 4: Scope Statement (single merged data cells) ---
set_cell(t.rows[18].cells[0], project_purpose)
set_cell(t.rows[20].cells[0], high_level_objectives)   # newline-joined bullets
set_cell(t.rows[22].cells[0], key_deliverables)
set_cell(t.rows[24].cells[0], scope_by_phase)          # replaces "Phase 1/2/3" placeholder text
set_cell(t.rows[26].cells[0], milestones_by_phase)     # replaces placeholder text
set_cell(t.rows[28].cells[0], high_level_risks)        # each: risk — H/M/L
set_cell(t.rows[30].cells[0], constraints)
set_cell(t.rows[32].cells[0], dependencies)

# --- Section 5: Communication Strategy (R34) ---
set_cell(t.rows[34].cells[0], communication_strategy)

# --- Section 6: Sign-off (2nd unique cell = Name & Position; leave signature/date blank) ---
set_cell(unique_cells(t.rows[37])[1], f"{sponsor or '[TO BE CONFIRMED]'} — Sponsor")
set_cell(unique_cells(t.rows[38])[1], f"{pm_name or '[TO BE CONFIRMED]'} — Project Manager")

# --- Section 7: Comments (R40) — optional ---
# set_cell(t.rows[40].cells[0], el_notes)

doc.save("<PROJECT_ROOT>/1. Sales Handoff & Transition/<PROJECT_ID> - Project Charter.docx")
```

> Preserve the template's formatting: only replace cell text via `set_cell`. Do not add/remove
> rows, delete sections, or touch `doc.tables[1]` (the instructions guide). No economic figures —
> the charter has no budget row; keep it that way.

### 6.3 Save

```
<PROJECT_ROOT>/1. Sales Handoff & Transition/<PROJECT_ID> - Project Charter.docx
```

---

## Step 7 — Deliverable 5: Technical Checklist Excel (.xlsx)

Generate the Project Technical Checklist (D13, Mandatory).

### 7.1 Checklist Structure

**Sheet: Technical Checklist**

| Column | Description |
|---|---|
| A — ID | Auto-incrementing (TC-001, TC-002, ...) |
| B — Category | Environment / Access / Data / Security / Tools / Integration / Compliance |
| C — Checklist Item | Specific technical readiness item |
| D — Owner | Person responsible (Kaizen or Client role) |
| E — Status | Not Started / In Progress / Complete / Blocked |
| F — Target Date | Expected completion date |
| G — Notes / Details | Additional context |
| H — Blocker? | Yes / No |

### 7.2 Standard Categories

Pre-populate with items relevant to the project's technology context from section 2.8. Include
ALL applicable items; omit items that clearly do not apply.

**Environment Setup**
- Development environment provisioned and accessible
- Staging / test environment provisioned
- Production environment identified and access path documented
- CI/CD pipeline configured
- Version control repository created
- Branch strategy documented and agreed

**Access & Credentials**
- VPN access granted to all Kaizen team members
- SSO / AD accounts provisioned for Kaizen team
- Database access credentials obtained
- Cloud platform access (console + programmatic) granted
- API keys / tokens obtained for integration endpoints
- Service accounts created for automated processes
- Access documented in secure credentials store

**Data Readiness**
- Data sources identified and documented
- Sample data received and validated
- Data access method confirmed (API / direct query / file drop / replication)
- Data refresh cadence agreed
- Data quality baseline assessed
- Data dictionary / schema documentation obtained
- PII / sensitive data fields identified and handling plan agreed

**Security & Compliance**
- Data classification confirmed (PII / PHI / public / internal)
- Encryption requirements documented (at rest / in transit)
- Access control model agreed (RBAC / ABAC)
- Audit logging requirements confirmed
- Compliance framework requirements noted (HIPAA / GDPR / SOC2)
- Data retention and disposal policy confirmed

**Tools & Licensing**
- All required software licences obtained
- Client-approved tool list confirmed
- Kaizen standard tooling compatible with client environment
- BI / reporting tool access confirmed

**Integration Points**
- All integration endpoints documented (URL, auth method, rate limits)
- API documentation obtained for each integration
- Test / sandbox environments available for integrations

**Project Infrastructure**
- Jira project created and configured (see project-backlog-init skill)
- SharePoint / OneDrive project folder structure created
- Communication channels set up (Teams / Slack)
- Meeting series created (standups, sprint reviews, SteerCo)

### 7.3 Customisation

After generating standard items, add project-specific items based on the technology stack from
section 2.8. Examples:
- Snowflake in scope → "Snowflake warehouse and role provisioned"
- ML models in scope → "Model registry set up", "GPU compute provisioned"
- Alteryx in scope → "Alteryx Server access and licence confirmed"

### 7.4 Save

```
<PROJECT_ROOT>/1. Sales Handoff & Transition/<PROJECT_ID> - Technical Checklist.xlsx
```

---

## Step 8 — Present All Deliverables for Review

After generating all five deliverables, present a unified summary:

```
📦 Project Kickoff Package for <PROJECT_NAME>

Saved to 2. Plan/:

  1. <PROJECT_ID> - Internal Kickoff.pptx
     Slides: N (Title, Agenda, Overview, Scope, Solution, Data, Plan, Teams, Agile, Cadence, Risks, Next Steps)

  2. <PROJECT_ID> - Requirements Review.docx
     Sections: Executive Summary, Scope Analysis, Solution Review, Data Review,
     Timeline & Resource Review, Risk Register, Recommendations
     Recommendations: N total (N High, N Medium, N Low)

  3. <PROJECT_ID> - Project Plan.xlsx   (populated from Kaizen Gantt template)
     Architecture: N workstreams / N tasks · ResourceList: N resources

Saved to 1. Sales Handoff & Transition/:

  4. <PROJECT_ID> - Project Charter.docx   (D12, populated from charter template)
     Sections filled: Project Detail, Team, Stakeholders, Scope Statement,
     Milestones, Risks, Constraints, Dependencies, Communication, Sign-off

  5. <PROJECT_ID> - Technical Checklist.xlsx   (D13)
     Items: N total across N categories
     Blockers: N items flagged

Documents read from Phase 0:
  - [list each file and its identified type]

Placeholders requiring EL input:
  - [list any [TO BE CONFIRMED] fields across all deliverables]

Flags:
  - [list any unreadable cloud-only files]

Please review all five deliverables. Reply with any changes, or say "looks good" to proceed
to backlog setup (project-backlog-init).
```

Present files using `mcp__cowork__present_files` if available.

---

## Error Handling

| Situation | Action |
|---|---|
| Phase 0 folder is empty | Stop; ask user to add Phase 0 documents and run sales-handoff-brief |
| No SOW found | Build deliverables with `[TO BE CONFIRMED]` placeholders on scope items |
| KT Brief missing but SOW available | Proceed with SOW only; warn that synthesis may be less precise |
| A source file is a cloud-only OneDrive stub | Note it, continue with others; tell user to right-click → "Always keep on this device" |
| Project root ambiguous | Ask user to confirm path |
| kaizen-pptx-template skill not available | Fall back to the generic "pptx" skill for the deck |
| Missing content for a slide | Insert `[TO BE CONFIRMED — field]` placeholder |
| python-pptx / python-docx / openpyxl not installed | `pip install python-pptx python-docx openpyxl --break-system-packages` |
| Slides render blank after editing | Revert and use raw XML editing (not python-pptx DOM) |
| Placeholders overlap at (0,0) | Missing `<a:xfrm>` positions — copy from layout XML |
| Economic data found in source docs | Skip entirely — do NOT include in any deliverable |
| Technology stack unclear from docs | Generate tech checklist with standard items; note to confirm with Tech Lead |
| Plan or Charter template missing from `templates/` | Stop for that deliverable; report the missing template file — do NOT silently fall back to generating from scratch |
| Fewer than the nine workstream blocks needed | Use only the blocks you need; clear the unused headers and TASK rows with the `clear()` helper |
| More than 9 workstreams or >20 tasks in one | Split across blocks; if still over capacity (9×20), note the overflow for the EL |
| Charter Sponsor / PM not named in sources | Fill `[TO BE CONFIRMED]` in Project Detail and Sign-off rows |
| openpyxl warns data-validation extension dropped | Expected — cosmetic; the Status dropdown may be lost but typed values stay valid |
| `1. Sales Handoff & Transition/` folder missing | Create it (or confirm project root) before saving the charter |
