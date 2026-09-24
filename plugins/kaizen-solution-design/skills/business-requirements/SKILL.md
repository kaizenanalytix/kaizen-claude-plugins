---
name: business-requirements
description: >
  Use this skill when the Business Analyst (BA) or Project Manager (PM) wants to draft the
  Business Requirements Document.
  Trigger on: "draft BRD", "create business requirements", "generate BRD",
  "business requirements document", "draft requirements doc", "write up the requirements",
  "generate business requirements".
  This skill reads the kickoff deck, KT brief, and planning documents from the project folder,
  generates a Business Requirements Document (.docx), and saves it to `requirements/`.
---

# business-requirements Skill

Generate the Business Requirements Document from the kickoff deck, KT brief,
and client workshop inputs. Output: a structured .docx saved to `requirements/`.

**Guardrails:** Before writing any file, show the proposed path and get the user's confirmation.
Never overwrite an existing file — if the target name already exists, save a new version (append
" v2", " v3", …). Keep any financial figures verbatim.

---

## Step 0 — Locate the Project Folder

Work inside the connected/working project folder. If no project folder is connected, ask the user
to connect or point to it. If the project folder is ambiguous, ask the user to confirm the path
before proceeding.

---

## Step 1 — Inventory Source Documents

Search the project folder recursively for the source documents:

```bash
find "<PROJECT_FOLDER>" -type f | sort
```

Identify and prioritise:

| Source | Purpose |
|---|---|
| Internal kickoff deck | Scope, objectives, solution overview, team |
| KT brief (.docx) | Deal summary, scope, risks, data requirements |
| SOW | Contractual scope, deliverables, acceptance criteria |
| Client workshop notes (if present) | Detailed requirements from discovery sessions |
| Solution overview diagram | Architecture context |

If a needed input can't be found or its location is ambiguous, ask the user to point at the file(s).
If no kickoff deck or KT brief is found, stop and advise:
> "To draft the BRD, I need the kickoff deck or KT brief. Please point me at these files in the
> project folder."

---

## Step 2 — Extract Requirements Content

Extract text from each source document using an appropriate reader for its file type.

From the extracted content, populate:

### 2.1 Project Context
- Project name, client, objectives (from kickoff deck)
- Business problem statement
- Current state description
- Desired future state

### 2.2 Stakeholders
- Business stakeholders and their interests
- Technical stakeholders
- End users of the solution

### 2.3 Functional Requirements
Use MoSCoW prioritisation:
- **Must Have** — critical for go-live
- **Should Have** — important but not blocking
- **Could Have** — desirable if time permits
- **Won't Have** (this release) — explicitly excluded

For each requirement:

| Field | Description |
|---|---|
| ID | FR-001, FR-002, ... |
| Description | Clear, specific, testable statement |
| Priority | Must / Should / Could / Won't |
| Source | Who requested it (client stakeholder, SOW, workshop) |
| Acceptance Criteria | Given/When/Then format |
| Dependencies | Other requirements or external systems |

### 2.4 Non-Functional Requirements (NFRs)

| Category | Examples |
|---|---|
| Performance | Response time, throughput, data processing SLAs |
| Scalability | Expected data growth, concurrent users |
| Security | Authentication, authorisation, encryption, compliance |
| Availability | Uptime requirements, disaster recovery |
| Usability | User experience expectations, accessibility |
| Data | Retention, archival, quality thresholds |
| Integration | API response times, retry policies, SLAs |

### 2.5 Data Requirements
- Data sources and formats
- Data quality expectations
- Data transformation rules
- Data validation criteria

### 2.6 Assumptions & Constraints
- Business assumptions
- Technical constraints
- Regulatory constraints
- Timeline constraints

### 2.7 Out of Scope
- Explicitly excluded items (from SOW)
- Deferred to future phases

---

## Step 3 — Generate the BRD (.docx)

Produce a .docx with this structure:

```
BUSINESS REQUIREMENTS DOCUMENT
[Client Familiar Name] [Timing] [Project Name]
Version: 1.0
Author: [BA Name / PM Name]
Date: [today's date]
Status: Draft

────────────────────────────────────
Document Control
  Version History table: Version | Date | Author | Changes

1. INTRODUCTION
   1.1 Purpose
   1.2 Project Context
   1.3 Business Problem Statement
   1.4 Scope (In-Scope / Out-of-Scope)

2. STAKEHOLDERS
   [Stakeholder table: Name | Role | Interest | Involvement Level]

3. FUNCTIONAL REQUIREMENTS
   3.1 Must Have
     [Requirements table: ID | Description | Source | Acceptance Criteria | Dependencies]
   3.2 Should Have
     [Same table format]
   3.3 Could Have
     [Same table format]
   3.4 Won't Have (This Release)
     [List with rationale]

4. NON-FUNCTIONAL REQUIREMENTS
   [NFR table: ID | Category | Description | Target / Metric]

5. DATA REQUIREMENTS
   [Data table: Source | Format | Volume | Quality Criteria | Transformation Rules]

6. ASSUMPTIONS & CONSTRAINTS
   [Table: ID | Type (Assumption/Constraint) | Description | Impact if Invalid]

7. DEPENDENCIES
   [Table: ID | Description | Owner | Target Date | Risk if Delayed]

8. ACCEPTANCE CRITERIA
   Summary of how the solution will be validated against these requirements.

9. APPENDICES
   A. Glossary of Terms
   B. Reference Documents
```

### Formatting rules
- Table header rows: Kaizen navy `#0A2342`, white text
- MoSCoW priority tags: Must = red bold, Should = amber, Could = green, Won't = grey
- "TBD" or missing fields: orange highlight
- Document must be skimmable — use tables over paragraphs

---

## Step 4 — Save the Output

Present the proposed file to the user (confirm before writing):
```
Proposed file:
  <PROJECT_FOLDER>/requirements/Business Requirements.docx

Reply "save" to write this file, or "revise" to make changes.
```

Create the `requirements/` subfolder under the project folder if it doesn't exist. Check for
existing versions (don't overwrite; version instead).

After saving, share the generated file with the user.

---

## Step 5 — Summary in Chat

```
✅ BRD generated: requirements/Business Requirements.docx

Requirements summary:
  • Functional requirements: N total (Must: N, Should: N, Could: N, Won't: N)
  • Non-functional requirements: N
  • Data requirements: N sources
  • Assumptions: N | Constraints: N

Items requiring follow-up (marked TBD in doc):
  • [list any incomplete requirements]

Suggested next: Schedule a requirements review with stakeholders. Once signed off,
say "update solution overview" to refresh the solution overview diagram.
```

---

## Error Handling

| Situation | Action |
|---|---|
| No source documents found | Stop; advise user to ensure kickoff deck or KT brief exists |
| Requirements vague in source docs | Generate with `[TBD — clarify with client]` placeholders |
| No acceptance criteria stated | Add placeholder: "Given [context], when [action], then [expected outcome — TBD]" |
| A source file is a cloud-only stub | Note it, continue with others; advise user |
| Project folder ambiguous | Ask user to confirm path |

---

_Last reviewed: 2026-08-27_
