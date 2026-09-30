---
name: closeout-archive
description: >
  Use this skill when the PM or EL wants to perform the Project Closeout (D31, Mandatory)
  and archive all project deliverables (T40, Mandatory) for a Kaizen PDP engagement.
  Trigger on: "project closeout", "close the project", "archive deliverables",
  "generate closeout", "D31 closeout", "T40 archive", "close out the project",
  "project closeout and archive", "finalise the project".
  This skill reads the full engagement record, generates a Project Closeout document (.docx),
  triggers archive of all deliverables via archive_deliverables, and saves to "6. Deploy".
---

# closeout-archive Skill

Generate the Project Closeout document (D31, Mandatory) and trigger archival of all project
deliverables (T40, Mandatory). This is the final PDP skill — it closes the project lifecycle.
The closeout incorporates the project insights summary (key findings and results) directly,
so there is no separate insights deliverable. Output: a .docx saved to `6. Deploy`, plus
archived deliverables.

Dependencies: read_phase_docs (shared MCP tool), write_deliverable (shared MCP tool),
archive_deliverables (shared MCP tool).

> **Guardrails:** This skill follows the shared guardrails (G1–G5) defined in the `guardrails`
> skill of shared-foundation-plugin. See that skill for version-not-overwrite, confirmation
> gates, verbatim financial data, deterministic finance, and approval gate rules.

---

## Step 0 — Locate the Project Root

Find the folder containing `6. Deploy/`.

If no workspace folder is connected, use `mcp__cowork__request_cowork_directory` to request one.
Extract the `PROJECT_ID`.

---

## Step 1 — Pre-Closeout Checklist

Before generating the closeout document, verify that the required Deploy-phase deliverables
exist:

```bash
for phase in "0. Sales Alignment" "1. Sales Handoff & Transition" "2. Plan" "3. Analyze" "4. Design" "5. Develop" "6. Deploy"; do
  echo "=== $phase ==="
  find "<PROJECT_ROOT>/$phase/" -type f 2>/dev/null | sort
done
```

### Required before closeout (Deploy phase gate):
- [ ] D29 Deployment/handoff checklist — exists in `6. Deploy/`?
- [ ] D30 Project Sign-Off — exists in `6. Deploy/`?
- [ ] D32 Case Study — exists in `6. Deploy/`?
- [ ] T37 Solution deployed
- [ ] T38 Support plan reviewed

If any mandatory items are missing, warn the user:
> "⚠ The following mandatory Deploy items are not yet complete: [list]. Proceeding with
> closeout will mark the project as closed with these items outstanding. Continue? (yes/no)"

---

## Step 2 — Gather Closeout Information

### 2.1 From Project Documents
Read key documents for the closeout record:

| Source | Purpose |
|---|---|
| Project Sign-Off (D30) | Acceptance status, outstanding items |
| SOW (D10) | Original scope for variance analysis |
| RAID Log | Final risk/issue status |
| Status Reports (D16) | Project history |
| All phase folders | Complete deliverables inventory |

### 2.2 From the PM/EL (conversational input)
- Project retrospective notes (T39, if conducted)
- Lessons learned
- Final team roster and their contributions
- Client relationship status at closeout
- Any post-project commitments (hypercare, follow-ons)

---

## Step 3 — Build the Closeout Document

### 3.1 Project Summary
- Client, project name, project ID
- Start date, end date, total duration
- Delivery model (from SOW, per G3)
- EL, PM, and key team members

### 3.2 Scope Summary
- Original scope (from SOW, per G3)
- Final delivered scope
- Scope changes (list all CRs and their outcomes)
- Variance analysis: what was delivered vs what was contracted

### 3.3 Deliverables Register
Complete inventory of all deliverables across all phases:

| Phase | Deliverable | PDP ID | Mandatory | Status | File Location |
|---|---|---|---|---|---|
| Sales Alignment | NDA | D1 | Y | Complete | 0. Sales Alignment/... |
| ... | ... | ... | ... | ... | ... |
| Deploy | Project Closeout | D31 | Y | This document | 6. Deploy/... |

### 3.4 Timeline Summary
- Planned vs actual timeline
- Key milestones: planned date vs actual date
- Sprint count: planned vs actual

### 3.5 RAID Log Final Status

| Type | Total | Open | Closed | Key Items |
|---|---|---|---|---|
| Risks | N | N | N | [list any that materialised] |
| Actions | N | N | N | [list any outstanding] |
| Issues | N | N | N | [list any unresolved] |
| Decisions | N | N | N | [key decisions for the record] |

### 3.6 Lessons Learned
- What went well (process, technical, team, client)
- What could be improved
- Recommendations for similar future engagements
- Kaizen process improvements identified

### 3.7 Post-Project Commitments

| Commitment | Owner | Duration | Status |
|---|---|---|---|
| Hypercare support | [PM] | [duration] | Active / Complete |
| Follow-on pursuit | [EL] | Ongoing | See Pursuit Plan |
| Documentation updates | [Tech Lead] | [date] | Pending / Complete |

### 3.8 Knowledge Artefacts
List reusable assets produced during the engagement:
- Templates, frameworks, or accelerators
- Code libraries or components (if open-sourced)
- Training materials
- Case study (D32)

Per G4: do NOT include financial close-out figures (final billing, margin analysis, etc.).
Financial closeout is handled outside PDP via P3 economics and Ruddr.

---

## Step 4 — Generate the Closeout Document (.docx)

Produce a .docx with this structure:

```
PROJECT CLOSEOUT
[Client Familiar Name] [Timing] [Project Name]
Date: [today's date]
Author: [PM Name]

────────────────────────────────────
1. PROJECT SUMMARY
   [Summary table: Client, Project ID, Dates, Duration, Model, EL, PM]

2. SCOPE SUMMARY
   2.1 Original Scope (from SOW)
   2.2 Final Delivered Scope
   2.3 Change Requests
   2.4 Variance Analysis

3. DELIVERABLES REGISTER
   [Full table across all phases: Phase | Deliverable | PDP ID | Mandatory | Status | Location]

4. TIMELINE SUMMARY
   [Table: Milestone | Planned Date | Actual Date | Variance]

5. RAID LOG FINAL STATUS
   [Summary table + notable items]

6. LESSONS LEARNED
   6.1 What Went Well
   6.2 Areas for Improvement
   6.3 Recommendations

7. POST-PROJECT COMMITMENTS
   [Table: Commitment | Owner | Duration | Status]

8. KNOWLEDGE ARTEFACTS
   [Table: Artefact | Type | Location | Reusable?]

9. SIGN-OFF
   Kaizen PM: _________________ Date: _________
   Kaizen EL: _________________ Date: _________
```

### Formatting rules
- Table header rows: Kaizen navy `#0A2342`, white text
- Status column: Complete = green, Outstanding = red
- SOW text: copied verbatim per G3
- Lessons learned: bullet format, actionable

---

## Step 5 — Archive All Deliverables (T40)

After the closeout document is saved, trigger the archive process:

```
Use archive_deliverables("<PROJECT_ROOT>") to archive all project deliverables.
```

If `archive_deliverables` is not available, present the manual archive checklist:
```
Manual archive checklist:
  [ ] All phase folders (0–6) backed up to [TO CONFIRM — Kaizen archive location]
  [ ] SharePoint permissions set to read-only for project team
  [ ] Jira project marked as complete / archived
  [ ] Ruddr updated with final project status (T9)
  [ ] Client access to shared folders reviewed and adjusted
  [ ] Reusable assets moved to Kaizen knowledge base
```

---

## Step 6 — Save the Output

Present the proposed file to the user (per guardrail G2):
```
Proposed file:
  <PROJECT_ROOT>/6. Deploy/<PROJECT_ID> - Project Closeout.docx

Archive action:
  archive_deliverables will be called to archive all project folders.

Reply "save and archive" to proceed, or "revise" to make changes.
```

Per G5: confirm with PM/EL before archiving (this is irreversible in some archive systems).

Check for existing versions (per guardrail G1).

After saving, present the file using `mcp__cowork__present_files`.

---

## Step 7 — Summary in Chat

```
✅ Project Closeout generated: 6. Deploy/<PROJECT_ID> - Project Closeout.docx
✅ Deliverables archived: [archive status]

Closeout summary:
  • Duration: [start] – [end] ([N weeks/months])
  • Deliverables: N total (Complete: N, Outstanding: N)
  • Change requests: N
  • Lessons learned: N items documented
  • Post-project commitments: N items

Archive status:
  • [archive tool result or manual checklist status]

🏁 Project [PROJECT_ID] is now closed.

All PDP phases are complete. The case study (D32) is available for the Kaizen portfolio.
```

---

## Error Handling

| Situation | Action |
|---|---|
| Mandatory Deploy items missing | Warn user; allow closeout with acknowledgement |
| archive_deliverables tool not available | Present manual archive checklist |
| Project Sign-Off (D30) not found | Warn: "Project has not been formally signed off" |
| Retrospective not conducted | Note in lessons learned: "Retrospective not conducted" |
| A source file is a cloud-only stub | Note it, continue; advise user (see m365-file-ops) |
| Project root ambiguous | Ask user to confirm path |

---

_Last reviewed: 2026-07-07_
