---
name: governance-scorecard
description: >
  Use this skill when the Engagement Lead (EL) wants to fill out the Project Governance Scorecard
  for a Kaizen PDP engagement — the monthly, VP-reviewed scorecard tracking Scope, Timeline,
  Budget, Client Satisfaction, Kaizen Team, and Pursuits (RAG + notes), plus recent milestones and
  the PDP checklist. Trigger on: "governance scorecard", "fill out the scorecard", "project
  governance scorecard", "monthly governance scorecard", "prep for the governance call",
  "governance review deck", "VP governance scorecard", "update the scorecard", "scorecard for the
  monthly connect". The skill SCANS the project's PDP phase folders to pre-fill everything it can
  find (checklist items, recent milestones, last month's status), ASKS the EL only about what it
  can't find or can't judge (RAG ratings, narrative), then POPULATES the branded scorecard slide
  and saves it to "7. Project Governance". If a scorecard deck already exists there, it APPENDS a
  new dated slide so each month accretes as history in one deck.
---

# governance-scorecard Skill

Fills out the **Project Governance Scorecard** — the monthly artifact the EL reviews with the VP
of Business Consulting. Output: a branded `.pptx` saved to `7. Project Governance`, one slide per
month.

**The scorecard MUST follow the bundled template**, at
`template/Project Governance Scorecard - TEMPLATE.pptx` (relative to this skill). Do not invent a
new layout — the generator clones the template's blank scorecard slide and fills its three tables.

The scorecard slide has three tables plus a RAG legend:

1. **Status** — six rows (Scope, Timeline, Budget, Client Sat., Kaizen Team, Pursuits), each with a
   RAG light (green / amber / red oval in the middle column) and a "Notes & Risks" cell.
2. **Upcoming Milestones & Recent Accomplishments** — Milestone / Date / Notes.
3. **PDP Checklist** — Agreed-upon Objects (RAID Log, Business Continuity Plan, End to End Diagram,
   System Arch Diagram, Value Tracker, Case Study) / Last Reviewed / Notes.

The flow is deliberately simple: **scan → ask only for gaps → populate → save or append.**

> **Guardrails:** This skill follows the shared guardrails (G1–G5) and file conventions (F1–F3)
> defined in the `guardrails` skill of kaizen-pdp-foundation. See that skill for
> version-not-overwrite, confirmation gates, verbatim financial data, deterministic finance,
> approval gates, folder structure, and file naming rules.

All deterministic work (scanning, populating tables, colouring RAG ovals, cloning/appending the
slide) is done by `scripts/build_scorecard.py`. **You** (the model) provide the judgment: reading
the scan, asking the EL about gaps, and mapping their answers into the data JSON. Never hand-edit
the PPTX — always drive the script.

---

## Step 0 — Locate the Project Root & Project ID

Find the folder containing the numbered phase folders (`0. …` through `8. …`), in particular
`7. Project Governance/`. If no workspace folder is connected, use
`mcp__cowork__request_cowork_directory`. If the root is ambiguous, ask the user to confirm.

Determine `PROJECT_ID` per F1: read `.kaizen-project.json` (`PROJECT_ID`) if present, else use the
root folder name. If neither looks valid, ask the user.

---

## Step 1 — Scan (read-only pre-fill)

Run the scan. It is read-only and never writes to the project:

```bash
python "<SKILL_DIR>/scripts/build_scorecard.py" scan \
  --root "<PROJECT_ROOT>" --project-id "<PROJECT_ID>" --out "<SCRATCH>/scan.json"
```

Read `scan.json`. It contains:

- `checklist` — each PDP-checklist item, whether a file was `found`, its `last_reviewed`
  (file's modified month), `file`, `path`, and `candidates`. Detection uses an explicit **alias
  map** (e.g. `End to End Diagram` ← `e2e` / `solution overview` / `playbook`; `Value Tracker` ←
  `p3` / `economics` / `benefits tracker`), so it catches files that don't match the item name
  literally. This is the deliberate fix for the Report Card's name-matching gap — do not rely on
  fuzzy name overlap.
- `gaps` — checklist items with no file found. **These are what you ask the EL about.**
- `milestone_candidates` — files touched in the last ~45 days, as candidate accomplishments.
- `status_prefill` + `prior_month` — last month's Status notes if a scorecard deck already exists
  (`deck_exists: true`), so the EL edits deltas rather than starting blank.

Tell the EL what you found vs. what's missing, e.g. "Found RAID Log, E2E, System Arch and Value
Tracker on disk; no Business Continuity Plan or Case Study yet."

---

## Step 2 — Ask only for the gaps and the judgment

Fill everything the scan already answered. Then ask the EL — briefly, one topic at a time — only
for what the scan can't provide:

1. **The six Status RAG ratings + notes.** These are EL judgment, not scannable. If
   `status_prefill` exists, show last month's note and ask what changed. For each row capture a RAG
   (`green` / `amber` / `red`) and a one-line note. You may *suggest* a RAG with a reason drawn
   from the scan (e.g. "Timeline → amber: Technical Design present but Test Plan missing"), but the
   EL's answer wins.
2. **Missing checklist items (`gaps`).** For each, ask: is it done, and where's the file? Or what's
   the status? If the EL points to a file, record its path in the notes. Never invent a status.
3. **Milestones.** Offer the `milestone_candidates` as a starting list; ask the EL to confirm,
   edit, or add the accomplishments and upcoming milestones worth showing the VP.

Per G3/G4 (Deterministic Finance): do not compute or estimate budget figures. For the Budget row,
record only what the EL states or what a source document (P3/SOW) says verbatim.

Do not overwhelm the EL — ask in small batches, pre-filling generously so most answers are a quick
confirm.

---

## Step 3 — Write the data JSON

Assemble the EL's answers plus the scan pre-fill into a data JSON (schema in the script header):

```json
{
  "project_id": "<PROJECT_ID>",
  "date": "<e.g. Jul 2026>",
  "product_name": "<short product/engagement name for the banner; defaults to project_id>",
  "status": {
    "Scope":       {"rag": "green", "notes": "..."},
    "Timeline":    {"rag": "amber", "notes": "..."},
    "Budget":      {"rag": "red",   "notes": "..."},
    "Client Sat.": {"rag": "green", "notes": "..."},
    "Kaizen Team": {"rag": "green", "notes": "..."},
    "Pursuits":    {"rag": "green", "notes": "..."}
  },
  "milestones": [ {"milestone": "...", "date": "7/18", "notes": "..."} ],
  "pdp_checklist": [ {"item": "RAID Log", "last_reviewed": "Jul 2026", "notes": "..."} ]
}
```

Write it to scratch (`<SCRATCH>/scorecard_data.json`). Use the exact Status row labels above.
RAG accepts `green|amber|red` (and common synonyms: on track / at risk / off track). Carry the
scanned `last_reviewed` / path into the checklist notes so the VP sees where each artifact lives.

---

## Step 4 — Confirm, then build (G2 gate)

Show the EL a summary of what will be written and the destination path **before** writing:

```
I'll add the <Month YYYY> scorecard slide to:
  7. Project Governance/<PROJECT_ID> - Project Governance Scorecard.pptx
  (<creating a new deck | appending a new slide to the existing deck>)
Reply "go ahead" to write it.
```

On approval, build:

```bash
python "<SKILL_DIR>/scripts/build_scorecard.py" build \
  --data "<SCRATCH>/scorecard_data.json" --root "<PROJECT_ROOT>"
```

Behaviour:
- **No deck exists** → creates `<PROJECT_ID> - Project Governance Scorecard.pptx` (title slide +
  this month's slide).
- **Deck exists** → appends a new dated slide cloned from the template's blank scorecard slide;
  earlier months are untouched (history accretes in one file).
- Pass `--no-append` only if the EL explicitly wants a separate new file — the script then G1-versions
  (`… v2.pptx`) instead of overwriting.

The generator places a clean RAG oval at each Status row's centre (the template's own ovals are
inconsistently positioned) and preserves the RAG legend.

---

## Step 5 — Present & Summarise

Present the deck with `mcp__cowork__present_files`, then summarise briefly:

```
✅ <Month YYYY> Project Governance Scorecard <created | appended>
  7. Project Governance/<PROJECT_ID> - Project Governance Scorecard.pptx  (<N> slides)

Status: Scope 🟢 · Timeline 🟡 · Budget 🔴 · Client Sat 🟢 · Team 🟢 · Pursuits 🟢
Checklist gaps still open: Business Continuity Plan, Case Study
```

---

## What the Scan Detects (reference)

The PDP-checklist alias map lives in `scripts/build_scorecard.py` (`CHECKLIST_ALIASES`). Extend it
there when the firm adds checklist items or new naming conventions — it is the single place that
bridges scorecard-checklist labels to on-disk filenames.

| Checklist item | Matches filenames containing |
|---|---|
| RAID Log | raid |
| Business Continuity Plan | business continuity, bcp, continuity plan |
| End to End Diagram | e2e, end to end, solution overview, playbook, process flow |
| System Arch Diagram | system arch, architecture, solution architecture, technical design, tdd |
| Value Tracker | value tracker, benefits tracker, p3, economics, roi |
| Case Study | case study |

---

## Error Handling

| Situation | Action |
|---|---|
| Project root ambiguous / not connected | Ask user to confirm; use `request_cowork_directory` |
| `PROJECT_ID` not derivable | Ask the user before building |
| A checklist item has no file | Leave it in `gaps`; ask the EL — never mark it reviewed by guessing |
| EL points to a file for a gap | Record its path in the item's notes; optionally note it for a Report Card refresh |
| Budget / financial figure requested | Per G3/G4 — copy verbatim from P3/SOW or record only what the EL states; never estimate |
| Deck already exists | Default: append a new dated slide. Only `--no-append` (→ G1 version) if the EL wants a separate file |
| `python-pptx` not installed | `pip install python-pptx --break-system-packages` |
| Prior deck unreadable for carry-forward | Proceed without prefill; tell the EL last month's notes couldn't be read |

---

_Last reviewed: 2026-07-20_
