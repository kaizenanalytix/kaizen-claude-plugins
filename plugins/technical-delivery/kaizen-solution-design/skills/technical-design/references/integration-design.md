# Outline — Integration Design

**Type:** Conditional. Generate when the solution connects multiple external systems, uses
messaging/queues or event streams, or ingests from external sources.
**Output:** `Integration Design.docx` in the `design/` folder.

> If integration is thin (a single external API), the skill may fold this into the API
> Specification instead of producing a separate document.

```
INTEGRATION DESIGN
[Client] [Project] · Version 1.0 · Author: [Tech Lead / Integration Architect] · Date: [today] · Status: Draft

Document Control (Version History; Reviewers)

1. INTRODUCTION
   1.1 Purpose · 1.2 Scope · 1.3 Related documents (BRD, Overview, API Spec, Security, data-model)

2. REQUIREMENTS TRACEABILITY
   [Table: Req ID | Requirement (short) | Integration | Section ref]

3. INTEGRATION LANDSCAPE
   3.1 System context — this solution + every external system it talks to
       (reference the E2E / solution overview diagram; do not redraw it here)
   3.2 Integration inventory [Table: # | External system | Direction (in/out/both) | Pattern | Protocol | Owner]

4. INTEGRATION PATTERNS
   Per integration (4.N): purpose, pattern (sync request/response, async messaging, batch/file,
   event/stream, CDC), protocol & format, endpoint/queue/topic, auth (cross-ref Security),
   data mapping (source ↔ target fields; reference data-model where relevant),
   frequency/volume, ordering/idempotency.

5. RELIABILITY & ERROR HANDLING
   Retries/backoff, dead-letter handling, reconciliation, monitoring hooks
   (cross-ref Infra & Deployment for alerting).

6. SECURITY OF INTEGRATIONS
   Transport security, credential storage, IP allow-lists — authoritative details in Security Design.

7. RISKS & OPEN ITEMS  [Table: ID | Item | Mitigation / [TO CONFIRM] | Priority]
```

**Notes**
- Data movement *diagrams* belong to `dataflow-diagrams`; this is the written contract/design.
- Field-level source-to-target belongs to `data-model` when it's a data build — reference it.
