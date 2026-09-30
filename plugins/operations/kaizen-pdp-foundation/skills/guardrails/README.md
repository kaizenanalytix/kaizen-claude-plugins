# guardrails

The single source of truth for the mandatory guardrails (**G1–G5**) and file conventions
(**F1–F3**) that every Kaizen PDP delivery skill must follow. This is a **reference** skill — it
does not generate documents. Other skills cite these rules by name rather than restating them.

## When to use it

Trigger phrases:

- "show guardrails" / "what are the delivery guardrails" / "PDP guardrails"
- "what rules apply to deliverables"
- "file naming conventions" / "PDP folder structure" / "where do deliverables go"

## Guardrails at a glance

| ID | Rule | In one line |
|---|---|---|
| G1 | Version, Never Overwrite | Save `v2`, `v3`, … — never clobber an existing deliverable |
| G2 | Confirmation Gate Before Writing | Show proposed filename + path and wait for explicit approval |
| G3 | P3/SOW Numbers Copied Verbatim | Copy financial figures exactly; flag conflicts, never round or paraphrase |
| G4 | Deterministic Finance | The LLM never computes/estimates financial figures — they come from source docs |
| G5 | EL/PM Approval Before External Actions | Get EL/PM approval before Jira, email/Slack/Teams, shared folders, client-facing docs |

## File conventions at a glance

| ID | Convention | In one line |
|---|---|---|
| F1 | Project Root | `[Client Familiar Name] [Timing] [Project Name]`; `PROJECT_ID` from `.kaizen-project.json` or the folder name |
| F2 | Phase Folder Structure | Numbered phase folders `0.`–`8.` mapping to deliverable ranges D1–D41 |
| F3 | File Naming | `[ProjectID] - [Deliverable Name].ext`; versioning follows G1 |

The SKILL.md also documents how to read inputs from and write outputs to phase folders
(pre-write checklist, post-write confirmation) and the error-handling matrix.

## How other skills reference these rules

Skills must not restate the rules. They include a one-line reference such as:

```
> **Guardrails:** This skill follows the shared guardrails (G1–G5) and file conventions (F1–F3)
> defined in the `guardrails` skill of kaizen-pdp-foundation.
```

Skill-specific constraints (e.g. "this deck excludes all financial data") should state the extra
rule and cite the underlying guardrail (e.g. G4).

## See also

- `SKILL.md` — the full text of every guardrail, file convention, and error-handling rule.
- `../kaizen-pdp-phases` — the phase/deliverable reference the F2/F3 conventions map onto.
- `../project-onboarding` — creates and enforces the F2 folder structure on disk.
