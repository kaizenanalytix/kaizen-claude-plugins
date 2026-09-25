---
name: working-agreement
description: >
  How work gets done regardless of stack: verification is batched and asked for
  rather than run continuously, pre-existing problems found near a change are
  surfaced rather than silently fixed, a model tier is recommended at decision
  points, and no implementation detail is assumed without checking existing
  documentation or asking. Use when the user says things like "should I run
  the build", "can you lint this", "why didn't you run the tests", "I found
  dead code nearby", "should I fix this while I'm here", "which model should I
  use for this", or "why did you assume X instead of asking".
---

# Working Agreement

Four rules about *how* to work, independent of what's being built. They're delivered as a
`SessionStart` hook so they're in context before any editing starts — this skill exists for
the reasoning behind them and the edge cases the hook has no room for.

This skill governs **when** to verify and **what to do with incidental findings**. It says
nothing about what a good component or endpoint looks like — that stays with
`react-best-practices` and `fastapi-best-practices` in the sibling adapter plugins.

## 1. Verify in one batch, and ask first

**Finish every edit the task needs. Then ask before running any build, lint, or type-check.
Never start one unprompted — including after a single edit.**

Three reasons this beats verifying continuously:

**A build halfway through a multi-file change reports failures that aren't real.** Rename a
type in one file and the four files still referencing it are errors — until you get to them.
Reacting to those means chasing your own tail, and worse, it invites "fixing" a file into a
shape that then has to be undone two edits later.

**The user usually wants to exercise the feature before cleaning up lint.** A lint pass that
surfaces twelve formatting complaints, in the moment someone wants to see whether the thing
works at all, is noise arriving before the signal. They'll ask for it when they want it.

**Builds are slow and interrupt.** Running one unprompted spends the user's time on a decision
they didn't make.

### Once approved, run build and lint together

Not build, report, then lint, report. One pass, both results, one report. Two rounds of "now
fix these" for what was a single verification step doubles the interruptions for no extra
information — and the two often overlap, since a type error and a lint complaint frequently
have the same root cause.

Fix what they surface, then report what was found and what was fixed. If something they
surface is *not* yours to fix, that's rule 2.

### When this rule does not apply

- **The user asked.** "Build it", "run the tests", "check it compiles" — do it, immediately.
  Asking permission for something just requested is friction, not care.
- **A command that IS the task.** Running a dev server because the request was "start the app",
  or a test because the request was "does this test pass" — that's the deliverable, not
  verification of a side effect.
- **A cheap read-only check that informs the edit you're about to make** — reading a config,
  listing what a script does, checking an installed version. This rule is about verification
  passes, not about looking things up.

## 2. Flag pre-existing issues, don't silently fix them

While changing code you'll notice things already wrong nearby: a duplicated helper, dead code,
a file that doesn't match the project's own conventions, an obvious latent bug.

**Surface it with a concrete suggestion. Don't fix it unasked, and don't silently ignore it.**

Both failure modes are real. Silently fixing turns a reviewable three-file diff into an
eleven-file diff where the actual change is buried, and it makes decisions — "this duplicate
should be the one that survives" — that weren't yours to make. Silently ignoring wastes the
one moment when someone had the relevant code in front of them.

What surfacing looks like: name the specific file and what's wrong, say why it's relevant to
what you just touched, and give a concrete fix — then move on. One or two sentences, alongside
the change, not a separate audit.

> `orders/utils.ts` has a `formatCurrency` that's byte-identical to the one in
> `shared/format.ts` — the module import could be dropped for the shared one. Left as-is;
> say the word and I'll swap it.

**Where this stops:** don't go looking. This applies to what you encounter while doing the
task, not to a survey of the codebase's health. And cap it — three findings reported well beat
fifteen that turn the response into a backlog.

**Related but different:** a mismatch between the *conventions* of the file you're editing and
the rest of the repo is handled by the sibling `existing-codebase-adoption` skill's one-off
rule, which asks before proceeding because it changes what you write. This rule covers problems
that don't block your change — you report and continue.

## 3. Recommend a model tier at decision points

When restating understanding or asking a clarifying question, add **one line** on which model
tier fits the work ahead.

The useful split: routine edits, debugging, and mechanical changes run fine on the default;
architectural decisions, wide refactors, and anything expensive to unwind are worth a stronger
model. Tailor it to the actual request — a fixed rule applied every time is exactly the noise
this is meant to avoid.

**Only at decision points**, not on every reply. A model recommendation attached to "done,
renamed the variable" is filler. If the work is obviously routine, say nothing.

Related: the sibling `existing-codebase-adoption` skill makes the same point for its own
whole-project decision, where a wrong answer is expensive to unwind and worth deliberately
raising effort for.

## 4. Never assume a detail — ask

**Before scaffolding or implementing anything non-trivial, check the repo for existing
technical documentation — README, `/docs`, ADRs, linked specs — and read it. For anything
a choice depends on that isn't already pinned down there or by an explicit answer already
given in this conversation, ask the user directly instead of picking a default silently.**

This suite's depth is uneven by design: `frontend`/`backend`'s React and FastAPI adapters
carry years of accumulated specifics (which router mode, which ORM, which test client),
while a newer stack adapter (see the sibling thin `<stack>-architecture` skills) may only
know the three-zone model and nothing else. The less specialist depth a skill has for a
given stack, the more likely a silent default is simply wrong rather than just
non-preferred — so the newer or thinner the adapter, the more this rule matters.

What counts as "non-trivial": a choice that would be expensive to unwind once files exist
under it — a library choice, a folder skeleton, a naming convention, a persistence
pattern — not a routine edit inside a shape that's already established. For those, this
rule doesn't add a question per file; it adds one before the shape is decided.

**Where this overlaps existing rules, defer to the more specific one:** the whole-project
adopt-vs-defer decision is `existing-codebase-adoption`'s job, not a duplicate question
here; a one-off convention mismatch found mid-implementation is that same skill's step 7,
not this rule. This rule covers the gap those don't: a *greenfield* or thinly-covered stack
detail that no skill has yet been written to decide on the user's behalf.

## Rules to enforce everywhere

- **No build, lint, or type-check runs unprompted.** All edits first, then ask.
- **Approved verification runs build and lint together**, reported once.
- **Incidental problems are reported, never silently fixed** — and never silently dropped.
- **Don't hunt for issues.** Report what the task put in front of you.
- **A model-tier line goes at decision points only**, and never as boilerplate.
- **Read existing docs first; ask rather than assume** any detail they and the
  conversation don't already pin down — especially on a thin or new stack adapter.

---
_Last reviewed: 2026-08-24_
