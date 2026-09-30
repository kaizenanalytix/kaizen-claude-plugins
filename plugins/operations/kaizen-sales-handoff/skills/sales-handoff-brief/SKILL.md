---
name: sales-handoff-brief
description: >
  Use this skill when the Engagement Lead (EL) wants to generate a Sales-to-Delivery Knowledge
  Transfer Brief from the Phase 0 sales documents.
  Trigger on: "generate handoff brief", "create KT brief", "sales handoff summary",
  "knowledge transfer brief", "generate sales brief", "handoff to delivery team",
  "create the brief", "run the KT brief", "sales to delivery handoff".
  This skill reads all documents from "0. Sales Alignment", synthesises a structured brief,
  and writes a .docx file to "1. Sales Handoff & Transition".
---

# sales-handoff-brief Skill

Synthesise all Phase 0 Sales Alignment documents into a structured Knowledge Transfer Brief for
the Kaizen delivery team. Output: a formatted .docx saved to `1. Sales Handoff & Transition`.

---

## Step 0 — Locate the Project Root

Find the folder containing both `0. Sales Alignment/` and `1. Sales Handoff & Transition/`.

If no workspace folder is connected, use `mcp__cowork__request_cowork_directory` to request one.
If the project root is ambiguous, ask the user to confirm the path before proceeding.

Extract the `PROJECT_ID` from `.kaizen-project.json` if present, or ask the user:
```bash
cat "<PROJECT_ROOT>/.kaizen-project.json" 2>/dev/null || echo "not found"
```

---

## Step 1 — Inventory Phase 0 Documents

List all files in `0. Sales Alignment/` and classify each by document type:

```bash
find "<PROJECT_ROOT>/0. Sales Alignment/" -type f | sort
```

| Filename keyword | Document type |
|---|---|
| SOW, statement-of-work | Statement of Work (D10) |
| proposal, client-proposal | Client Proposal (D7) |
| solution-overview, solution_overview | Solution Overview Diagram (D4) |
| NDA, non-disclosure | NDA (D1) |
| opportunity, ask, problem-statement | Opportunity summary (D2) |
| MSA, master-service | MSA (D9) |
| P3, economics, project-economics | P3 Project Economics (D5) |
| data-request, data_request | Data Request Document (D8) |
| scope, estimation, estimate | Project Scope & Estimation Summary (D3) |
| review-committee, DRC | Deal Review Committee Submission (D6) |

If the folder is empty, stop and tell the user:
> "The Sales Alignment folder is empty. Please upload your Phase 0 documents (SOW, proposal, P3, NDA, MSA, etc.) into '0. Sales Alignment' and then re-run this skill."

---

## Step 2 — Extract Content from Each Document

Extract text from each file based on type. Install dependencies if missing:
```bash
pip install python-docx python-pptx openpyxl --break-system-packages -q
apt-get install -y poppler-utils -q 2>/dev/null || true
```

**PDF:**
```bash
pdftotext "<file_path>" -
```

**DOCX:**
```python
from docx import Document
doc = Document("<file_path>")
for para in doc.paragraphs: print(para.text)
```

**PPTX:**
```python
from pptx import Presentation
prs = Presentation("<file_path>")
for slide in prs.slides:
    for shape in slide.shapes:
        if hasattr(shape, "text"): print(shape.text)
```

**XLSX/CSV:**
```python
import pandas as pd
df = pd.read_excel("<file_path>")  # or pd.read_csv
print(df.to_string())
```

Label each extracted block clearly: `[SOW]`, `[PROPOSAL]`, `[P3]`, etc.

---

## Step 3 — Extract Structured Fields

From all extracted content, populate the following fields.
Mark any missing field as: **"Not specified — confirm with sales lead"** (will be highlighted orange in the doc).

### 3.1 Deal Summary
- Client Name
- Project Name / Engagement Name (`[Client Familiar Name] [Timing] [Project Name]` format)
- Project Code (if referenced)
- Proposed Start Date
- Proposed End Date / Duration
- Delivery Model (Fixed Price / T&M / Retainer)
- Sales Lead Name

### 3.2 Scope & Objectives
- In-Scope items (max 10 bullets, from SOW)
- Out-of-Scope items (explicitly excluded)
- Key Deliverables (final outputs client receives)
- Success Criteria / Acceptance Criteria

### 3.3 Solution Approach
- Solution Summary (2–3 sentences, plain English)
- Key Technologies & Tools
- Data Sources & Integrations
- Architecture Notes / Constraints

### 3.4 Data Requirements
- Data requested (from D8 data request doc)
- Agreed data delivery dates
- Systems / environments access needed
- Data sensitivity / compliance notes (PII, HIPAA, GDPR, etc.)

### 3.5 Key Risks & Assumptions
List all risks, assumptions, dependencies, and open questions noted during sales.
Flag unresolved items clearly.

### 3.6 Commercial Terms
- Total Contract Value (from P3 or SOW)
- Payment Milestones
- Rate Card / Billing Structure
- Budget Constraints or Caps
- **Penalty Clauses or SLA commitments** — flag these in yellow

### 3.7 Team & Timeline
Build a contact table:

| Role | Name | Organisation | Email |
|---|---|---|---|
| Client Executive Sponsor | | | |
| Client Project Lead | | | |
| Client Technical Contact | | | |
| Kaizen Sales Lead | | | |
| Kaizen Engagement Manager | | | |

Proposed timeline with key milestones if stated.

### 3.8 Open Items from Sales
Items marked as unresolved, deferred, or requiring follow-up from the delivery team.

---

## Step 4 — Generate the KT Brief DOCX

Read the docx skill first:
```
Read: mnt/.claude/skills/docx/SKILL.md
```

Then produce a .docx with this structure:

```
KNOWLEDGE TRANSFER BRIEF
[Client Familiar Name] [Timing] [Project Name]
Prepared by: Kaizen Analytix Sales Team
Handoff Date: [today's date]
Recipient: Delivery Team

────────────────────────────────────
1. DEAL SUMMARY
   [Summary table: client, project ID, dates, model, TCV, sales lead]

2. SCOPE & OBJECTIVES
   2.1 In-Scope
   2.2 Out-of-Scope
   2.3 Key Deliverables
   2.4 Success Criteria

3. SOLUTION APPROACH
   3.1 Solution Summary
   3.2 Technologies & Tools
   3.3 Data Sources & Integrations
   3.4 Architecture Notes

4. DATA REQUIREMENTS
   [Table: data source | delivery date | access type | sensitivity]

5. KEY RISKS & ASSUMPTIONS
   [Table: item | type (Risk/Assumption/Open Item) | owner | status]

6. COMMERCIAL TERMS
   [Table: TCV | payment milestones | billing structure]
   ⚠ Penalty Clauses / SLAs: [yellow highlight if present]

7. TEAM & CONTACTS
   [Contact table]

8. OPEN ITEMS FOR DELIVERY TEAM
   [Table: item | priority | owner]

9. PHASE 0 CHECKLIST STATUS
   Columns: Deliverable | Mandatory | Status | Notes
   List all D1–D10 and T1–T9 with status based on documents found.

10. RECOMMENDED NEXT STEPS (Phase 1)
    Standard Phase 1 tasks for the delivery team:
    - T10: Sales knowledge transfer meeting with delivery team (Mandatory)
    - T11: Jira Set Up (Mandatory)
    - T12: Receive Data samples
    - T13: Identify team members (Mandatory)
    - T14: Review Agile Best Practices Guidelines
    - T15: Draft Kickoff PPT (Mandatory)
    - T16: Complete Internal Kickoff w/ Project team (Mandatory)
    Mandatory deliverables to produce:
    - D11: Internal Kickoff PPT
    - D13: Project technical checklist
```

### Formatting rules
- Table header rows: Kaizen navy `#0A2342`, white text
- "Not specified" fields: orange highlight — need follow-up
- Penalty clauses / SLA commitments: yellow highlight
- Do NOT reproduce full document text — summarise and extract key points only
- Brief must be skimmable in under 10 minutes

---

## Step 5 — Save the Output

Save to:
```
<PROJECT_ROOT>/1. Sales Handoff & Transition/<PROJECT_ID> - KT Brief.docx
```

If PROJECT_ID is not known, use: `[Client Familiar Name] [Project Name] - KT Brief.docx`

After saving, present the file using `mcp__cowork__present_files`.

---

## Step 6 — Summary in Chat

```
✅ KT Brief generated: 1. Sales Handoff & Transition/<PROJECT_ID> - KT Brief.docx

Documents read from Phase 0:
  • [list each file and its identified type]

Fields requiring follow-up (marked orange in doc):
  • [list any "Not specified" fields]

⚠ Flags:
  • [list any penalty clauses, SLAs, or unresolved open items]

Suggested next: Say "generate kickoff PPT" to produce the Internal Kickoff deck.
```

---

## Error Handling

| Situation | Action |
|---|---|
| Phase 0 folder is empty | Stop and ask user to upload documents |
| A file cannot be read | Skip it, note it in summary, continue with others |
| No SOW found | Generate brief with prominent warning: "SOW not found — scope section incomplete" |
| Project root ambiguous | Ask user to confirm path |
| `python-docx` not installed | Run `pip install python-docx --break-system-packages` |
| `pdftotext` not available | Run `apt-get install -y poppler-utils` |
