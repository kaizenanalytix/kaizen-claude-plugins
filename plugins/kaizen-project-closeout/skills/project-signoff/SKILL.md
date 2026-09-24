---
name: project-signoff
description: >
  Use this skill when the EL or PM wants to prepare the Project Sign-Off document
  (D30, Mandatory) for a Kaizen PDP engagement.
  Trigger on: "prepare project sign-off", "generate sign-off", "project sign-off document",
  "client sign-off", "D30 sign-off", "create the sign-off", "project acceptance",
  "generate project sign-off".
  This skill reads the acceptance criteria and deliverables record from across all phases,
  generates a Project Sign-Off document (.docx), and saves it to "6. Deploy".
---

# project-signoff Skill

Generate the Project Sign-Off document (D30, Mandatory) for formal client acceptance of the
delivered solution. This document records what was delivered against what was contracted,
acceptance criteria status, and sign-off signatures. Output: a .docx saved to `6. Deploy`.

Dependencies: read_phase_docs (shared MCP tool), write_deliverable (shared MCP tool).

> **Guardrails:** This skill follows the shared guardrails (G1–G5) defined in the `guardrails`
> skill of shared-foundation-plugin. See that skill for version-not-overwrite, confirmation
> gates, verbatim financial data, deterministic finance, and approval gate rules.

---

## Step 0 — Locate the Project Root

Find the folder containing `6. Deploy/`.

If no workspace folder is connected, use `mcp__cowork__request_cowork_directory` to request one.
Extract the `PROJECT_ID`.

---

## Step 1 — Inventory Project Deliverables

Scan all phase folders to build a complete deliverables register:

```bash
for phase in "0. Sales Alignment" "1. Sales Handoff & Transition" "2. Plan" "3. Analyze" "4. Design" "5. Develop" "6. Deploy"; do
  echo "=== $phase ==="
  find "<PROJECT_ROOT>/$phase/" -type f 2>/dev/null | sort
done
```

Also read:
- SOW (D10) — contracted scope and acceptance criteria
- BRD (D18) — requirements with acceptance criteria
- Test results / UAT sign-off (if documented)

---

## Step 2 — Build Sign-Off Content

### 2.1 Project Summary
- Client name, project name, project ID
- Engagement start date and end date
- Delivery model (from SOW, copied verbatim per G3)
- EL name and PM name

### 2.2 Scope Delivered vs Contracted
For each contracted deliverable from the SOW:

| SOW Item | Deliverable | Status | Evidence / Location | Notes |
|---|---|---|---|---|
| [item from SOW] | [what was delivered] | Complete / Partial / Deferred | [file path in phase folder] | [any notes] |

Per G3: copy SOW deliverable descriptions verbatim. Do not paraphrase or summarise.

### 2.3 Acceptance Criteria Status
For each acceptance criterion from the SOW or BRD:

| ID | Criterion | Status | Evidence | Accepted By |
|---|---|---|---|---|
| AC-01 | [criterion text — verbatim from SOW per G3] | Met / Partially Met / Not Met | [test result, demo, UAT] | [client name] |

### 2.4 Change Requests
List all change requests raised during the engagement:

| CR# | Description | Status | Impact |
|---|---|---|---|
| CR-001 | [description] | Approved / Rejected / Pending | [scope/timeline impact] |

### 2.5 Known Issues / Limitations
Any open defects or known limitations at time of sign-off:

| ID | Description | Severity | Mitigation | Resolution Plan |
|---|---|---|---|---|
| [ID] | [issue] | [High/Med/Low] | [workaround] | [when it will be fixed] |

### 2.6 Outstanding Items
Items that remain open post sign-off (e.g. hypercare, documentation updates):

| Item | Owner | Target Date |
|---|---|---|
| [item] | [owner] | [date] |

### 2.7 Sign-Off

Per G5: this is a client-facing document requiring explicit EL approval before sharing.

---

## Step 3 — Generate the Sign-Off (.docx)

Produce a .docx with this structure:

```
PROJECT SIGN-OFF
[Client Familiar Name] [Timing] [Project Name]
Date: [today's date]

────────────────────────────────────
1. PROJECT SUMMARY
   [Summary table: Client, Project ID, Start Date, End Date, Delivery Model, EL, PM]

2. SCOPE DELIVERED
   [Deliverables table: SOW Item | Delivered | Status | Evidence | Notes]

3. ACCEPTANCE CRITERIA
   [Criteria table: ID | Criterion | Status | Evidence | Accepted By]

4. CHANGE REQUESTS
   [CR table: CR# | Description | Status | Impact]

5. KNOWN ISSUES & LIMITATIONS
   [Issues table: ID | Description | Severity | Mitigation | Resolution Plan]

6. OUTSTANDING ITEMS
   [Items table: Item | Owner | Target Date]

7. SIGN-OFF APPROVAL

   By signing below, the parties confirm that the project deliverables have been reviewed
   and accepted in accordance with the Statement of Work.

   Kaizen Analytix:
   Name: ________________________  Role: Engagement Lead
   Signature: ____________________  Date: ____________

   Name: ________________________  Role: Project Manager
   Signature: ____________________  Date: ____________

   [Client Name]:
   Name: ________________________  Role: [Client Project Lead]
   Signature: ____________________  Date: ____________

   Name: ________________________  Role: [Client Executive Sponsor]
   Signature: ____________________  Date: ____________
```

### Formatting rules
- Table header rows: Kaizen navy `#0A2342`, white text
- Status column: Complete = green, Partial = amber, Not Met = red, Deferred = grey
- Acceptance criteria verbatim from SOW (per G3)
- Signature lines: clearly formatted with space for wet or digital signatures

---

## Step 4 — Save the Output

Present the proposed file to the user (per guardrail G2):
```
Proposed file:
  <PROJECT_ROOT>/6. Deploy/<PROJECT_ID> - Project Sign-Off.docx

⚠ This is a client-facing sign-off document. Review carefully with the EL before sharing.

Reply "save" to write this file, or "revise" to make changes.
```

Per G5: confirm with EL before finalising.

Check for existing versions (per guardrail G1).

After saving, present the file using `mcp__cowork__present_files`.

---

## Step 5 — Summary in Chat

```
✅ Project Sign-Off generated: 6. Deploy/<PROJECT_ID> - Project Sign-Off.docx

Sign-off summary:
  • Deliverables: N total (Complete: N, Partial: N, Deferred: N)
  • Acceptance criteria: N total (Met: N, Partially Met: N, Not Met: N)
  • Change requests: N (Approved: N, Rejected: N, Pending: N)
  • Known issues: N (High: N, Medium: N, Low: N)
  • Outstanding items: N

⚠ EL review required before sharing with the client.

Suggested next: Route to EL for review, then to client for signature.
Say "create case study" to produce D32.
```

---

## Error Handling

| Situation | Action |
|---|---|
| SOW not found | Ask user for contracted scope; flag that sign-off may be incomplete |
| Acceptance criteria not documented | Ask user/EL for criteria; insert `[TO CONFIRM]` |
| Deliverable status unclear | Default to `[TO CONFIRM]`; ask user to verify |
| A source file is a cloud-only stub | Note it, continue; advise user (see m365-file-ops) |
| Project root ambiguous | Ask user to confirm path |

---

_Last reviewed: 2026-07-07_
