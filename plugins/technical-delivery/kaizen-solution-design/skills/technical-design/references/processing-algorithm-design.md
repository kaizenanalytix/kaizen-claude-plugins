# Outline — Processing / Algorithm / ML Design

**Type:** Conditional. Generate when the solution has non-trivial processing: models/ML, scoring,
forecasting, optimisation, a rules engine, or substantial batch transformation logic.
**Output:** `Processing & Algorithm Design.docx` in the `design/` folder.

```
PROCESSING / ALGORITHM / ML DESIGN
[Client] [Project] · Version 1.0 · Author: [Data Scientist / Tech Lead] · Date: [today] · Status: Draft

Document Control (Version History; Reviewers)

1. INTRODUCTION
   1.1 Purpose · 1.2 Scope · 1.3 Related documents (BRD, Back-end Design, data-model, dataflow-diagrams)

2. REQUIREMENTS TRACEABILITY
   [Table: Req ID | Requirement (short) | Processing component | Section ref]

3. PROCESSING OVERVIEW
   3.1 Inventory of processing components [Table: Component | Type (rule/ML/transform/opt) | Trigger | I/O]
   3.2 Where each runs (batch/stream/on-request) — reference dataflow-diagrams for the flow picture

4. PER-COMPONENT DESIGN  (4.N for each)
   4.N.1 Purpose & business rule it satisfies
   4.N.2 Inputs / outputs (schemas; reference data model)
   4.N.3 Logic — pseudocode / rules / model approach
   4.N.4 Parameters / thresholds / features (exact where known, else [TO CONFIRM])
   4.N.5 Performance characteristics (complexity, expected runtime/volume)
   4.N.6 Edge cases & error handling

5. MODEL SPECIFICS (ML components only)
   Algorithm family + version, training data & features, target metric, validation approach,
   retraining cadence, drift monitoring (cross-ref Infra & Deployment for the ops hooks),
   explainability/fairness notes if required.

6. VALIDATION & ACCEPTANCE
   How outputs are validated against acceptance criteria (feeds the Test Plan / test-training-plans).

7. RISKS & OPEN ITEMS  [Table: ID | Item | Mitigation / [TO CONFIRM] | Priority]
```

**Notes**
- Keep this to the design of the logic. The data it runs on is defined by `data-model`; the movement
  is drawn by `dataflow-diagrams`. Reference both.
