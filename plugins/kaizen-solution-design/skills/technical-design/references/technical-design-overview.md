# Outline — Technical Design Overview

**Type:** Universal (always generated). The parent/index document for the design set.
**Output:** `Technical Design Overview.docx` in the `design/` folder.
**Role:** Short, skimmable summary that links every child document and rolls up traceability.
Keep the substantive detail in the child docs — this doc orients the reader, it does not duplicate.

```
TECHNICAL DESIGN OVERVIEW
[Client Familiar Name] [Timing] [Project Name]
Version: 1.0 · Author: [Tech Lead / Architect] · Date: [today] · Status: Draft

────────────────────────────────────
Document Control
  Version History: Version | Date | Author | Changes
  Reviewers: Name | Role | Review Date

1. INTRODUCTION
   1.1 Purpose
   1.2 Scope (reference the BRD)
   1.3 How to read this set — the list of design documents that make up the package

2. DESIGN DOCUMENT INDEX
   [Table: Document | Owner (role) | Status | File]
   One row per document actually generated (universal + confirmed conditional) and
   per delegated deliverable, with a link/path. Delegated rows point to data-model /
   dataflow-diagrams / e2e-diagrams output.

3. ARCHITECTURE SUMMARY
   3.1 Solution context (one paragraph + reference to the E2E / solution overview diagram)
   3.2 Component map [Table: Component | Responsibility | Owning design doc | Technology]
   3.3 Technology Stack [Table: Layer | Technology | Version (exact) | Purpose]

4. CROSS-CUTTING CONCERNS
   Brief pointers (1–2 lines each) to where each is fully specified:
   security → Security Design; scaling/monitoring → Infra & Deployment Design;
   data → data-model; error handling → Back-end Design.

5. REQUIREMENTS TRACEABILITY (ROLLED-UP)
   [Table: Req ID | Requirement (short) | Addressed in document(s) | Status]
   Every FR-###/NFR-### from the BRD. Any requirement with no design element →
   flag [GAP — no design element].

6. DESIGN DECISIONS REGISTER
   The architect's answers from the Step 3 Deciding-Factor Interview — the single source of
   truth every child document draws its technology/approach statements from.
   [Table: ID | Decision | Chosen value | Source (architect / technical checklist / SOW) | Rationale | Status]
   Deferred decisions appear here as [TO CONFIRM] with an owner.

7. APPENDICES / REFERENCE DOCUMENTS
```

**Notes**
- Section 5 is the value of this doc — it's the single place to see whether the design covers the
  requirements. Build it by unioning the per-document traceability tables.
- Section 2 must reflect what was actually generated in this run, plus the delegated pointers.
