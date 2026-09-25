---
name: generate-report-card
description: >
  Scans an already-onboarded Kaizen PDP project (the numbered phase folders on disk) and
  (re)generates the Project Report Card — a Dashboard of per-phase completion plus the
  full D1–D41 Deliverables tracker. Use for an up-to-date read on project status without
  redoing onboarding. Trigger on: "refresh/regenerate/update the report card", "rescan
  the project", "scan the project folders", "how compliant is this project", "status
  snapshot", "check deliverable completion", "what's missing", "project health check",
  "is this project up to date". Fast, read-only re-scan — never moves, renames, deletes,
  or creates files or phase folders. If the project isn't onboarded yet (no numbered
  phase folders) or the user wants folders scaffolded or files reorganised, use
  `project-onboarding` instead — it handles first-time setup and brownfield reorg and
  builds the first Report Card. This skill runs standalone on every re-scan after that.
---

# generate-report-card Skill

A lightweight, read-only companion to `project-onboarding`. That skill *sets up* the PDP
structure and builds the first Report Card; this skill *re-scans* an already-compliant (or
mostly-compliant) project and refreshes the Report Card to match what's actually on disk —
with no folder creation, no file moves, and no reorganisation workflow to walk through.

> **Guardrails:** This skill follows the shared guardrails (G1–G5) and file conventions
> (F1–F3) defined in the `guardrails` skill of kaizen-pdp-foundation — see that skill for
> the folder structure and file naming convention this scan relies on. One deliberate
> exception to G1: the Report Card itself is a tool-generated tracker, not a client
> deliverable, so it is refreshed in place on every run rather than versioned — this
> matches how `project-onboarding` already treats it.

All scanning and Excel generation is done by `scripts/generate_report_card.py`. It has no
dependency on `project-onboarding/scripts/pdp_onboard.py` — it encodes the D1–D41 taxonomy
itself. **You** (the model) only need to resolve three inputs and hand them to the script;
never hand-build the Excel yourself.

---

## Step 0 — Resolve inputs

1. **Project root.** The folder that should contain the numbered phase folders (`0. Sales
   Alignment/` … `8. Quality/`). If a workspace folder is connected, use it; if ambiguous,
   ask the user to confirm the path.
2. **Project ID (F1).** Read `.kaizen-project.json` (`PROJECT_ID`) if present at the root;
   otherwise the script falls back to the root folder name automatically — you don't need
   to ask unless the folder name clearly isn't a real project ID.
3. **Engagement type.** Drives which deliverables count as mandatory. Read
   `.kaizen-project.json` (`engagement_type`) if present. If it's missing, **ask the
   user** — one of `deliverable-based` (default), `capability-pod`, `managed-analytics`,
   `gcc`. Don't silently assume; if they don't know, default to `deliverable-based` and
   say so.

You don't need to pre-check whether the phase folders exist — the script handles a
partially- or non-compliant root gracefully (see Step 2).

---

## Step 1 — Run the scan

```bash
python "<SKILL_DIR>/scripts/generate_report_card.py" --root "<PROJECT_ROOT>" \
  --engagement-type "<deliverable-based|capability-pod|managed-analytics|gcc>"
```

Add `--project-id "<ID>"` if you resolved one explicitly in Step 0 rather than letting the
script infer it. Add `--out "<path>"` only if the user wants the file written somewhere
other than the default.

The script:
- Walks each of the 9 phase folders (recursively) that actually exist — it does **not**
  create any that are missing.
- Matches files it finds to deliverables by exact F3 filename, then by a conservative
  "all significant words of the deliverable name appear in the filename" fallback (e.g. a
  file named `Weekly Status Report wk10.xlsx` matches the Status Report deliverable).
  Files it can't confidently match are left unclassified — never guessed.
- Writes the Report Card to `<PROJECT_ROOT>/7. Project Governance/<PROJECT_ID> - Project
  Report Card.xlsx` if that folder exists, otherwise to the project root (and prints which
  it did — surface this to the user, since it usually means the project needs
  `project-onboarding` run on it properly).
- Prints a JSON summary to stdout: output path, folders found vs. total, missing folders,
  mandatory totals, and any unclassified files per phase.

If `openpyxl` is missing: `pip install openpyxl --break-system-packages`, then retry.

---

## Step 2 — Read the summary and flag issues

Read the JSON the script printed. This is where "best-effort scan, flag issues, never
move files" comes in — the script has already surfaced the raw facts; your job is to
translate them into a clear chat summary:

- **Missing phase folders** (`missing_folders` non-empty): tell the user which ones, and
  that those phases show 0 deliverables present by definition — not because work is
  missing, but because the folder itself isn't there. Suggest `project-onboarding` if
  several are missing (this usually means the project was never fully onboarded).
- **Unclassified files** (`unclassified_files_total` > 0): list them per phase from
  `unclassified_by_phase`. These are files sitting in a phase folder that don't map to any
  known deliverable by name — could be genuinely extra material, or could need renaming to
  match F3 so the scan picks them up next time. Don't move or rename them yourself.
- **Mandatory gap** (`mandatory_present` < `mandatory_total`): note the count and, if
  useful, open the Deliverables sheet mentally (or actually, via Read/Bash) to name the
  specific missing mandatory IDs for the user.

---

## Step 3 — Present the result

```
✅ Rescanned <PROJECT_ID> (<engagement type>)

Report Card: 7. Project Governance/<PROJECT_ID> - Project Report Card.xlsx
  • Dashboard — per-phase completion & gate status
  • Deliverables — full D1–D41 tracker, Present?/Actual File(s) reflect what's on disk right now

Folders found: <folders_found>/9<, missing: [...] if any>
Mandatory deliverables present: <mandatory_present>/<mandatory_total>
Unclassified files: <unclassified_files_total> <(list if any)>
```

Present the `.xlsx` with `mcp__cowork__present_files`.

---

## Notes & Known Issues

- **Taxonomy is duplicated by design.** `PHASES` in `scripts/generate_report_card.py`
  re-encodes the same D1–D41 list as `project-onboarding/scripts/pdp_onboard.py` and
  `kaizen-pdp-phases/references/pdp-checklist.md`. If the taxonomy changes (new
  deliverable, renumbering, changed mandatory flags), all three need updating by hand —
  this skill was deliberately kept independent of `pdp_onboard.py` rather than importing
  it, so there is no single shared source of truth to patch in code, only in convention.
- **Scope is intentionally narrower than `project-onboarding`'s Report Card.** This skill
  only produces the Dashboard and Deliverables sheets. It does not produce a Tasks sheet,
  a Gap Analysis sheet, a Reorg Manifest, per-phase checklists, or the Quality audit
  files — `project-onboarding` remains the place for those. Because the output filename
  and location match exactly, running this skill after `project-onboarding` simply
  refreshes the same Report Card file with a leaner sheet set.
- **Matching is conservative on purpose.** A file only counts as satisfying a deliverable
  if it matches the F3 name exactly or contains every significant word of the deliverable
  name. A near-miss is safer left "unclassified" than silently mis-attributed.

---

## Error Handling

| Situation | Action |
|---|---|
| Project root ambiguous / not connected | Ask the user to confirm the path |
| No `.kaizen-project.json` and folder name looks wrong | Ask the user for the Project ID before running |
| Engagement type not in `.kaizen-project.json` | Ask the user; default to `deliverable-based` only if they don't know |
| `openpyxl` not installed | `pip install openpyxl --break-system-packages` |
| No phase folders exist at all | Still run the scan (it will show 0/9), but tell the user this project likely needs `project-onboarding` instead |
| Some phase folders missing, others present | Proceed normally — flag the missing ones on the Dashboard and in your summary |
| File present but unmatched to any deliverable | Leave it unclassified in the output; report it, never guess or rename |
| `7. Project Governance` folder doesn't exist | Script writes the Report Card to the project root instead and says so — mention this to the user as a sign the project isn't fully onboarded |

---

_Created 2026-07-09._
