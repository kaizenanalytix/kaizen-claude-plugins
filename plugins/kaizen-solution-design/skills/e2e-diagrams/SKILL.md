---
name: e2e-diagram
description: >
  Generate the Kaizen End-to-End (E2E) Solution Overview diagram for an engagement by filling the
  bundled draw.io templates (1280x720, Kaizen blue) — NOT by hand-drawing or by the JSON renderer.
  Trigger on: "create E2E diagram", "end to end diagram", "E2E flow", "solution overview diagram",
  "generate the solution overview diagram", "draw the solution overview", "make the end-to-end diagram".
  The skill reads the engagement's architecture from the project documents, maps it to 4 plain-language
  business PHASES plus technical-stage GROUPS (Approach 3), fills the master template, checks it against
  the Kaizen Diagramming Best Practices, and saves an editable .drawio (+ optional PNG) to the project.
---

# e2e-diagram Skill

Produce the End-to-End Solution Overview (the one-slide solution overview picture) as an **editable
draw.io file** built by filling the bundled templates. One slide, 1280x720, unified Kaizen blue.

Assets (in this skill's `templates/` — the four files in `E2E Diagram Templates/`):

| File | Role |
|---|---|
| `e2e-template-01-master-kaizenblue.drawio` | The canvas you fill in (header, phase strip, automated band, footer) |
| `e2e-template-02-shape-stencils.drawio` | Node & chrome vocabulary — copy the correct shape |
| `e2e-template-03-palette-typography.drawio` | Colours (hex), type scale, flow notation |
| `e2e-template-04-building-blocks.drawio` | Assembled snippets (phase strip, group, footer trio) |

See `references/e2e-diagramming-standards.md` for the house rules and `references/authoring-workflow.md`
for the step-by-step fill + mapping.

> **Guardrails:** before writing, show the proposed path and get confirmation; never overwrite —
> version instead (" v2", …); keep financial figures verbatim.

> **Source of the visual language:** the colour format, icons/shapes, and diagramming rules come
> **only from the four E2E templates** above. Do **not** use the `solution-overview` skill's
> JSON renderer or its AWS/cloud/brand icon vocabulary (`aws.s3`, `databricks`, etc.). This E2E
> diagram is business-facing and shape-based — no technical/vendor logos. From `solution-overview`
> we reuse **process only** (workflow steps and the BP checklist).

---

## House conventions (locked)

- **One unified Kaizen blue `#002F6C`** for the frame, band header, phase cards, and phase-bearing
  group headers — on light `#E7EEF6` / white fills. Phases are told apart by **number + name +
  position**, not by hue.
- **Square group containers** (`rounded=0`). Process/service boxes stay rounded; data stores are
  cylinders; decisions are diamonds; externals are dashed boxes; actors are person shapes.
- **Black arrows only** (`#000000`). Every arrow is labelled. **No connector-dot (A/B) notation** —
  represent each link as a labelled black arrow.
- **Feedback is optional** — include a dashed black arrow only when a real loop exists.
- **No technical logos** on the business E2E; keep only a recognisable product in `[brackets]`.
- **Type scale**: title 28 · subtitle 16 · band header 14 · phase/group title 13 · actor 12 ·
  box/cylinder label 12–13 · box detail 10 · arrow labels 10–11 · footer 12/10 · caption 9.
- **Approach 3 structure**: 4 phases (1–4) each bound to a same-numbered group; extra architectural
  groups are neutral-gray "supporting" (no number).

---

## Step 0 — Locate the project & confirm scope
Work inside the connected/working project folder. If no project folder is connected or it's ambiguous,
ask the user to connect or point to it. Confirm this is a **business-facing E2E overview** (not the
technical design).

## Step 1 — Gather the architecture
Read whatever solution context exists (see `references/authoring-workflow.md` for the source-doc
table): proposal / SOW / KT brief / BRD / technical design / any existing diagram. Search the working
folder for these. Extract: data sources, the processing stages, data stores, the actors, the consumers,
and any external systems/APIs. If nothing is found, ask the user to point at the describing file(s).

## Step 2 — Map to phases + groups (Approach 3)
- **4 PHASES** = plain-language business beats (verb-led, outcome-focused). Always four; they carry
  the story, the number, and the colour.
- **Phase-bearing GROUPS** = the technical stage that delivers each phase; each inherits its phase's
  number + a matching name.
- **Supporting GROUPS** = architectural stages that aren't a phase beat → neutral gray, no number.
- Decide the **actors** (one pill per responsible role) and the **feedback loop** (only if real).

## Step 3 — Fill the master template
Copy `e2e-template-01-master-kaizenblue.drawio`, then replace every `[ … ]` placeholder with real
text. Add nodes inside each group by copying shapes from templates 02/04. Connect with labelled black
arrows. Fill the footer: Legend, Data Sources (cards + badges + "For <purpose>"), External APIs. Keep
everything inside the 1280x720 bounds. Do NOT change colours, shapes, or fonts — the template already
encodes them.

## Step 4 — Review against the Best Practices
Self-check against BP-1…BP-10 in `references/e2e-diagramming-standards.md`. For a rigorous pass, export
a PNG (or open the `.drawio`) and self-review it against BP-1…BP-10, applying fixes and re-checking
until it passes. House rule: labelled black arrows, no connector dots; shape-based icons, no logos.

## Step 5 — Present & save
Show the diagram summary (phases, groups, actors, #arrows, feedback yes/no) and propose the save path
under a `diagrams/` subfolder of the working folder — `diagrams/E2E Solution Overview.drawio` (create
`diagrams/` if missing). On confirmation, save the `.drawio` (+ PNG if a renderer is available), then
present the files.

## Step 6 — Summary
Report the saved paths, the phase→group map, and the review verdict.

---

## Error handling
| Situation | Action |
|---|---|
| No architecture docs | Ask which file(s) describe the solution |
| Architecture unclear | Best-effort; mark uncertain nodes `[TO CONFIRM]`; list unknowns |
| More than 4 natural phases | Keep 4 business beats; fold detail into groups/supporting groups |
| A feedback loop isn't real | Omit it (it's optional) |
| Can't render a PNG | Save the `.drawio`; review by opening it in draw.io |
| Project folder ambiguous | Ask the user to confirm the path |

---

_Last reviewed: 2026-08-27_
