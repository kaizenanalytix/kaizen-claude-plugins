# support-plan

Drafts the **Support Plan** — a component of the mandatory Deployment/handoff checklist
(**D29**) — for a Kaizen PDP engagement. It reads deployment context and operations notes from
`5. Develop` and `6. Deploy`, then generates a Support Plan `.docx` saved to `6. Deploy`.

The plan defines post-go-live support arrangements, support levels and SLAs, escalation
procedures, the hypercare period, knowledge transfer to operations, monitoring, and post-go-live
change management. SLA fields not yet agreed with the client are left as `[TO CONFIRM]`.

## When to use it

Trigger phrases: "draft support plan", "create support plan", "generate support plan",
"post-go-live support", "hypercare plan", "support plan", "support model",
"write the support plan".

## Inputs

| Source | Purpose |
|---|---|
| Technical Design (D21) | Architecture, monitoring, deployment details, integration points |
| Data Flow Diagrams (D22) | Integration points and data flows to support |
| Training Plan (D24, if generated) | Training status, user readiness |
| SOW (D10) | Contracted support terms, SLAs |

Plus conversational input from the PM/EL: support duration, coverage hours, escalation
contacts, known risks, and the handoff approach.

## Integrations

- Shared MCP tools: `read_phase_docs`, `write_deliverable`.
- `mcp__cowork__request_cowork_directory` (locate the project root) and
  `mcp__cowork__present_files` (present the saved file).
- Follows shared guardrails **G1–G5** from the `guardrails` skill in shared-foundation-plugin.

## See also

- `../project-signoff/README.md` — suggested next step (D30) once SLAs are reviewed.
- `../closeout-archive/README.md` — final closeout that verifies the support plan (T38).
- `SKILL.md` — full step-by-step workflow, document structure, and error handling.
