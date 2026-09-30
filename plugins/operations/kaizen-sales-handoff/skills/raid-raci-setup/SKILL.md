---
name: raid-raci-setup
description: >
  Use this skill when the Engagement Lead (EL) or Project Manager (PM) wants to SET UP or UPDATE
  the RAID Log (D33, Mandatory) and the RACI Chart (D34, Mandatory) for a Kaizen PDP engagement.
  The RAID Log is a living document — use this skill both to create it and to keep it current as
  new information arrives from emails, meeting transcripts, Minutes of Meeting, or any project
  document.
  Trigger on: "set up RAID and RACI", "create RAID log", "generate RAID", "RACI chart",
  "set up risk register", "create RACI matrix", "RAID setup", "risks actions issues decisions",
  "generate RACI", and also on UPDATE phrasings like "update the RAID log", "add this to the
  RAID log", "update RAID from the latest email/MoM/meeting", "log these risks/actions/decisions",
  "refresh the RAID log", "add these action items to the RAID". Whenever the user wants RAID or
  RACI content captured or refreshed — even if they just paste an email or point at a transcript
  and say "put the risks/actions in the log" — use this skill.
  It reads the KT Brief and team list plus any user-supplied source (email, transcript, MoM, or
  PDP document), and writes/updates a RAID Log (.xlsx) and optionally a RACI Chart (.xlsx) in
  "7. Project Governance".
---

# raid-raci-setup Skill

Create **or update** the RAID Log (D33, Mandatory) and the RACI Chart (D34, Mandatory).
Output: one or two .xlsx files in `7. Project Governance`.

The RAID Log is a **living governance document**. This skill runs in two modes:

- **SETUP** — no RAID Log exists yet → copy the bundled template and seed it from the KT Brief.
- **UPDATE** — a RAID Log already exists → ingest new source material and append/amend it without
  disturbing existing rows or manual edits.

The RAID Log **MUST** be produced by copying and populating the bundled template, never by
building a workbook from scratch:

```
<SKILL_DIR>/templates/RAID Log (Risk Actions Issues Decisions) Template.xlsx
```

The template is the single source of truth for the RAID Log's structure, formulas, dropdowns,
formatting, and print areas. Preserve all of it — only add data rows and fill the header cells
and the Lookup staff list. Do not delete sheets, rename columns, or alter the header rows.

All writes to the workbook go through the bundled engine, which keeps the "don't clobber the log"
rules in one tested place (continues IDs, preserves formulas, dedups, stamps provenance):

```
<SKILL_DIR>/scripts/update_raid_log.py
```

Source extraction protocols (email/transcript/MoM/docs) live in:

```
<SKILL_DIR>/references/source-ingestion.md
```

Dependencies: `openpyxl` (used by the engine); optionally an Outlook/M365 email connector and a
Teams/meeting transcript connector for pulling sources (both degrade gracefully to user-supplied
files if not authorized).

> **Guardrails:** This skill follows the shared guardrails (G1–G5) defined in the `guardrails`
> skill of shared-foundation-plugin. See that skill for version-not-overwrite, confirmation
> gates, verbatim financial data, deterministic finance, and approval gate rules.

---

## Step 0 — Locate the Project Root

Find the folder containing `1. Sales Handoff & Transition/`.

If no workspace folder is connected, use `mcp__cowork__request_cowork_directory` to request one.
If the project root is ambiguous, ask the user to confirm the path before proceeding.

Extract the `PROJECT_ID` from `.kaizen-project.json` if present, or parse the workspace folder
name (`[Client Familiar Name] [Timing] [Project Name]`). If neither is available, ask the user.

---

## Step 1 — Detect Mode: SETUP or UPDATE

Look for an existing RAID Log so you know whether to create or update:

```bash
find "<PROJECT_ROOT>/7. Project Governance/" -iname "*RAID*Log*.xlsx" | sort
```

- **No RAID Log found → SETUP mode.** Continue to Step 2, then seed from the KT Brief.
- **A RAID Log exists → UPDATE mode.** Use the latest version as the working file. Confirm with
  the user which log you'll update if more than one is present. In UPDATE mode you never start
  from the blank template — you modify the existing file in place (versioned per guardrail G1).

If the user's request names a specific source ("update the RAID from this email/MoM"), lean toward
UPDATE mode against the existing log.

---

## Step 2 — Gather Sources

RAID content comes from two kinds of source. Use whichever the request implies; ask if unclear.

### 2A. Baseline (SETUP) — project documents

For first-time setup, inventory `1. Sales Handoff & Transition/`:

```bash
find "<PROJECT_ROOT>/1. Sales Handoff & Transition/" -type f | sort
```

| Source | Purpose |
|---|---|
| KT Brief (.docx) | Risks, assumptions, open items, team contacts, scope |
| Internal Kickoff PPT (.pptx) | Team roster, project plan, risks slide |
| Team list / org chart (if present) | Full team roster with roles |

If no KT Brief or kickoff deck is found for a SETUP, advise the user to run `sales-handoff-brief`
or `project-kickoff-init` first (or to supply a source directly, as below).

### 2B. Ongoing (UPDATE) — user-supplied sources

The RAID Log is kept current from four source types. **Read
`references/source-ingestion.md` for the extraction protocol for each** — especially the email
rules, which are strict:

| Source | How it reaches the skill |
|---|---|
| **Outlook emails** | Scoped search only — ask for the Outlook **category/tag** first; if none, ask for a **subject** to search. Never scan the whole mailbox. |
| **Teams transcripts** | Ask for the **meeting name** first, then search transcripts for that meeting only (or read a transcript file/path the user provides). Never search all transcripts blindly. |
| **Minutes of Meeting (MoM)** | A file the user provides in chat or points to in a PDP folder. |
| **Any other PDP document** | Any file the user points at in the PDP folders. |

Confirm the concrete source(s) with the user before extracting so scope stays tight.

### 2C. Extract into RAID items

From any gathered source, collect items for the four sheets. Copy wording, names, and dates
**verbatim** (guardrail G3):

- **Risks** — a future possibility (data availability, staffing, timeline, technical complexity,
  client dependencies, compliance). Fields: description, who raised it, likelihood, impact
  (High/Medium/Low each), owner, risk strategy (Acceptance / Mitigation / Transference),
  mitigating action, contingent action, status.
- **Actions** — open items / to-dos. Fields: category, who requested it, priority, description,
  current owner, expected resolution date, status.
- **Issues** — a problem already occurring. Same fields as Actions.
- **Decisions** — an agreement the team must honour. Fields: date, category, the decision,
  details, status (TBD / Draft / Confirmed).

For SETUP, also collect **header values** (Project name, Kaizen PM, Client PM) and the **team
member names** for the Lookup staff list. For the RACI Chart, collect team members and the key
activities/deliverables in scope.

Assemble the extracted items into a JSON file matching the shape in the engine's docstring
(`scripts/update_raid_log.py`), and pick a short **provenance label** for the source (e.g.
`KT Brief`, `Email "Re: data access" 2026-07-10`, `MoM 2026-07-08`).

---

## Step 3 — Write the RAID Log (D33) via the Engine

Never hand-populate the workbook with ad-hoc openpyxl. Always go through
`scripts/update_raid_log.py`, which continues IDs per sheet, preserves formulas and header rows,
dedups against what's already logged, and stamps each new row with its provenance. Its docstring
has the full JSON shape and column maps — read it if you need the details.

### SETUP mode

Copy the template, then run the engine with `--clear-examples` (blanks the template's demo rows
before writing real entries):

```bash
cp "<SKILL_DIR>/templates/RAID Log (Risk Actions Issues Decisions) Template.xlsx" "<OUTPUT_PATH>"
python "<SKILL_DIR>/scripts/update_raid_log.py" \
  --workbook "<OUTPUT_PATH>" --items items.json --source-tag "KT Brief" --clear-examples
```

The engine writes the header cells (`Risks!B2/B3/B4` — project name and PMs, which feed the other
tabs by formula), appends the staff list to the `Lookup` tab, and fills Risks/Actions/Issues/
Decisions from `items.json`.

### UPDATE mode — preview first, then write

Because items are extracted from free-form sources, the EL must see them before they enter the
governance log. Run the engine **`--dry-run` first** to produce the preview, show the user what
would be added (and any duplicates that would be skipped), then run for real once they approve:

```bash
# 1. Preview
python "<SKILL_DIR>/scripts/update_raid_log.py" \
  --workbook "<EXISTING_RAID>.xlsx" --items items.json \
  --source-tag 'Email "Re: data access" 2026-07-10' --dry-run
# 2. On approval, re-run without --dry-run
```

Present the dry-run result as a short table grouped by sheet (Risks / Actions / Issues /
Decisions), e.g.:

```
Proposed additions from <source>:
  Risks (2 new, 1 duplicate skipped):
    + Model refresh cadence undefined  (owner: —, status: Open)
    ⤫ Client data access not provisioned  (already logged)
  Actions (1 new): + Share sample invoices dataset  (owner: Jordan)

Reply "approve" to write these, or tell me what to change.
```

### Proposed changes to existing rows

If a source implies an **existing** item changed (a risk is now resolved, an action completed),
do **not** silently edit it. List the proposed edits for approval:

```
Proposed changes to existing items:
  Risk #1 "Client data access not provisioned": Status → Complete, Progress → "Access granted 7/11"

Reply "approve changes" to apply.
```

Apply only approved edits via the engine's `--updates` path:

```bash
python "<SKILL_DIR>/scripts/update_raid_log.py" --workbook "<EXISTING_RAID>.xlsx" --updates updates.json
```

`updates.json` is a list like `[{"sheet":"Risks","id":1,"set":{"status":"Complete","progress":"…"}}]`.

Per G3: copy all descriptions, dates, and names verbatim from source documents.

---

## Step 4 — Generate the RACI Chart (D34, Mandatory)

The RACI Chart is a mandatory Phase 7 deliverable. There is no bundled template for it, so build
it from scratch using the structure below. Generate it by default. If the user explicitly
wants to defer it, confirm:
> "The RACI Chart (D34) is mandatory. Generate it now, or defer? Reply 'generate' or 'defer'."

Generate it unless the user defers.

### Sheet: RACI Matrix

**Rows:** Key project activities and deliverables. Pre-populate from PDP phases relevant to the
project scope:

| Activity | Description | PDP Ref |
|---|---|---|
| Sales Knowledge Transfer | KT meeting with delivery team | T10 |
| Internal Kickoff | Kickoff deck + meeting | D11, T15, T16 |
| Environment Setup | Dev/test environment provisioning | T18 |
| Requirements Gathering | Business requirements document | D18 |
| Solution Design | Technical design | D21 |
| Development | Build and calibrate solution | T30 |
| Testing | Unit, integration, user testing | T31 |
| Sprint Reviews | Regular sprint/milestone reviews | T32 |
| Deployment | Deploy solution to production | T37 |
| Project Sign-Off | Client acceptance and sign-off | D30 |
| [TO CONFIRM] | Additional project-specific activities | — |

**Columns:** One column per team member. Use role abbreviations if names are not yet known:
EL, PM, Tech Lead, BA, Data Engineer, Developer, QA, Client Sponsor, Client PM, Client SME.

**Cell values:** R (Responsible), A (Accountable), C (Consulted), I (Informed), or blank.

### Default RACI assignments (adjust based on team structure)

| Activity | EL | PM | Tech Lead | BA | Client Sponsor | Client PM |
|---|---|---|---|---|---|---|
| Sales Knowledge Transfer | A | R | I | I | I | I |
| Internal Kickoff | A | R | C | I | I | I |
| Requirements Gathering | I | A | C | R | C | C |
| Solution Design | I | I | A/R | C | I | C |
| Development | I | I | A | — | I | I |
| Testing | I | A | C | C | I | C |
| Sprint Reviews | A | R | C | I | I | R |
| Deployment | I | A | R | I | I | C |
| Project Sign-Off | A | R | I | I | A | R |

[TO CONFIRM] — default RACI assignments should be validated against Kaizen's standard RACI
template if one exists.

### Formatting
- Header row and first column: Kaizen navy (`#0A2342`), white text
- R cells: dark blue fill
- A cells: green fill
- C cells: yellow fill
- I cells: light grey fill
- Include a legend row at the top explaining R/A/C/I

---

## Step 5 — Save the Output

**SETUP** writes new files to `7. Project Governance`:
```
Proposed files:
  1. <PROJECT_ROOT>/7. Project Governance/<PROJECT_ID> - RAID Log.xlsx
  2. <PROJECT_ROOT>/7. Project Governance/<PROJECT_ID> - RACI Chart.xlsx  (if generated)
```

**UPDATE** modifies the existing RAID Log. Per guardrail G1, do not overwrite blindly: save a
versioned copy (e.g. `… - RAID Log v2.xlsx`) unless the user explicitly wants the current file
updated in place. The EL preview gate in Step 3 already served as the content confirmation, so
here just confirm the destination filename.

After writing, present the file(s) using `mcp__cowork__present_files`.

---

## Step 6 — Summary in Chat

For **SETUP**:

```
✅ RAID Log generated: 7. Project Governance/<PROJECT_ID> - RAID Log.xlsx
✅ RACI Chart generated: 7. Project Governance/<PROJECT_ID> - RACI Chart.xlsx  (if applicable)

RAID Log summary:
  • Risks: N   • Actions: N   • Issues: N   • Decisions: N

Items requiring follow-up:
  • [list any items with missing owners or dates]
```

For **UPDATE**, report what changed and cite the source:

```
✅ RAID Log updated from <source>: 7. Project Governance/<PROJECT_ID> - RAID Log.xlsx

Added:   Risks +N, Actions +N, Issues +N, Decisions +N
Changed: Risk #1 → Complete (approved)
Skipped: N duplicates already logged

Items requiring follow-up:
  • [list any new items with missing owners or dates]
```

Suggested next: Say "generate technical checklist" to produce the Project Technical Checklist (D13).

---

## Error Handling

| Situation | Action |
|---|---|
| SETUP requested but no KT Brief/kickoff deck | Advise user to run prior skills first, or to supply a source directly |
| UPDATE requested but no existing RAID Log found | Switch to SETUP, or ask the user to point at the log |
| RAID template file missing from `templates/` | Stop; do not build a RAID Log from scratch. The bundled template is required |
| No items found in a source | Report "nothing to add from <source>"; make no changes |
| User asks to search email with no category | Ask for the Outlook category/tag; if none, ask for a subject. Never scan the whole mailbox |
| User asks to pull a transcript with no meeting name | Ask for the meeting name first; never search all transcripts blindly |
| Email/transcript connector not authorized | Say so; fall back to a user-supplied file/pasted text |
| Source implies an existing item changed | Propose the edit for approval; apply only via `--updates` after "approve changes" |
| Team members not yet identified | Use role placeholders (EL, PM, Tech Lead, etc.) |
| A source file is a cloud-only stub | Note it, continue with others; advise user |
| Project root ambiguous | Ask user to confirm path |
| `openpyxl` not installed | Run `pip install openpyxl --break-system-packages` |

---

_Last reviewed: 2026-07-13_
