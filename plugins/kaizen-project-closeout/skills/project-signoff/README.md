# project-signoff

Prepares the **Project Sign-Off** document (**D30, Mandatory**) for formal client acceptance of
the delivered solution. It reads the acceptance criteria and deliverables record across all
phases, then generates a Sign-Off `.docx` saved to `6. Deploy`.

The document records what was delivered against what was contracted, acceptance-criteria status,
change requests, known issues, outstanding items, and formal sign-off signature blocks for
Kaizen and the client.

## When to use it

Trigger phrases: "prepare project sign-off", "generate sign-off", "project sign-off document",
"client sign-off", "D30 sign-off", "create the sign-off", "project acceptance",
"generate project sign-off".

## Inputs

- A full inventory of every phase folder (`0.`–`6.`) to build the deliverables register.
- SOW (D10) — contracted scope and acceptance criteria (**copied verbatim per G3**).
- BRD (D18) — requirements with acceptance criteria.
- Test results / UAT sign-off, where documented.

## Integrations

- Shared MCP tools: `read_phase_docs`, `write_deliverable`.
- `mcp__cowork__request_cowork_directory` and `mcp__cowork__present_files`.
- Follows shared guardrails **G1–G5** from the `guardrails` skill in shared-foundation-plugin.
  This is a client-facing document requiring explicit EL approval before sharing (**G5**).

## See also

- `../support-plan/README.md` — the support plan (D29) that typically precedes sign-off.
- `../case-study/README.md` — suggested next step (D32) after sign-off.
- `../closeout-archive/README.md` — final closeout (D31); warns if D30 is missing.
- `SKILL.md` — full step-by-step workflow, document structure, and error handling.
