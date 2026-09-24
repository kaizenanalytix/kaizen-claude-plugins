# Solution Design

**Version 2.0.0** · Kaizen Analytix LLC

Helps delivery teams work through the **Analyze & Design** phase of an engagement: capturing
business requirements, drafting the technical design, modelling data, producing the standard
diagram set, and packaging it all for the build team.

## Skills

| Skill | What it does |
|---|---|
| `business-requirements` | Drafts the Business Requirements Document (`.docx`) from the kickoff deck, KT brief and planning docs. |
| `technical-design` | Interviews the architect on the deciding factors, then writes a set of design docs (overview, back-end, security, infrastructure, plus front-end / API / integration / processing when they apply). |
| `data-model` | Conceptual, logical, physical or dimensional models: ERD (`.drawio` + PNG), DBML, runnable DDL and a data dictionary (`.xlsx`). Also reverse-engineers existing schemas. |
| `e2e-diagrams` | The Kaizen End-to-End Solution Overview diagram, filled from the bundled draw.io templates. |
| `dataflow-diagrams` | End-to-end and data flow diagrams from the technical design. |
| `api-sequence-diagram` | A UML-style sequence diagram for one API flow. |
| `tech-architecture-diagram` | A tiered technical architecture diagram with tech-stack iconography. |
| `design-handoff` | Converts the design docs and data model into a `docs/` folder of Markdown with a root `CLAUDE.md`, ready for a build team or the full-stack plugins. |

## Typical flow

`business-requirements` → `technical-design` → `data-model` → diagrams → `design-handoff`

The handoff package is designed to be consumed by the [full-stack engineering plugins](../../docs/full-stack-guide.md).

## How it fits the Kaizen PDP

Follows the guardrails and file conventions defined in
[`kaizen-pdp-foundation`](../kaizen-pdp-foundation/README.md) and writes into the phase folders it
creates. Install both.
