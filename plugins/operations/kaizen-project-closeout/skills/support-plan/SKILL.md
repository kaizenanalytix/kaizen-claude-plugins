---
name: support-plan
description: >
  Use this skill when the PM or EL wants to draft the Support Plan — a component of the
  Deployment/handoff checklist (D29) — for a Kaizen PDP engagement.
  Trigger on: "draft support plan", "create support plan", "generate support plan",
  "post-go-live support", "hypercare plan", "support plan", "support model",
  "write the support plan".
  This skill reads the deployment context and operations notes from "5. Develop" and
  "6. Deploy", generates a Support Plan document (.docx), and saves it to "6. Deploy".
---

# support-plan Skill

Generate the Support Plan defining post-go-live support arrangements, escalation procedures, and
transition to steady-state operations. Per the PDP sheet, the Support Plan is one component of
the mandatory Deployment/handoff checklist (D29). Output: a .docx saved to `6. Deploy`.

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

## Step 1 — Gather Support Context

### 1.1 From Project Documents
```bash
find "<PROJECT_ROOT>/5. Develop/" -type f | sort
find "<PROJECT_ROOT>/6. Deploy/" -type f | sort
find "<PROJECT_ROOT>/4. Design/" -name "*Technical*" | sort
```

| Source | Purpose |
|---|---|
| Technical Design (D21) | System architecture, monitoring, deployment details, integration points |
| Data Flow Diagrams (D22) | Integration points and data flows to support |
| Training Plan (D24, if generated) | Training status, user readiness |
| SOW (D10) | Contracted support terms, SLAs |

### 1.2 From the PM/EL (conversational input)
- Agreed support duration (hypercare period)
- Support hours and coverage (business hours / 24x7)
- Escalation contacts at Kaizen and client
- Known post-go-live risks
- Handoff approach (to client IT, to managed services, retained Kaizen support)

---

## Step 2 — Populate Support Plan Content

### 2.1 Support Overview
- Support scope: what is covered vs not covered
- Support duration: hypercare period + ongoing support (if any)
- Support model: Kaizen-managed / client-managed / shared / transitional

### 2.2 Support Levels

| Level | Description | Response Time | Resolution Time | Handled By |
|---|---|---|---|---|
| L1 | User queries, how-to questions | [TO CONFIRM] | [TO CONFIRM] | Client helpdesk / power users |
| L2 | Configuration, data issues, minor bugs | [TO CONFIRM] | [TO CONFIRM] | Client IT / Kaizen support |
| L3 | Architecture, complex bugs, enhancements | [TO CONFIRM] | [TO CONFIRM] | Kaizen engineering |

[TO CONFIRM] — SLA response/resolution times should be agreed with the client and aligned with
any contractual SLAs in the SOW.

### 2.3 Escalation Procedure

| Step | Action | Contact | Timeframe |
|---|---|---|---|
| 1 | Log issue in [TO CONFIRM — ticketing system] | End user | Immediate |
| 2 | L1 triage and attempt resolution | [Client helpdesk contact] | Within SLA |
| 3 | Escalate to L2 if unresolved | [Client IT / Kaizen contact] | Per SLA |
| 4 | Escalate to L3 if unresolved | [Kaizen Tech Lead] | Per SLA |
| 5 | Executive escalation | [Kaizen EL] ↔ [Client Sponsor] | As needed |

### 2.4 Hypercare Period
- Duration: [TO CONFIRM — typically 2–4 weeks post go-live]
- Scope: enhanced monitoring, rapid response, on-site / on-call availability
- Staffing: team members and availability during hypercare
- Exit criteria: conditions for ending hypercare and transitioning to BAU support

### 2.5 Knowledge Transfer to Operations
- Documentation to be handed over (admin guides, runbooks, FAQs)
- Training for client support team (reference D24 Training Plan)
- Access and credential transfer
- Monitoring and alerting handover

### 2.6 Monitoring & Alerting
- Key metrics to monitor post-go-live
- Alerting thresholds and channels
- Dashboard access for operations team
- Health check procedures

### 2.7 Change Management (post go-live)
- How to request enhancements or changes
- Minor fix vs change request threshold
- Release management approach for updates

---

## Step 3 — Generate the Support Plan (.docx)

Produce a .docx with this structure:

```
SUPPORT PLAN
[Client Familiar Name] [Timing] [Project Name]
Version: 1.0
Author: [PM Name]
Date: [today's date]
Status: Draft

────────────────────────────────────
Document Control
  Version History: Version | Date | Author | Changes

1. SUPPORT OVERVIEW
   1.1 Scope of Support
   1.2 Support Duration & Model
   1.3 Support Hours

2. SUPPORT LEVELS & SLAs
   [Table: Level | Description | Response Time | Resolution Time | Handled By]

3. ESCALATION PROCEDURE
   [Table: Step | Action | Contact | Timeframe]
   Escalation diagram (if applicable)

4. HYPERCARE PERIOD
   4.1 Duration and Scope
   4.2 Staffing
   4.3 Exit Criteria

5. KNOWLEDGE TRANSFER TO OPERATIONS
   5.1 Documentation Inventory
     [Table: Document | Type | Location | Status]
   5.2 Training Requirements
   5.3 Access & Credential Transfer

6. MONITORING & ALERTING
   [Table: Metric | Threshold | Alert Channel | Responsible]

7. POST-GO-LIVE CHANGE MANAGEMENT
   7.1 Enhancement Requests
   7.2 Minor Fixes
   7.3 Release Schedule

8. CONTACTS
   [Table: Role | Name | Email | Phone | Availability]

9. APPENDICES
   - Runbook references
   - FAQ
```

### Formatting rules
- Table header rows: Kaizen navy `#0A2342`, white text
- SLA fields: `[TO CONFIRM]` if not yet agreed with client
- Hypercare exit criteria: bold, clearly defined

---

## Step 4 — Save the Output

Present the proposed file to the user (per guardrail G2):
```
Proposed file:
  <PROJECT_ROOT>/6. Deploy/<PROJECT_ID> - Support Plan.docx

Reply "save" to write this file, or "revise" to make changes.
```

Check for existing versions (per guardrail G1).

After saving, present the file using `mcp__cowork__present_files`.

---

## Step 5 — Summary in Chat

```
✅ Support Plan generated: 6. Deploy/<PROJECT_ID> - Support Plan.docx

Support plan summary:
  • Support model: [Kaizen-managed / Client-managed / Shared]
  • Hypercare period: [duration]
  • Support levels defined: L1, L2, L3
  • Escalation contacts: N

Items requiring agreement with client:
  • [list all [TO CONFIRM] items — SLAs, hypercare duration, contacts]

Suggested next: Review SLAs with the client. Say "prepare project sign-off" to produce D30.
```

---

## Error Handling

| Situation | Action |
|---|---|
| No deployment context available | Ask PM/EL for support requirements verbally |
| SLAs not defined in SOW | Insert `[TO CONFIRM]` for all SLA fields |
| Support model unclear | Default to transitional (Kaizen → client); confirm with EL |
| A source file is a cloud-only stub | Note it, continue; advise user (see m365-file-ops) |
| Project root ambiguous | Ask user to confirm path |

---

_Last reviewed: 2026-07-07_
