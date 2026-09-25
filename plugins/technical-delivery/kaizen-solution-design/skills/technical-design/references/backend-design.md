# Outline — Back-end / Application Design

**Type:** Universal (always generated). The server/application build blueprint.
**Output:** `Back-end Design.docx` in the `design/` folder.

```
BACK-END / APPLICATION DESIGN
[Client] [Project] · Version 1.0 · Author: [Tech Lead] · Date: [today] · Status: Draft

Document Control (Version History; Reviewers)

1. INTRODUCTION
   1.1 Purpose · 1.2 Scope · 1.3 Related documents (BRD, Overview, API Spec, data-model, Security)

2. REQUIREMENTS TRACEABILITY
   [Table: Req ID | Requirement (short) | Service / module / logic | Section ref]

3. APPLICATION ARCHITECTURE
   3.1 Architectural style (monolith / modular / microservices / serverless) + why
   3.2 Service / module breakdown [Table: Module | Responsibility | Technology (version) | Dependencies]
   3.3 Repository structure
   3.4 Configuration & dependency management

4. INTERNAL COMPONENT DESIGN
   For each key module: responsibilities, inputs/outputs, collaborators, error handling.

5. DATA ACCESS (alignment layer — not the data model)
   How the back-end reads/writes the data model produced by the `data-model` skill:
   access pattern (ORM/query), transaction boundaries, connection/pooling.
   [Table: Entity/Table (from data model) | Accessed by | Operations | Notes]
   Do NOT define the schema here — reference the data model.

6. BUSINESS LOGIC & WORKFLOWS
   Core workflows as steps/pseudocode; validation rules; idempotency where relevant.
   (Heavy algorithmic/ML logic goes in the Processing/Algorithm doc if that was generated.)

7. ERROR HANDLING, LOGGING & RESILIENCE
   Error taxonomy, ret/retry/backoff, circuit breakers, structured logging, correlation IDs.

8. NON-FUNCTIONAL IMPLEMENTATION
   How back-end meets performance/scalability/availability NFRs (cross-ref Infra & Deployment).

9. RISKS & TECHNICAL DEBT  [Table: ID | Item | Type (Risk/Debt) | Mitigation | Priority]
```

**Notes**
- Section 5 is a deliberate seam: this doc consumes the data model, it never defines tables.
- If APIs exist, endpoint contracts live in the API Specification doc — reference, don't duplicate.
