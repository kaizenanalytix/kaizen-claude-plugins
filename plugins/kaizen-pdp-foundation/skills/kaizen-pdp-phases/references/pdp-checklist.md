# Kaizen PDP Project Checklist v2 — Machine-Readable Reference

Aligned to **PDP Deliverables (June 22 2026)**. The sheet's single "1. Sales Handoff &
Transition" step is split into **0. Sales Alignment** (through SOW) and **1. Sales Handoff &
Transition** (after SOW). Mandatory flags follow the sheet's "Mandatory" column.

Project naming convention: [Client Familiar Name] [Timing] [Project Name]

## Engagement-Type Applicability

Whether a deliverable is mandatory depends on the **engagement type**. The per-phase tables below
use the baseline **Deliverable-based** column (identical to the sheet's "Mandatory" column). The
matrix below carries all four engagement types from `PDP Deliverables June222026.xlsx`; the
`project-onboarding` script encodes the same matrix in `PHASES` and lets `--engagement-type` pick
which column drives the Report Card's Mandatory flags and gate math.

Legend: **DB** = Deliverable-based, **Pod** = Capability Pod, **MA** = Managed Analytics & Support
Services, **GCC** = GCC Engagements.

| ID | Deliverable | DB | Pod | MA | GCC |
|---|---|---|---|---|---|
| D1 | NDA | Y | Y | Y | Y |
| D2 | Opportunity summary | Y | Y | Y | Y |
| D3 | Project scope & estimation summary | N | N | N | N |
| D4 | High-level solution overview diagram | Y | Y | Y | Y |
| D5 | P3 Project Economics | Y | Y | Y | Y |
| D6 | Deal review committee submission | N | N | N | N |
| D7 | Client proposal | Y | Y | Y | Y |
| D8 | Data request document | N | N | N | N |
| D9 | MSA | Y | Y | Y | Y |
| D10 | SOW | Y | Y | Y | Y |
| D11 | Internal Kickoff PPT | Y | Y | Y | Y |
| D12 | Project Charter | N | N | N | N |
| D13 | Project technical checklist | Y | N | Y | Y |
| D14 | Enter User stories in JIRA | N | N | N | N |
| D15 | Kickoff document and minutes | Y | Y | Y | Y |
| D16 | Status Report | Y | Y | Y | Y |
| D17 | Project Plan/WBS | Y | N | Y | Y |
| D18 | Business Requirements, with sign off | Y | N | Y | Y |
| D19 | Validated Data Set | Y | N | N | N |
| D20 | Change Request Template | Y | Y | Y | Y |
| D21 | Technical Design | Y | N | N | N |
| D22 | End to End Flows and Data Flow Diagrams | Y | N | N | N |
| D23 | Test Plans | Y | N | N | N |
| D24 | Training Plans | Y | N | N | N |
| D25 | Sprint Log | Y | N | N | N |
| D26 | Issue Log | Y | N | N | Y |
| D27 | Definition of done | Y | N | N | N |
| D28 | Testing sign off | Y | N | N | N |
| D29 | Deployment/handoff checklist | Y | N | Y | Y |
| D30 | Project Sign Off | Y | Y | Y | Y |
| D31 | Project Close Out | Y | Y | Y | Y |
| D32 | Kaizen Case Study | Y | Y | Y | Y |
| D33 | RAID Log | Y | Y | Y | Y |
| D34 | RACI Chart | Y | N | Y | Y |
| D35 | Value Tracker | Y | Y | Y | Y |
| D36 | Business Continuity Plan (BCP) | Y | Y | Y | Y |
| D37 | Updated project governance scorecard | Y | Y | Y | Y |
| D38 | Customer Satisfaction Survey (CSAT) | Y | Y | Y | Y |
| D39 | Quality Plan | N | N | N | N |
| D40 | Project Metrics | N | N | N | N |
| D41 | Risk assessment Sheet | N | N | N | N |

---

## Sales Alignment (Phase 0) — Folder: 0. Sales Alignment

### Deliverables
| # | Name | Mandatory |
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

### Tasks
| # | Name | Mandatory |
|---|---|---|
| T1 | Project scoping and estimations | Y |
| T2 | Review case studies for proposal | N |
| T3 | Review Useful PPT Slides & Graphics | N |
| T4 | Draft & send data request document | Y |
| T5 | Agree dates for data procurement | Y |
| T6 | Draft SOW | Y |
| T7 | Build P3 economics | Y |
| T8 | Deal review committee meeting | Y |
| T9 | Update Ruddr | Y |

---

## Sales Handoff and Transition (Phase 1) — Folder: 1. Sales Handoff & Transition

### Deliverables
| # | Name | Mandatory |
|---|---|---|
| D11 | Internal Kickoff PPT | Y |
| D12 | Project Charter | N |
| D13 | Project technical checklist | Y |

### Tasks
| # | Name | Mandatory |
|---|---|---|
| T10 | Sales knowledge transfer to delivery team | Y |
| T11 | Jira Set Up | Y |
| T12 | Receive Data samples | N |
| T13 | Identify team members | Y |
| T14 | Review Agile Best Practices Guidelines | N |
| T15 | Draft Kickoff PPT | Y |
| T16 | Complete Internal Kickoff w/ Project team | Y |

---

## Plan (Phase 2) — Folder: 2. Plan

### Deliverables
| # | Name | Mandatory |
|---|---|---|
| D14 | Enter User stories in JIRA | N |
| D15 | Kickoff document and minutes | Y |
| D16 | Status Report | Y |
| D17 | Project Plan/WBS | Y |

### Tasks
| # | Name | Mandatory |
|---|---|---|
| T18 | Environment set up and access | Y |
| T19 | Review Agile Story Guidelines | N |
| T20 | Review Alteryx Guidelines (as applicable) | N |
| T21 | Kickoff Meeting | Y |
| T22 | Project Governance Sign Off | N |
| T23 | Agree Project Plans | Y |

---

## Analyze (Phase 3) — Folder: 3. Analyze

### Deliverables
| # | Name | Mandatory |
|---|---|---|
| D18 | Business Requirements, with sign off | Y |
| D19 | Validated Data Set | Y |
| D20 | Change Request Template | Y |

### Tasks
| # | Name | Mandatory |
|---|---|---|
| T24 | Requirements Signoff | N |
| T25 | Data Validation Signoff | N |
| T26 | Draft Technical Design | Y |

---

## Design (Phase 4) — Folder: 4. Design

### Deliverables
| # | Name | Mandatory |
|---|---|---|
| D21 | Technical Design | Y |
| D22 | End to End Flows and Data Flow Diagrams | Y |
| D23 | Test Plans | Y |
| D24 | Training Plans | Y |

### Tasks
| # | Name | Mandatory |
|---|---|---|
| T27 | Produce detailed Solution Overview diagram | N |
| T28 | Draft Test Plans | Y |
| T29 | Draft Training Plans | Y |

---

## Develop (Phase 5) — Folder: 5. Develop

### Deliverables
| # | Name | Mandatory |
|---|---|---|
| D25 | Sprint Log | Y |
| D26 | Issue Log | Y |
| D27 | Definition of done | Y |
| D28 | Testing sign off | Y |

### Tasks
| # | Name | Mandatory |
|---|---|---|
| T30 | Solution Development & Calibration | Y |
| T31 | Unit, integration and user testing | Y |
| T32 | Conduct sprint / milestone review | Y |
| T33 | Monthly Kaizen Project Review | Y |
| T34 | Training preparation | N |

---

## Deploy (Phase 6) — Folder: 6. Deploy

### Deliverables
| # | Name | Mandatory |
|---|---|---|
| D29 | Deployment/handoff checklist | Y |
| D30 | Project Sign Off | Y |
| D31 | Project Close Out | Y |
| D32 | Kaizen Case Study | Y |

> The Deployment/handoff checklist (D29) may bundle the Final Design Document, Training
> Documents, and Support Plan as components, per the sheet's note.

### Tasks
| # | Name | Mandatory |
|---|---|---|
| T36 | User Training | N |
| T37 | Deploy Solution | Y |
| T38 | Review support plan | Y |
| T39 | Project Retrospective | N |
| T40 | Archive all project deliverables | Y |

---

## Project Governance (Phase 7) — Folder: 7. Project Governance

### Deliverables
| # | Name | Mandatory |
|---|---|---|
| D33 | RAID Log | Y |
| D34 | RACI Chart | Y |
| D35 | Value Tracker | Y |
| D36 | Business Continuity Plan (BCP) | Y |
| D37 | Updated project governance scorecard | Y |

Cross-phase governance artifacts; keep current at all times across phases 0–6 (Teams/Confluence
site, RAID log, RACI chart, Business Continuity Plan, value tracker, end-to-end diagram, system
architecture diagram, governance scorecard, case study).

---

## Quality (Phase 8) — Folder: 8. Quality

### Deliverables
| # | Name | Mandatory |
|---|---|---|
| D38 | Customer Satisfaction Survey (CSAT) | Y |
| D39 | Quality Plan | N |
| D40 | Project Metrics | N |
| D41 | Risk assessment Sheet | N |

---

## Summary Counts

| Phase | Total Deliverables | Mandatory | Total Tasks | Mandatory |
|---|---|---|---|---|
| Sales Alignment | 10 | 7 | 9 | 7 |
| Sales Handoff & Transition | 3 | 2 | 7 | 5 |
| Plan | 4 | 3 | 6 | 3 |
| Analyze | 3 | 3 | 3 | 1 |
| Design | 4 | 4 | 3 | 2 |
| Develop | 4 | 4 | 5 | 4 |
| Deploy | 4 | 4 | 5 | 3 |
| Project Governance | 5 | 5 | — | — |
| Quality | 4 | 1 | — | — |
| **Total** | **41** | **33** | **38** | **25** |
