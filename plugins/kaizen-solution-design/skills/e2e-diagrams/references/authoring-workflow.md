# Authoring Workflow — fill the E2E templates

How the skill turns an engagement into a finished E2E Solution Overview by **filling the templates**
(no hand-drawing, no JSON renderer, no imported logos). Pair with `e2e-diagramming-standards.md`.

---

## A · Where to read the architecture

Read whatever exists in the working project folder (search it for these; missing docs are fine):

| Source doc | What to pull |
|---|---|
| Client Proposal / SOW / Opportunity Summary | scope, approach, tech direction |
| KT brief / Internal Kickoff / Technical checklist | stack, data sources, decisions |
| Business Requirements (BRD) | the functional flow / stages |
| Solution or Technical Design | confirmed components, data stores, integrations, actors |
| Any existing diagram | prior architecture to build on |

If none exist: *"Point me at the file(s) describing the solution and I'll build the E2E."*

Extract six things: **data sources · processing stages · data stores · decisions · actors ·
consumers**, plus any **external systems/APIs**.

## B · Map to phases + groups (Approach 3)

1. **Name 4 PHASES** — plain-language business beats, verb-led, outcome-focused (e.g. Collect →
   Build → Run → Improve). Exactly four. They carry the number, colour, and story.
2. **Bind a GROUP to each phase** — the technical stage that delivers it; it inherits the phase's
   number and a matching name (Phase 2 "Build" → Group "2 · Model training").
3. **Add SUPPORTING groups** for architecture that isn't itself a phase beat (staging, shared
   services) — neutral gray, **no number**.
4. **Pick actors** — one pill per responsible role, placed above the group(s) it owns.
5. **Feedback loop?** Only if a real one exists → one dashed black arrow (e.g. phase 4 → phase 2).

Write a quick map before drawing, e.g.:
```
Phase 1 Collect   → Group 1 Data intake        actor: Data team
Phase 2 Build     → Group 2 Reconcile & model  actor: Data team
(supporting)      → Data prep / staging
Phase 3 Run       → Group 3 Serve & publish     actor: Analyst
Phase 4 Improve   → Group 4 Review & correct    actor: Analyst   (feedback → Phase 2)
```

## C · Fill the master template

1. Copy `e2e-template-01-master-kaizenblue.drawio`.
2. Replace every `[ … ]` placeholder: title, subtitle, client logo, phase names + one-line outcomes,
   band headline, actor pills, group titles.
3. **Add nodes** inside each group by copying shapes from `02` (stencils) / `04` (blocks): rounded
   process boxes, data-store cylinders, a decision diamond where there's a real branch, a gray
   archive box for a reject path.
4. **Connect** with labelled **black** arrows (solid = flow, dashed = async/optional/feedback).
5. **Footer**: Legend (copy from `04`), Data Sources (one card per source: name · what it provides ·
   format badge · "For <purpose>"), External APIs (dashed cards).
6. Keep everything inside **1280×720**; do not alter colours, shapes, or font sizes — the template
   already encodes the standard.

## D · Review (BP-1…BP-10)

Self-check with the checklist in `e2e-diagramming-standards.md §6`. For a rigorous pass, export a PNG
(or open the `.drawio`) and self-review it against the BP checklist, applying the same house rules
(black arrows not connector dots; shape-based icons, no logos). Apply every fix and re-check until it
passes.

Fast checklist:
- [ ] 4 phases, each bound to a same-numbered group; extras are gray "supporting"
- [ ] Kaizen blue `#002F6C` unified; square groups; rounded process boxes; cylinders for stores
- [ ] every arrow black and **labelled**; feedback (if any) dashed; no connector dots; no logos
- [ ] title + Kaizen logo (L) + client logo (R); one frame; footer trio present
- [ ] type scale respected; nothing clipped/overlapping; fits 1280×720
- [ ] labels business-readable (products only in `[brackets]`)

## E · Save & summarise

Present a summary (phases, groups, actors, #arrows, feedback y/n) and the proposed path
`diagrams/E2E Solution Overview.drawio` (create the `diagrams/` subfolder under the working folder if
missing). **Guardrails:** check for an existing version and version instead of overwriting (" v2", …);
show the path and get confirmation before writing. On "save": write the `.drawio` (+ PNG if a renderer
is available) and present the files. Report the saved paths, the phase→group map, and the review verdict.

## Error handling
See the table in `SKILL.md`. Key ones: unclear architecture → best-effort with `[TO CONFIRM]`;
more than four natural phases → keep four business beats and push detail into groups; no real loop →
omit feedback (it's optional); can't render PNG → deliver the `.drawio` and review by opening it.
