---
name: kaizen-pdp-phases
description: >
  Use this skill when the Engagement Lead (EL) wants guidance on the Kaizen PDP checklist,
  phase requirements, what to do next on a project, or how Kaizen's EL processes actually
  work (drawing on the EL Knowledge Base on SharePoint).
  Trigger on: "what's next", "PDP status", "show checklist", "what's mandatory",
  "phase guide", "what deliverables are left", "PDP overview", "show me the checklist",
  "what do I need to do in [phase]", "what's mandatory in [phase]", "what phase are we in",
  "PDP checklist", "show PDP phases", "phase overview".
  Also trigger on EL "how-to" / process questions that the handbook or knowledge base answers:
  "how do I set up a project in PSA/Sage", "what's the process for X", "what does the EL
  handbook say about Y", "agile best practices", "EL timesheet checklist", "how does Kaizen
  handle Z", "what are the do's and don'ts for W".
  This skill is a REFERENCE GUIDE only — it does not generate documents. For document
  generation, invoke the relevant skill (sales-handoff-brief, project-kickoff-init, etc.).
---

# kaizen-pdp-phases Skill

Interactive reference for the Kaizen PDP (Project Delivery Process) checklist, aligned to the
**PDP Deliverables (June 22 2026)** sheet. Answers questions about phases, mandatory items, and
what to do next. For "how do we actually do this" process questions, it also consults the
**EL Knowledge Base** on SharePoint (see below). Does NOT generate files — guides and
references only.

**Two sources of truth, two kinds of question:**

- **Structure / status questions** ("what's mandatory in Design", "what phase are we in",
  "show the checklist") → answer from the bundled checklist (`references/pdp-checklist.md`
  and the phase tables below). Fast and deterministic — do NOT hit SharePoint for these.
- **Process / how-to questions** ("how do I set up a project in PSA", "what does the handbook
  say about allocations", "agile best practices") → search the **EL Knowledge Base** folder
  (see "EL Knowledge Base Lookup") and answer from the actual documents, with a citation.

---

## Full PDP Phase & Checklist Reference

The complete checklist is in `references/pdp-checklist.md`. Load it when answering phase-specific
questions. It is the single source of truth for deliverable IDs, names, and mandatory flags.

---

## EL Knowledge Base Lookup (SharePoint)

For process / how-to questions (not checklist-structure questions), consult the **EL Knowledge
Base** — a curated SharePoint folder of the handbooks and process guides an EL should know.

**Location (as of 2026-07):**
`Emerging Technologies > Shared Documents > ET Core > Claude Tests Folder > EL Knowledge Base`
Do not hard-code the path or file IDs — always resolve the folder by name so it survives moves.

### When to use it

Use it when the EL asks *how a process works* or *what a Kaizen guide says*, e.g. project
setup in PSA/Sage, allocations and resourcing, agile best practices, the EL handbook, timesheet
expectations. Do NOT use it for pure checklist/phase/mandatory questions — those are answered
locally from `references/pdp-checklist.md` and the phase tables.

### How to use it (required flow)

1. **Scope every search to the folder.** Call `sharepoint_search` with the user's keywords AND
   `folderName: "EL Knowledge Base"`. Without the folder scope, the same query returns 100+
   unrelated project docs from across the tenant — always filter.
2. **Open the top hit(s).** The search result is metadata + a truncated snippet only. Call
   `read_resource` on the returned `uri` to get the full document text before answering. Read
   more than one file if the answer might span documents.
3. **Answer from the document, then cite it.** Give a concise, action-oriented answer and end
   with a `Sources:` line linking the document by its `webUrl`, e.g.
   `Sources: [The Engagement Lead Handbook](<webUrl>)`.
4. **If nothing relevant is found,** say so plainly and fall back to the bundled PDP reference
   rather than guessing.

### Known documents in the folder (for orientation, not exhaustive — always search live)

- **The Engagement Lead Handbook.pptx** — the primary EL reference (roles, PDP overview, expectations).
- **The Engagement Lead Handbook v2.1 PDP Slides Only.pptx** — PDP-focused subset of the handbook.
- **Project setup process - Sage v2.pptx** — PSA/Sage project creation, allocations, roles, revenue, do's & don'ts.
- **Kaizen Agile Best Practices - Internal Services Guidelines 2022.pptx** — agile delivery practices.
- **Weekly EL Timesheet Checklist - Jan302026.docx** — weekly timesheet expectations.

### ⚠️ Image / diagram limitation (important)

`read_resource` extracts **text** — including text inside tables, bullet lists, and shape-based
diagrams / SmartArt (e.g. flowchart boxes with text labels). It does **not** OCR or interpret
*flattened raster images* (screenshots, exported PNG diagrams, pictures with no underlying text);
those slides return little or nothing. If an answer clearly depends on a graphic that didn't come
through as text:
- Say the detail lives in a diagram that couldn't be read as text, and cite the doc + slide so
  the EL can open it directly.
- Do **not** fabricate the contents of a diagram you couldn't read.
- KB-side fix (recommended to the owner): add a short description in the slide's **speaker notes**
  or a caption text box — notes extract as text and make the diagram readable to this skill.

---

## How to Respond

### "What's next?" or "What phase are we in?"

1. Ask the user (or infer from context) which deliverables/tasks have been completed.
2. Determine the current phase based on the checklist's mandatory items:
   - Sales Alignment mandatory: D1, D2, D4, D5, D7, D9, D10
   - Sales Handoff & Transition mandatory: D11, D13
   - Plan mandatory: D15, D16, D17
   - Analyze mandatory: D18, D19, D20
   - Design mandatory: D21, D22, D23, D24
   - Develop mandatory: D25, D26, D27, D28
   - Deploy mandatory: D29, D30, D31, D32
   - Project Governance mandatory: D33, D34, D35, D36, D37
3. List the next mandatory items to complete.
4. Optionally list the non-mandatory items the team may want to consider.

### "What's mandatory in [phase]?"

Look up the phase in `references/pdp-checklist.md` and list all items where `Mandatory = Y`.
Format as two tables: Deliverables and Tasks.

### "Show me the PDP checklist" or "PDP overview"

Display a compact summary of all 9 folders (phases 0–8) with total mandatory vs total items
counts. Offer to drill into any specific phase.

### "What deliverables are left?"

Ask which phase the user is asking about (or assume current phase).
List all deliverables with their mandatory status and leave the Complete column blank for the user
to track.

### "How do I [process]?" / "What does the handbook say about [X]?"

This is a process / how-to question — use the **EL Knowledge Base Lookup** flow above:
folder-scoped `sharepoint_search` → `read_resource` on the top hit(s) → concise answer with a
`Sources:` citation. Respect the image/diagram limitation. If the KB has nothing relevant, say so
and fall back to the bundled PDP reference.

---

## Phase Summaries (Quick Reference)

### Phase 0: Sales Alignment
Folder: `0. Sales Alignment`
Goal: Close the deal and prepare for handoff (everything through SOW).

| # | Deliverable | Mandatory |
|---|---|---|
| D1 | NDA | Y |
| D2 | Opportunity summary | Y |
| D3 | Project scope & estimation summary | N |
| D4 | High-level solution overview diagram | Y |
| D5 | P3 Project Economics | Y |
| D6 | Deal review committee submission | N |
| D7 | Client proposal | Y |
| D8 | Data request document | N |
| D9 | MSA | Y |
| D10 | SOW | Y |

**AI-assisted:** sales-handoff-brief skill reads Phase 0 docs and generates the KT Brief.

---

### Phase 1: Sales Handoff & Transition
Folder: `1. Sales Handoff & Transition`
Goal: Transfer knowledge from sales to delivery, set up the project (everything after SOW).

| # | Deliverable | Mandatory |
|---|---|---|
| D11 | Internal Kickoff PPT | Y |
| D12 | Project Charter | N |
| D13 | Project technical checklist | Y |

**AI-assisted:** project-kickoff-init skill generates D11 and the Project technical checklist
(D13). project-backlog-init handles Jira (T11).

---

### Phase 2: Plan
Folder: `2. Plan`
Goal: Establish project governance, plans, and kick off with the client.

| # | Deliverable | Mandatory |
|---|---|---|
| D14 | Enter User stories in JIRA | N |
| D15 | Kickoff document and minutes | Y |
| D16 | Status Report | Y |
| D17 | Project Plan/WBS | Y |

**AI-assisted:** status-report skill generates D16. project-kickoff-init generates D15.
project-backlog-init handles D14.

---

### Phase 3: Analyze
Folder: `3. Analyze`
Goal: Confirm requirements, validate data, manage scope changes.

| # | Deliverable | Mandatory |
|---|---|---|
| D18 | Business Requirements, with sign off | Y |
| D19 | Validated Data Set | Y |
| D20 | Change Request Template | Y |

**AI-assisted:** business-requirements skill generates D18. change-request skill generates D20.

---

### Phase 4: Design
Folder: `4. Design`
Goal: Finalise technical design, data flows, and test/training plans.

| # | Deliverable | Mandatory |
|---|---|---|
| D21 | Technical Design | Y |
| D22 | End to End Flows and Data Flow Diagrams | Y |
| D23 | Test Plans | Y |
| D24 | Training Plans | Y |

**AI-assisted:** technical-design skill generates D21 (covers solution/functional design too).
dataflow-diagrams skill generates D22. test-training-plans skill generates D23 and D24.
solution-overview skill produces the detailed end-to-end solution overview diagram (D4) here,
building on the high-level D4 drafted in Phase 0.

---

### Phase 5: Develop
Folder: `5. Develop`
Goal: Build, test, and review the solution with disciplined sprint tracking.

| # | Deliverable | Mandatory |
|---|---|---|
| D25 | Sprint Log | Y |
| D26 | Issue Log | Y |
| D27 | Definition of done | Y |
| D28 | Testing sign off | Y |

**AI-assisted:** sprint-review skill produces the Sprint Log (D25) via the sprint / monthly
review cycle (T32/T33). D26–D28 are tracked manually (no generator skill yet).

---

### Phase 6: Deploy
Folder: `6. Deploy`
Goal: Deploy to production, close the project, create the case study.

| # | Deliverable | Mandatory |
|---|---|---|
| D29 | Deployment/handoff checklist | Y |
| D30 | Project Sign Off | Y |
| D31 | Project Close Out | Y |
| D32 | Kaizen Case Study | Y |

The Deployment/handoff checklist (D29) may bundle the Final Design Document, Training Documents,
and Support Plan as components.

**AI-assisted:** support-plan skill produces the Support Plan component of D29. project-signoff
skill generates D30. closeout-archive skill generates D31 (incorporating the insights summary)
and handles T40. case-study skill generates D32.

---

### Phase 7: Project Governance
Folder: `7. Project Governance`
Goal: House cross-phase governance artifacts that span the full project lifecycle (phases 0–6).

| # | Deliverable | Mandatory |
|---|---|---|
| D33 | RAID Log | Y |
| D34 | RACI Chart | Y |
| D35 | Value Tracker | Y |
| D36 | Business Continuity Plan (BCP) | Y |
| D37 | Updated project governance scorecard | Y |

**AI-assisted:** raid-raci-setup skill generates the RAID Log (D33) and RACI Chart (D34).
status-report skill keeps the governance scorecard (D37) current. Value Tracker (D35) and the
Business Continuity Plan (D36) are tracked manually.

---

### Phase 8: Quality
Folder: `8. Quality`
Goal: Track quality artifacts — satisfaction, quality plan, metrics, and risk.

| # | Deliverable | Mandatory |
|---|---|---|
| D38 | Customer Satisfaction Survey (CSAT) | Y |
| D39 | Quality Plan | N |
| D40 | Project Metrics | N |
| D41 | Risk assessment Sheet | N |

D38–D41 are tracked manually (no generator skill yet).

---

## Gate Logic (Phase Transitions)

| From → To | Gate condition |
|---|---|
| Sales Alignment → Handoff & Transition | Mandatory D1, D2, D4, D5, D7, D9, D10 and T1–T9 (mandatory) complete |
| Handoff & Transition → Plan | D11, D13 done; T10, T11, T13, T15, T16 done |
| Plan → Analyze | D15, D16, D17 done; T18, T21, T23 done |
| Analyze → Design | D18, D19, D20 done; T26 done |
| Design → Develop | D21, D22, D23, D24 done |
| Develop → Deploy | D25, D26, D27, D28 done; T30, T31, T32, T33 done |
| Deploy → Closed | D29, D30, D31, D32 done; T37, T38, T40 done |

---

## AI-Skill Cross-Reference

| Skill | Plugin | Handles |
|---|---|---|
| `sales-handoff-brief` | kaizen-sales-handoff | Phase 0 → Phase 1 KT Brief (supporting handoff doc) |
| `project-kickoff-init` | kaizen-sales-handoff | D11 Internal Kickoff PPT, D13 Project technical checklist, D15 Kickoff document & minutes |
| `project-backlog-init` | kaizen-sales-handoff | D14 User stories in JIRA, T11 Jira Set Up |
| `raid-raci-setup` | kaizen-sales-handoff | D33 RAID Log, D34 RACI Chart (Phase 7 Governance) |
| `status-report` | kaizen-project-governance | D16 Status Report, D37 Governance scorecard |
| `business-requirements` | kaizen-solution-design | D18 Business Requirements |
| `solution-overview` | kaizen-solution-design | High-level D4 in Phase 0; detailed D4 in Design |
| `change-request` | kaizen-solution-design | D20 Change Request Template |
| `technical-design` | kaizen-solution-design | D21 Technical Design (incl. solution/functional design) |
| `dataflow-diagrams` | kaizen-solution-design | D22 E2E / Data Flow Diagrams |
| `test-training-plans` | kaizen-solution-design | D23 Test Plans, D24 Training Plans |
| `sprint-review` | kaizen-project-delivery | D25 Sprint Log via T32/T33 Sprint / Monthly Review |
| `support-plan` | kaizen-project-closeout | Support Plan component of D29 Deployment/handoff checklist |
| `project-signoff` | kaizen-project-closeout | D30 Project Sign Off |
| `case-study` | kaizen-project-closeout | D32 Kaizen Case Study |
| `closeout-archive` | kaizen-project-closeout | D31 Project Close Out (incl. insights), T40 Archive |
| `kaizen-pdp-phases` | kaizen-pdp-foundation | Reference only — no file output |

**Retired / relocated skills:** `solution-design` folded into `technical-design` (D21);
`internal-project-review` folded into `sprint-review` (D25); `insights-summary` folded into
`closeout-archive` (D31); `pursuit-plan` relocated out of the PDP plugins to
`sales-marketing/account-management` (account growth is not a PDP deliverable).

---

## Response Format Guidelines

- For phase overviews: use compact tables (deliverable # | name | mandatory)
- For "what's next": bullet list of 3–5 most important next actions, ordered by priority
- For checklist status: two-table format (deliverables | tasks), leave Complete column blank
- Always end phase guidance with: "Say 'generate [relevant deliverable]' to have Claude produce it."
- Keep answers concise — the EL needs to act, not read essays

---

_Last reviewed: 2026-07-13 (added EL Knowledge Base SharePoint lookup)_
