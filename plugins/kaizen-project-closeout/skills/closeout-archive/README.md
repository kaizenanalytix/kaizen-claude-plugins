# closeout-archive

Generates the **Project Closeout** document (**D31, Mandatory**) and triggers archival of all
project deliverables (**T40, Mandatory**). This is the final PDP skill — it closes the project
lifecycle. The closeout incorporates the project insights summary (key findings and results)
directly, so there is no separate insights deliverable. Output: a `.docx` saved to `6. Deploy`,
plus archived deliverables.

## When to use it

Trigger phrases: "project closeout", "close the project", "archive deliverables",
"generate closeout", "D31 closeout", "T40 archive", "close out the project",
"project closeout and archive", "finalise the project".

## Pre-closeout gate

Before generating the document, the skill verifies the required Deploy-phase items exist and
warns if any are outstanding:

- D29 Deployment/handoff checklist, D30 Project Sign-Off, D32 Case Study (in `6. Deploy/`)
- T37 Solution deployed, T38 Support plan reviewed

## Document contents

Project summary, scope/variance analysis, full deliverables register across all phases, timeline
summary, RAID log final status, lessons learned, post-project commitments, knowledge artefacts,
and a sign-off block. Financial close-out figures are excluded (**G4**; handled outside PDP via
P3 economics and Ruddr).

## Integrations

- Shared MCP tools: `read_phase_docs`, `write_deliverable`, and `archive_deliverables` (T40).
  If `archive_deliverables` is unavailable, a manual archive checklist is presented instead.
- `mcp__cowork__request_cowork_directory` and `mcp__cowork__present_files`.
- Follows shared guardrails **G1–G5**. Archiving is confirmed with the PM/EL before proceeding
  as it can be irreversible (**G5**).

## See also

- `../project-signoff/README.md` — D30 sign-off checked at the pre-closeout gate.
- `../case-study/README.md` — D32 case study checked at the pre-closeout gate.
- `../support-plan/README.md` — D29 support plan reviewed (T38) before closeout.
- `SKILL.md` — full step-by-step workflow, archive checklist, and error handling.
