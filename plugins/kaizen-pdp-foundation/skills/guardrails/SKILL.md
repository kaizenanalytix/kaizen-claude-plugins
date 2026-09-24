---
name: guardrails
description: >
  Reference skill defining the mandatory guardrails and file conventions that every Kaizen PDP
  delivery skill must follow. This skill does not generate documents — it is the single source
  of truth for cross-cutting safety rules and the project folder/file naming standards.
  Other skills reference these guardrails by name (G1–G5) and file conventions (F1–F3) rather
  than restating them.
  Trigger on: "show guardrails", "what are the delivery guardrails", "PDP guardrails",
  "what rules apply to deliverables", "file naming conventions", "PDP folder structure",
  "where do deliverables go".
---

# guardrails Skill

Single source of truth for the mandatory rules and file conventions every Kaizen PDP delivery
skill must follow. This is a REFERENCE skill — it does not generate documents.

---

## Guardrails

### G1 — Version, Never Overwrite

When saving any deliverable to a PDP phase folder:

- **Never overwrite an existing file.** If `<name>.docx` already exists, save as `<name> v2.docx`,
  then `v3`, etc.
- Check for existing files before writing — list the destination folder to check for prior versions.
- The version suffix goes before the extension: `ProjectID - KT Brief v2.docx`, not
  `ProjectID - KT Brief.docx (2)`.
- Version 1 has no suffix — the first save is just `[ProjectID] - [Deliverable Name].ext`.
- If the user explicitly says "overwrite" or "replace", confirm once before proceeding:
  > "This will replace the existing file. Type 'confirm overwrite' to proceed."

---

### G2 — Confirmation Gate Before Writing

Before writing any file to a shared or destination PDP folder:

- Present the proposed filename and destination path in chat.
- Wait for explicit user confirmation ("save it", "yes", "go ahead", "write it") before writing.
- If the skill produces multiple files, list all of them and get a single confirmation.
- **Never auto-save** to a PDP phase folder without the user seeing the proposed output first.

---

### G3 — P3/SOW Numbers Copied Verbatim

When a deliverable includes financial figures, contract values, dates, or reference numbers
sourced from the P3 Project Economics (D5) or SOW (D10):

- **Copy the exact value** from the source document. Do not round, reformat, recalculate, or
  paraphrase.
- If a value is ambiguous or appears in multiple places with different amounts, flag it:
  > "⚠ Conflicting values found for [field]: [value A] in SOW vs [value B] in P3. Please confirm
  > which is correct."
- If a value is missing, mark it as `[NOT SPECIFIED — confirm with sales lead]` — never estimate.

---

### G4 — Deterministic Finance

The LLM must **never compute, derive, estimate, or infer** financial figures. This includes:

- Total Contract Value (TCV)
- Hourly/daily rates
- Gross margin (GM) percentages
- Investment breakdowns or budget allocations
- Payment milestone amounts
- Resource cost calculations
- ROI estimates or projections

All financial figures must come directly from a source document (P3, SOW, proposal) and be
copied verbatim per G3. If a financial figure is needed but not found in source documents,
insert `[NOT SPECIFIED — refer to P3/SOW]`.

**Exception:** Non-financial arithmetic (e.g. counting deliverables, summing sprint weeks,
calculating team size) is permitted.

---

### G5 — EL/PM Approval Before External Actions

Before performing any action that is visible to people outside the current conversation:

- **Jira:** Do not push epics, stories, or sprint plans without explicit EL approval.
- **Email / Slack / Teams:** Do not send messages on behalf of the user without explicit approval.
- **Shared folders:** Writing to a shared PDP folder requires the G2 confirmation gate.
- **Client-facing documents:** Flag any document that will be shared with the client and confirm
  with the EL before finalising.

The approval gate pattern:
```
⏸ Waiting for your approval before [action].
Reply "approved" / "go ahead" to proceed, or "revise" to make changes.
```

---

## File Conventions

### F1 — Project Root Convention

Every Kaizen PDP project has a root folder named:

```
[Client Familiar Name] [Timing] [Project Name]
```

Components (space-separated):
- **Client Familiar Name** — if the client is known by a single name, use it (e.g. `Landmark`,
  `Savers`, `Coolsys`). Otherwise use the agreed abbreviation (e.g. `UDX`, `SP`, `TMNA`).
- **Timing** — the year, expressed as fiscal year, calendar year, quarter, or specific dates
  (e.g. `2025`, `FY26`, `Q3 2026`). If the timing basis is unclear, default to the calendar
  year of the kick-off date.
- **Project Name** — a meaningful representation of the work.

Examples:
- `TMNA FY2027 Trade Vault`
- `Landmark 2025 Data Platform`
- `Coolsys FY26 Inventory Optimization`

The project root is the folder containing the numbered phase subfolders. If a
`.kaizen-project.json` file exists at the root, read the `PROJECT_ID` from it. Otherwise,
use the folder name as the `PROJECT_ID`.

---

### F2 — Phase Folder Structure

The project root contains these numbered phase folders:

| Folder | PDP Phase | Deliverables |
|---|---|---|
| `0. Sales Alignment/` | Phase 0: Sales Alignment (through SOW) | D1–D10 |
| `1. Sales Handoff & Transition/` | Phase 1: Sales Handoff & Transition (after SOW) | D11–D13 |
| `2. Plan/` | Phase 2: Plan | D14–D17 |
| `3. Analyze/` | Phase 3: Analyze | D18–D20 |
| `4. Design/` | Phase 4: Design | D21–D24 |
| `5. Develop/` | Phase 5: Develop | D25–D28 |
| `6. Deploy/` | Phase 6: Deploy | D29–D32 |
| `7. Project Governance/` | Phase 7: Project Governance | D33–D37 |
| `8. Quality/` | Phase 8: Quality | D38–D41 |

Skills read inputs from earlier phase folders and write outputs to the phase folder
matching their deliverable ID.

---

### F3 — File Naming Convention

All deliverables follow this naming pattern:

```
[ProjectID] - [Deliverable Name].ext
```

Examples:
- `TMNA FY2027 Trade Vault - KT Brief.docx`
- `TMNA FY2027 Trade Vault - Internal Kickoff.pptx`
- `TMNA FY2027 Trade Vault - RAID Log.xlsx`
- `TMNA FY2027 Trade Vault - Solution Design.docx`

If `PROJECT_ID` is not known, fall back to `[Client Familiar Name] [Project Name]` format.

Versioning follows G1: first save has no suffix, subsequent saves append `v2`, `v3`, etc.

---

## Reading Files from Phase Folders

### Locating the project root

1. If a workspace folder is connected, check if it follows the `[Client Familiar Name] [Timing] [Project Name]`
   convention and contains numbered phase folders.
2. If `.kaizen-project.json` exists, read `PROJECT_ID` from it.
3. If ambiguous, ask the user to confirm the project root path.

### Reading input documents

Use the file tools (Read, Glob, Bash) to locate and read files from phase folders:

```bash
# List all files in a phase folder
find "<PROJECT_ROOT>/<Phase Folder>/" -type f | sort

# Or use Glob to find specific file types
Glob pattern: "<PROJECT_ROOT>/<Phase Folder>/**/*.docx"
```

### Handling unreadable files

If a file cannot be read (empty content, corrupt, or cloud-only stub):
1. Report it to the user: "Could not read [filename]. Please ensure the file is available locally."
2. Never silently skip unreadable files — always surface what was skipped and why.

---

## Writing Deliverables to Phase Folders

### Pre-write checklist (G1 + G2)

1. **Confirm destination:** Present the full path to the user.
2. **Check for existing versions:** List the destination folder for files matching the deliverable name.
3. **Determine version number:** If prior versions exist, increment per G1.
4. **Wait for confirmation:** Do not write until the user approves per G2.

### Post-write

After writing, confirm in chat:
```
Saved: <Phase Folder>/<filename>
```

Present the written file to the user via `mcp__cowork__present_files`.

---

## How Skills Reference These Rules

Skills must NOT restate these rules. Instead, include a one-line reference:

```
> **Guardrails:** This skill follows the shared guardrails (G1–G5) and file conventions (F1–F3)
> defined in the `guardrails` skill of kaizen-pdp-foundation. See that skill for versioning,
> confirmation gates, verbatim financial data, deterministic finance, approval gates, folder
> structure, and file naming rules.
```

If a skill needs to add specific behaviour (e.g. the kickoff deck's "No Economics" rule),
it should state the additional constraint and reference the underlying guardrail:

```
> Per G4 (Deterministic Finance): this deck excludes ALL financial data. Skip P3 content entirely.
```

---

## Error Handling

| Situation | Action |
|---|---|
| Project root not found | Ask user to confirm the workspace path |
| Phase folder does not exist | Ask user to create it or confirm the project structure |
| Existing file found at destination | Apply G1 — save as next version (v2, v3, ...) |
| User says "just save it" without seeing output | Apply G2 — show the output summary first, then save |
| Financial figure not in source docs | Apply G3/G4 — insert placeholder, never estimate |
| Action would affect external system | Apply G5 — present approval gate and wait |
| File cannot be read | Report to user with remediation steps, never skip silently |
| PROJECT_ID unknown | Ask user or fall back to `[Client Familiar Name] [Project Name]` |
| User explicitly requests overriding a guardrail | Comply but log a warning in the chat summary |

---

_Last reviewed: 2026-07-07_
