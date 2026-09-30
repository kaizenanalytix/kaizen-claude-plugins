---
name: existing-codebase-adoption
description: >
  Decides, once and explicitly, whether to impose this suite's conventions
  for a given discipline on a project that already has its own existing
  structure, or to defer to that structure instead — then records the
  decision so later work stays consistent, and keeps handling one-off
  inconsistencies discovered later during implementation the same way. Use
  when the user says things like "this project already has a frontend",
  "this project already has a backend/API", "we already have an existing
  app", "should I follow this repo's conventions or Kaizen's", "adopt the
  existing structure", or when any other skill in a discipline plugin
  (frontend, backend, ...) is about to scaffold/rename/restructure something
  inside a project that wasn't started from scratch by this plugin.
---

# Existing Codebase Adoption

This skill exists because applying a discipline's own module skeleton or
naming rules to a project that already has its own different shape produces
an inconsistent codebase — half following Kaizen conventions, half following
whatever was already there — unless the choice is made explicitly, once, and
remembered. It's framework-agnostic on purpose: the calling adapter
(`frontend-architecture`, `backend-architecture`, or any future discipline
adapter) supplies its own stack detection and its own concrete specialist
skills; this skill only owns the adopt-vs-defer decision itself, its
persistence, and how one-off inconsistencies get handled afterward.

## Purpose

Before any structural convention from a discipline plugin (module shape,
file/folder naming, data-layer layout) is applied to a project, confirm
whether that project should adopt Kaizen's conventions going forward or keep
following its own existing conventions instead — and persist that decision
so this session and every future one stay consistent rather than silently
mixing both. This skill is also the one reliable trigger for keeping this
project's codebase map current: see step 1a below. `codebase-map-sync`
records facts and may already have a cached `predates_kaizen` fact for this
discipline — that's a useful signal for step 2 — but it never makes the
adopt-vs-defer decision itself; this skill still asks the user directly per
step 3 rather than deciding from that fact alone.

## 1. Check for an existing decision first

Look for `.kaizen/adoption.json` at the project root. If it has an entry for
the current discipline (`frontend`, `backend`, ...), read its `decision`
field and apply it — do not ask the user again. Only continue to the steps
below if no such entry exists yet for this discipline.

## 1a. Trigger codebase-map-sync alongside this decision

If a sibling `codebase-map` plugin is installed, invoke its
`codebase-map-sync` skill now, regardless of which branch step 1 took — they
write to different artifacts (`.kaizen/adoption.json` here,
`~/.claude/kaizen/<project>/codebase-map.json` there), so there's no ordering
dependency between them. This is what makes this skill a reliable single
entry point for "start working on an existing codebase": going through it
always also leaves the project mapped, instead of the map only existing when
some other skill happened to call `codebase-map-sync` first. If that plugin
isn't installed, skip this step — nothing else here requires it.

## 2. Confirm this is actually a decision point

The calling adapter already confirmed the stack and checked for greenfield
before routing here (e.g. `frontend-architecture` confirms React and checks
for existing `src/` app code; `backend-architecture` confirms FastAPI and
checks for an existing `core/`/`modules/` split) — reuse that adapter's own
check rather than re-detecting the stack here. If it's greenfield, this skill
doesn't apply: hand to a sibling `project-kickoff` skill in this plugin, which
sequences the whole start (design system, bootstrap, architecture, seeding the
codebase map) and routes to that discipline's own bootstrap skill
(`react-project-bootstrap`, `fastapi-project-bootstrap`, ...) at the right point
in that order. Its scaffold already follows Kaizen conventions from the first
file, so there's nothing to reconcile. If the project already has code for this
discipline — components,
pages, modules, or a folder structure that predates this plugin's
involvement — continue to step 3.

### The young project that skipped kickoff

There's a third case between "greenfield" and "an established codebase with its
own conventions": a small, recent project that was scaffolded by hand — nobody
ran `project-kickoff`, so no design system, no architecture skeleton, and no
codebase map were ever seeded, but there is real code now.

This plugin's `PreToolUse` adoption gate routes these here once they pass its
~20-tracked-file threshold, so expect to land in this case. **Do not ping-pong
it back to `project-kickoff`** — that skill's step 0 will bounce it straight
back here because code exists, and the user watches two skills disagree.

Handle it directly instead:

1. Say what you actually see — a small project, recently started, no kickoff
   artifacts (no central token/theme file, no `core/`/`modules/`/`shared/`
   split, no cached map).
2. Note that it's still cheap to adopt the conventions at this size, and that
   this stops being true fast — that's the whole argument `project-kickoff`
   makes about ordering.
3. Ask the normal step 3 question, but framed for the real situation: adopt
   this suite's conventions going forward, or keep the current ad-hoc layout?
4. If they choose Kaizen, offer the kickoff steps this project missed
   (design system, architecture skeleton) as **follow-up work they opt into**,
   not something that happens as a side effect of answering a convention
   question.

Then continue to step 5 and record the decision as normal. Step 1a's
`codebase-map-sync` call still runs, which is what gets this project mapped —
the seeding that `project-kickoff`'s step 6 would have done.

## 3. Restate your understanding, then ask

Before presenting the choice, restate in plain terms what you've actually
observed — the existing structure/convention found, or the specific signal
that this project predates the plugin — and why a decision is needed now.
This lets the user correct a misread before answering a binary choice built
on a wrong premise. For example: *"This repo already has an `app/services/`
layout using snake_case files, with no three-zone module split yet. Before I
scaffold anything, I need to know: should new code follow Kaizen's
conventions going forward, or should it match this existing layout?"* If the
user's reply suggests you misunderstood, correct it and restate before
proceeding.

Then present the choice:

- **(a) Adopt Kaizen's conventions going forward.** New code follows this
  discipline's own specialist skills for module shape, naming, and
  data-layer layout. Existing code is left alone unless the user separately
  asks for it to be migrated.
- **(b) Follow this repo's existing structure instead.** This discipline's
  skills adapt their suggestions to match the conventions already in this
  project rather than introducing a second, competing shape.

## 4. Get explicit confirmation before anything changes

This decision is consequential and expensive to unwind — undoing a
whole-project structural choice after several files have already been
written under it means redoing all of them. Do not write
`.kaizen/adoption.json`, scaffold anything, or rename/restructure anything on
an inferred or assumed answer; wait for the user's explicit reply to step 3.
If their phrasing is ambiguous between (a) and (b), ask again rather than
guessing.

There's no SKILL.md field to pin a model or reasoning-effort tier
declaratively (frontmatter here only carries `name`/`description`), so this
is guidance for whoever is steering the session rather than an enforced
setting: because a wrong answer here is expensive to unwind and this
decision point is rare — once per project, not once per file — it's worth
deliberately favoring higher reasoning effort for reading the existing repo
and framing the restatement in step 3, even if the rest of the session runs
on a faster default for routine edits. The one-off inconsistency asks in
step 7 don't need this same escalation — they're narrow and cheap to redo if
wrong, so default effort is fine there.

## 5. Persist the decision

Write (or update) `.kaizen/adoption.json` at the project root, keyed by
discipline so multiple disciplines can each have their own entry without
overwriting one another:

```json
{
  "frontend": {
    "decision": "kaizen",
    "decided_on": "2026-08-05",
    "notes": "short free-text description of the existing structure, if decision is 'existing'"
  },
  "backend": {
    "decision": "existing",
    "decided_on": "2026-08-06",
    "notes": "FastAPI app using a flat app/services/ layout, snake_case files, no three-zone split"
  }
}
```

If the file already exists with other disciplines' entries, merge in — don't
replace the whole file.

## 6. Route based on the decision

- `"kaizen"` → proceed normally: hand off to this discipline's own specialist
  skills for scaffolding, naming, and data-layer conventions (see the
  calling adapter's own routing table for which skill handles what).
- `"existing"` → before applying any structural convention from this
  discipline's plugin, read the existing repo's own equivalent pattern (how
  modules/components are currently organized, how files are named) and match
  it instead of applying a specialist skill's skeleton or naming rules
  verbatim. Non-structural guidance — correctness concerns like
  `state-philosophy`'s server-state/client-state split, `react-best-practices`'
  hooks hygiene, or `fastapi-best-practices`' async/DI checks — still
  applies, since it's about correctness rather than folder shape.

## 7. One-off inconsistencies found during implementation

The decision above answers ONE whole-project question. It does not resolve
every individual mismatch that surfaces later while actually writing code —
e.g. one existing file uses camelCase while the rest of the repo (or the
recorded decision) uses kebab-case; one existing module skips a layer every
other module has. When you notice a mismatch like this **during**
implementation, do not silently pick a side — neither "match the outlier"
nor "fix it to match everything else" is yours to decide unilaterally:

1. Stop before writing the change the mismatch affects.
2. Name the specific mismatch in plain terms: which file/area, which two
   conventions are in conflict, and why it matters for the change you're
   about to make.
3. Ask directly: match this file/area's existing (possibly inconsistent)
   pattern, or fix it now to be consistent with the rest of the repo (or the
   recorded decision)?
4. Proceed only after the user answers, and apply that answer only to the
   specific file/area asked about. This is **not** a new whole-project
   decision — don't write it to `.kaizen/adoption.json`, which is reserved
   for the one project-wide decision above, not per-file exceptions. If the
   same category of mismatch recurs elsewhere later in the task, point out
   that it matches one already resolved and ask whether the same answer
   applies, rather than treating it as unrelated.

This is a standing rule for the remainder of the current task, not a
one-time check. Once this skill has been read once — via the calling
adapter's gate, or because the user asked about adoption directly — keep
applying this rule to every file you touch for the rest of the task. It
doesn't need a fresh skill trigger each time: no one will phrase "this one
file is named differently" as a request for this skill by name, so the only
way this rule stays active is by already being in context from when the
skill first loaded.

## 8. Make the driving decision visible, cheaply

When a response's structure, naming, or skeleton choice is being driven by
this skill — either the whole-project decision above, or a one-off answer
from step 7 — say so in one short line alongside the change, e.g.
`Following the existing-codebase-adoption decision (existing): matching this
module's current file layout.` One line, not a restated rationale — just
enough that the user can tell this skill, not the plugin's own defaults, is
why the code looks the way it does. Skip this line entirely on turns where no
adoption-related decision is actually in play.

## 9. Revisiting the decision

If the user later asks to migrate toward Kaizen's conventions, update the
`decision` field in `.kaizen/adoption.json` for that discipline and note the
migration in `notes`. Don't start applying different rules without updating
the marker — otherwise this skill (and every other skill checking it) will
disagree with what's actually on disk.

---
_Last reviewed: 2026-08-24_
