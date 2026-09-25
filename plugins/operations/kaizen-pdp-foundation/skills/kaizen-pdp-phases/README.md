# kaizen-pdp-phases

An interactive **reference guide** for the Kaizen PDP (Project Delivery Process) checklist,
aligned to the *PDP Deliverables (June 22 2026)* sheet. It answers questions about phases,
mandatory items, gate conditions, and what to do next — for the Engagement Lead (EL) who needs to
act, not read essays. For "how do we actually do this" process questions, it also consults the
**EL Knowledge Base** on SharePoint (handbook, PSA/Sage setup, agile practices, etc.). It does
**not** generate documents; for that, invoke the relevant delivery skill.

## When to use it

Trigger phrases:

- "what's next" / "what phase are we in" / "PDP status"
- "show checklist" / "show me the checklist" / "PDP checklist" / "show PDP phases"
- "what's mandatory" / "what's mandatory in [phase]"
- "what deliverables are left" / "what do I need to do in [phase]"
- "phase guide" / "phase overview" / "PDP overview"
- Process / how-to: "how do I set up a project in PSA/Sage" / "what does the EL handbook say
  about [X]" / "agile best practices" / "EL timesheet checklist" (→ EL Knowledge Base lookup)

## Layout

```
kaizen-pdp-phases/
├── SKILL.md                          # Response patterns + quick-reference phase summaries + EL KB lookup flow
├── README.md                         # This file
└── references/
    └── pdp-checklist.md              # Full checklist — single source of truth for D/T IDs & mandatory flags
```

The EL Knowledge Base itself lives on SharePoint (not in this folder); the skill resolves it by
name (`EL Knowledge Base`) at query time and reads documents via the SharePoint connector's
`sharepoint_search` + `read_resource`. See the "EL Knowledge Base Lookup" section in `SKILL.md`.

Load `references/pdp-checklist.md` when answering phase-specific questions; the SKILL.md carries
compact per-phase summary tables for quick lookups.

## What it covers

- The 9 PDP phases (folders `0.`–`8.`) and their deliverables **D1–D41**, with mandatory flags.
- Gate logic for each phase transition (which deliverables/tasks must be done to advance).
- An **AI-Skill Cross-Reference** mapping each deliverable to the skill/plugin that generates it,
  plus notes on retired/relocated skills.

Note: this is a read-only reference. The `pdp-checklist.md` taxonomy is deliberately duplicated in
`project-onboarding` and `generate-report-card` scripts, so any change to deliverable IDs,
names, or mandatory flags must be applied in all three places by hand.

## See also

- `SKILL.md` — response format guidelines and the full phase/gate/skill reference tables.
- `../guardrails` — the G1–G5 guardrails and F1–F3 file conventions these phases assume.
- `../project-onboarding` — creates the phase folders and per-phase checklists this describes.
- `../generate-report-card` — turns the same taxonomy into an on-disk status Report Card.
