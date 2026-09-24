# case-study

Creates the **Kaizen Case Study** (**D32, Mandatory**) from the full engagement record — a
reusable, client-approved summary of the project for Kaizen's portfolio. It reads documents
across all phases and generates a branded `.pptx` saved to `6. Deploy`.

## When to use it

Trigger phrases: "create case study", "generate case study", "Kaizen case study",
"D32 case study", "write the case study", "engagement case study", "project case study",
"make the case study".

## Inputs

| Source | Purpose |
|---|---|
| SOW (D10) | Project scope and objectives |
| KT Brief | Client context, solution approach |
| Technical Design (D21) | Architecture and technology |
| Project Close Out (D31) | Key findings and results |
| Project Sign-Off (D30) | Deliverables and acceptance status |
| Proposal (D7) | Original business case and value proposition |

Plus EL input on the approved case-study name, client-approved metrics, testimonials, and
permission level (public / Kaizen-internal / anonymised).

The skill maps synthesised content onto a 5–8 slide deck (Title, The Challenge, Our Approach,
Solution Architecture, Key Results, Client Testimonial, Kaizen Differentiators).

## Integrations

- Shared MCP tools: `read_phase_docs`, `write_deliverable`.
- **kaizen-pptx-template** skill for branded PPTX rendering (falls back to a generic pptx skill
  if unavailable).
- `mcp__cowork__request_cowork_directory` and `mcp__cowork__present_files`.
- Follows shared guardrails **G1–G5**. Metrics are copied verbatim and never computed (**G4**);
  the deck may be shared externally, so it requires explicit EL approval (**G5**).

## See also

- `../project-signoff/README.md` — sign-off (D30) that usually precedes the case study.
- `../closeout-archive/README.md` — suggested next step (D31 closeout and T40 archive).
- `SKILL.md` — full step-by-step workflow, slide mapping, and error handling.
