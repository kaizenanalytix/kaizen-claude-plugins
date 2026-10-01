---
name: subtask-orchestration
description: >
  Splits a large task into stages and subtasks small enough for one context, each dispatched with
  acceptance criteria declared up front, verified against those criteria rather than against how
  good the summary reads, and memoised so a retry reuses finished work instead of re-solving it.
  Also governs bulk work done directly: a change repeating across more than about five files
  pilots on ONE first, shows the real diff, and confirms the pattern before the rest.
  Use when the user says things like "break this into smaller pieces", "do it in stages", "step by
  step", "use subagents", "this is too big for one pass", "rename this everywhere", "update all
  the files", "run these in parallel", or "the agent ran out of context".
---

# Subtask Orchestration

A large task handled in one context degrades in a specific way: early decisions fall out of
working memory, later work contradicts them, and nobody notices because the same agent that made
the mistake is the one checking for it.

> **Guardrails:** implements the O (orchestration) family defined in a sibling `guardrails`
> plugin's `guardrails` skill. If that plugin isn't installed, the rules below still stand on
> their own.

Splitting the work fixes the context problem and introduces two new ones — sub-agents can't ask
the user anything, and an orchestrator that grades its own homework will pass it. This skill is
about the second and third problems, which is where most of the value is.

**This is the same pattern a sibling `architecture-foundations` plugin's `project-kickoff` skill
uses for its design-system chain**, generalised: criteria declared at dispatch, results verified
against them, completed work memoised, and a user checkpoint at every phase boundary.

---

## 1. Decompose

A good subtask is one an agent can complete without needing anything you haven't handed it.

- **Sized to fit.** If it needs more than a handful of files in context, split it again.
- **Independent where possible.** Subtasks that can run in parallel should share no state.
- **Mechanical.** Anything needing live user judgement doesn't get dispatched at all (O7) — it
  stays in the main conversation where the user can see and interrupt it.
- **Verifiable.** If you can't say up front what "done correctly" looks like, you can't check the
  result, and the subtask isn't ready to dispatch.

Overlapping subproblems get factored out into their own subtask and solved **once** — the shared
type definitions, the common fixture, the schema both sides read. Solving the same thing in two
parallel agents gets you two different answers.

---

## 2. Checkpoint the plan (O8)

Before dispatching anything, show the user the decomposition and wait.

```
PLAN — 4 subtasks, 2 phases

Phase 1 (parallel, 2 agents)
  1. orders module: repository + service layer
     done when: OrderRepository implements the 4 declared methods; OrderService
     routes through it; no direct DB access outside infra/
  2. invoices module: repository + service layer
     done when: same shape as (1), against InvoiceRepository

Phase 2 (sequential, after both)
  3. wire both modules into the DI container and the app router
     done when: both routers mounted under /api/v1; both services resolve
  4. integration tests across the two modules
     done when: the declared cases pass against the test database

Resolved up front, so no agent has to ask:
  - repository pattern per fastapi-data-layer (existing project convention)
  - snake_case files, one class per file
  - no new dependencies

Not covered — say so explicitly
  - the payments module (untouched)
  - migrations (none needed; tables exist)

Shall I run this?
```

**A hard stop, not a suggestion.** The decomposition is the cheapest thing in the whole run to
correct — it costs one message now and several agents later.

---

## 3. Dispatch — the four things (O2)

Every dispatch prompt carries all four. Anything missing becomes something the sub-agent invents.

1. **The resolved answers, verbatim.** Every decision from §2, restated in full. The sub-agent has
   none of this conversation's context and cannot ask (O1).
2. **The acceptance criteria.** The same "done when" you showed the user — this is what you'll
   check against later, so it must be checkable.
3. **The return shape.** What the summary must contain: files written, decisions made, anything
   it couldn't do. Say "return a short summary, not your full reasoning."
4. **The negative constraints.** What not to touch, what not to create. State these **explicitly
   in every dispatch** — don't rely on them being obvious from context the sub-agent doesn't have:
   - make no further user-facing decisions
   - never create `.claude/`, `.claude/settings.json`, or `CLAUDE.md` (S3)
   - don't touch files outside the named scope (S2)
   - don't install dependencies (S5)

**Parallel fan-out:** dispatch independent subtasks as separate `Agent` calls **in the same
message** (several tool-use blocks in one response), then wait for all of them. Dispatching them
in consecutive messages silently reintroduces the sequential cost the split was meant to remove.

---

## 4. Verify against the criteria (O4)

Check each result against the criteria you declared at dispatch — **not** against whether the
summary reads convincingly. A well-written summary of work that wasn't done is the most common
failure here, and it is invisible unless you check against something fixed in advance.

For each subtask: criteria met / not met / can't tell from the result. Where you can't tell, go
look at the files. The sub-agent's report is evidence, not proof.

**A missing, null, or malformed result is a failure (O3).** Never fabricate a plausible summary
for a sub-agent that didn't return one, and never proceed as though a failed side succeeded. If
one of two parallel agents comes back empty, that side failed — say so and stop; don't infer what
it probably did.

---

## 5. Memoise (O6)

Record each completed subtask so a retry reuses it instead of re-solving it. This is what makes
the loop cheap enough to actually run.

`~/.claude/kaizen/<project-key>/orchestration/<task-id>.json` — per-user, **outside the project**,
the same place the codebase map and the adoption decision live. Orchestration state is this
marketplace's bookkeeping, not an artifact of the product, and it has no business being committed
to someone's codebase:

```json
{
  "task": "orders-and-invoices-modules",
  "started": "2026-09-18T10:22:00Z",
  "subtasks": {
    "1-orders-repo": {
      "status": "verified",
      "criteria": "OrderRepository implements the 4 declared methods; OrderService routes through it; no direct DB access outside infra/",
      "result": "6 files under modules/orders/{domain,infra,service,api}",
      "attempts": 1
    },
    "2-invoices-repo": {
      "status": "failed-verification",
      "criteria": "same shape as (1), against InvoiceRepository",
      "result": "wrote service and api, no repository interface in domain/",
      "attempts": 1
    }
  }
}
```

`status` is one of `pending | dispatched | verified | failed-verification | abandoned`.

**On a retry, read this file first and re-dispatch only what isn't `verified`.** A subtask solved
once is never solved twice — not across a retry, not across a new session, not because the
orchestrator forgot.

It survives a session, so an interrupted run resumes instead of restarting. It is deliberately
*not* shared with teammates — a half-finished orchestration is one person's in-flight work, not a
fact about the repo.

---

## 6. The loop — bounded, and with the user in it (O5)

When verification fails:

1. **Report what failed** — which criterion, what came back instead, and the evidence you checked.
2. **Say what you'd change** in the re-dispatch — a sharper criterion, more context, a smaller
   split. "Run it again" is not a change and won't produce a different result.
3. **Ask before spending another agent.** Each re-dispatch costs real time and tokens, and the
   user may know immediately that the criterion itself was wrong.
4. **Cap at two re-dispatches.** After that, stop and hand it back with everything you've learned.

```
Subtask 2 (invoices repository) failed verification.

  Criterion   InvoiceRepository interface declared in domain/, service routes through it
  Got         service and api written; no interface in domain/ — the service imports
              the SQLAlchemy model directly
  Checked     read modules/invoices/domain/ — only entities.py, no repository.py

  What I'd change: the dispatch didn't say the interface goes in domain/ and the
  implementation in infra/. I'd state that split explicitly and name both file paths.

Subtask 1 verified and won't re-run. Shall I re-dispatch 2 with that fix?
```

The loop closing without the user in it is the failure this rule exists to prevent — an
orchestrator that re-dispatches on its own can burn a dozen agents on a criterion that was wrong
from the start.

---

## 6a. The team model: a lead, a graph, and a review per node

Everything above treats subtasks as a flat list. Real work is a **graph** — the contract has to
exist before either side codes against it; the e2e test needs both sides. Phases approximate that
badly: they make independent nodes wait for unrelated ones.

**The shape.** Declare nodes with their dependencies. The lead repeatedly computes the *ready set*
— nodes whose dependencies have all completed — and dispatches that whole wave at once. When the
wave returns, it computes the next one. No node waits on anything it doesn't actually need.

**The constraint that shapes all of it: sub-agents cannot talk to each other.** They are spawned,
they run, they return to whoever spawned them. So "the team interacts" has exactly one true
meaning: **the lead is the message bus.** Every edge passes through it, and the lead decides what
of a finished node's output the next node actually needs.

That's not a limitation to route around — it's what keeps contexts small. Agents that could talk
freely would accumulate each other's noise, which is the failure the split exists to prevent.

**The handover packet** is what moves along each edge — a declared schema, not prose:

```
node          which node produced this
filesWritten  what it touched
exports       symbols, routes, or types a dependent may rely on
decisions     choices a dependent must not contradict
blocked       what it could not do, and why
```

`exports` and `decisions` carry the weight. A dependent needs to know *what it can import* and
*what it must not contradict* — and close to nothing else. Passing it the predecessor's full
reasoning is how contexts quietly grow back to the size you split to avoid (O10).

**Every node is reviewed by a different agent than built it** — given the acceptance criteria and
the packet, told to read the files, and explicitly told not to fix anything. An implementer
summarising its own work is evidence, not proof; a well-written summary of work that wasn't done is
the failure mode. The reviewer never sees the implementer's prompt, or it grades the intent instead
of the result.

**The loop per node:** implement → review → if the verdict fails, retry once with *only* the
reviewer's `mustFix` list → then stop and report (O5).

**The mechanism.** This is deterministic control flow — loops, conditionals, fan-out — so it belongs
in a script rather than in a model's judgement about what to dispatch next. The Workflow tool
provides exactly the pieces: `schema` enforces the handover packet at the tool-call layer,
`isolation: 'worktree'` stops concurrent implementers corrupting each other's files,
`resumeFromRunId` is O6's memoisation, and a plain `for` loop is the bounded retry. It requires
explicit opt-in on every run — a real cost, and not something to make a silent default.

`references/team-model.md` has the complete runnable script and the sizing table.

**When the graph drains**, the lead reports three things, not one: what completed, what failed, and
what **never started** because its upstream failed. That last list is the one most often omitted,
and the most misleading to omit — those nodes aren't broken, they were never attempted, and silence
reads as coverage.

---

## 7. Bulk work: pilot first, then stages (O9)

Everything above is about sub-agents. This section is about the other kind of large task — the
repetitive one you'd do yourself: rename a symbol across forty files, add a header to every skill,
migrate every component off a deprecated prop, reformat a hundred fixtures.

**The rule: more than about five files or items, and you do one first.**

1. **Pilot.** Apply the change to exactly one file. Show the actual result — the real diff, not a
   description of it.
2. **Confirm the pattern.** Ask whether that's right. This is the whole point: a wrong pattern
   costs one file to discover instead of forty.
3. **Stage the rest.** Work in visible batches with a checkpoint between them. Report what each
   stage touched.

**A script does not exempt you — it's the reason the rule exists.** Writing a loop that rewrites
fifty files in one call feels efficient, and it is, right up until the pattern is subtly wrong.
Then you have fifty wrong files, one unreviewable diff, and no signal about which of them the
error actually mattered in. Write the script if it helps, then *run it on one file first*.

> **A real example, from building this plugin.** Stamping a guardrail reference into 53 `SKILL.md`
> files was done as a single scripted pass over all 53. It happened to be correct. Had the
> insertion point been wrong — placed before the H1 instead of after the opening paragraph — that
> would have been 53 broken files in one commit, discovered only afterwards. One file, shown first,
> would have cost one message and caught it.

**What "stage" means in practice.** Not arbitrary chunks. Group by something real — by module, by
directory, by the kind of change — so a stage that fails tells you *which class* of case your
pattern didn't handle. Fifty files split as "1–25, 26–50" teaches you nothing when stage two
breaks; split as "components, then hooks, then tests" tells you immediately that hooks are
different.

**Where this doesn't apply.** A genuinely mechanical change the user has already seen the shape of,
under about five items, or a change that is meaningless one-at-a-time (a single rename that has to
land atomically or nothing compiles). For that last case, say so — "this has to go in one pass or
the build breaks" — rather than silently skipping the rule.

---

## 8. What doesn't get orchestrated

Splitting has real overhead: the plan, the checkpoint, the dispatch prompts, the verification.
Don't pay it for:

- work that fits comfortably in one context
- anything needing live user judgement at each step — that's a conversation, not a fan-out
- tightly coupled work where each step depends on the last one's output (a chain of one-agent
  hops is just a slower single agent)
- anything where you can't state acceptance criteria up front — write the criteria first, and if
  you can't, the task isn't understood well enough to split

---

## Rules to enforce everywhere

- **Criteria before dispatch.** If you can't say what "done correctly" means, don't dispatch it.
- **Checkpoint the decomposition** and wait. It's the cheapest correction in the run.
- **Every dispatch carries four things**: resolved answers verbatim, criteria, return shape,
  negative constraints.
- **A sub-agent never asks the user.** Resolve it before dispatch or don't dispatch it.
- **Independent subtasks go out in one message**, not consecutive ones.
- **Verify against the declared criteria**, not against how the summary reads.
- **A missing or malformed result is a failure** — never fabricate one, never proceed past it.
- **Memoise verified subtasks.** Solved once, never twice.
- **Ask before spending another agent**, and cap at two re-dispatches.
- **Overlapping subproblems get factored out** and solved once, not in parallel twice.
- **Dispatch the ready set, not a phase.** A node waits only on what it actually needs.
- **Pass predecessors' packets, never the whole history** — `exports` and `decisions`, not reasoning.
- **A different agent reviews than built.** Self-review is evidence, not proof.
- **Report what never started**, not just what failed.
- **Bulk work pilots on one item first**, shows the real result, then proceeds in staged batches.
- **A script doesn't exempt bulk work from staging** — it enlarges the blast radius, it doesn't
  shrink the review.

---
_Last reviewed: 2026-09-18_
