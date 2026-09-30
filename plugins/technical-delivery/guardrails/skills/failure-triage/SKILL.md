---
name: failure-triage
description: >
  What to do when a test, build, lint, or command fails — report the real output, sort the failure
  into test-was-wrong / real-defect / genuinely-ambiguous, state the explanation explicitly as a
  hypothesis rather than a finding, and ask before changing code. Covers the hypothesis report
  format, the two-attempt retry cap, and why forcing a test green is never an option. Stack- and
  tooling-agnostic. Implements the V guardrail family.
  Use when the user says things like "the test is failing", "this build broke", "why did that
  fail", "fix the failing test", "it says assertion error", "just make it pass", "the CI is red",
  "you keep trying the same thing", or after any test, build, type-check, or lint run comes back
  non-green.
---

# Failure Triage

A failing command is a **disagreement** between what something expected and what actually
happened. It is not, on its own, evidence about which side is wrong.

> **Guardrails:** implements the V (verification and the failure loop) family defined in a sibling
> `guardrails` plugin's `guardrails` skill. If that plugin isn't installed, the rules below still
> stand on their own.

The failure mode this skill exists to prevent: seeing a red test, forming a quick explanation,
editing the code to match that explanation, seeing green, and reporting success. When the
explanation was wrong, that sequence **permanently launders a real defect into "expected
behaviour"** — and every future green run then falsely confirms the app is fine. The one signal
that would have caught it is gone, and nobody knows it's gone.

---

## 1. Before anything: quote the real output

Paste the actual failing lines — the assertion, the stack frame, the type error, the exit status.
Verbatim, not paraphrased, not summarised into "the test failed because of a null issue."

The paraphrase is where the damage starts. Rewriting an error in your own words bakes your
interpretation into the evidence, so the user can no longer check your reasoning against what
actually happened — they can only check it against your reading of what happened.

Trim irrelevant stack frames if the output is enormous. Never trim the assertion itself, the
actual-vs-expected values, or the error type.

---

## 2. Trace it before explaining it

Read the source the failure points at — the function, the handler, the component, the comment
explaining why it works the way it does. Then sort the failure into **exactly one** of three
outcomes.

### (a) The test's assumption was wrong

The code shows the behaviour is deliberate — a comment, a doc, an unambiguous design decision —
and the test assumed something else.

→ Fix the test, re-run, and **say in one line** that you changed the test rather than the code,
and what made the behaviour deliberate.

### (b) This is a real defect

The behaviour contradicts the code's own stated intent, or is obviously wrong — data loss, broken
keyboard access, a security hole, an off-by-one in a boundary the code documents.

→ **Flag it as an application finding.** Don't quietly fix it as part of a test task unless fixing
it is the task. The user needs to know their app has this, separately from whether the suite is
green.

### (c) Genuinely ambiguous

The code doesn't make clear whether this was intended.

→ **Do not guess in either direction.** Don't fix the app, don't adjust the test's expectation.
Collect it, move to the next failure, and report it at the end (§3).

> **"I can't tell, so I'll just make it pass" is never an option.**

---

## 3. The hypothesis report

For anything in (b) or (c) — and for anything in (a) where the judgement wasn't obvious — present
this before touching code, then **stop and wait**.

```
<command that failed>

ACTUAL OUTPUT
  <the real failing lines, verbatim>

MY HYPOTHESIS (not a finding — I have not verified this)
  I think <explanation>.
  I also considered: <the other candidates, and why they're less likely>.

PROPOSED CHANGE
  <the exact change>, in <file:line>.
  If this is right, <what would then pass, and what that would prove>.

WHAT I'M NOT SURE ABOUT
  <the specific thing that would settle it, if you know>

This is the output, and I'm assuming <hypothesis> — shall I go ahead and make that change?
```

**Label the hypothesis as a hypothesis.** "The validator rejects empty carts" is a finding.
"I think the validator rejects empty carts" is a hypothesis. Only one of them is honest before
you've checked, and the difference changes how much weight the user gives it.

**List what else it could be.** A single explanation presented alone reads as settled. Naming the
alternatives you ruled out shows the user your reasoning and gives them the cheapest possible
place to correct it — they often know immediately which one it is.

**Never assume the code is the wrong side.** The test, the fixture, the environment, a stale
build, or your own earlier edit in this session are all equally likely causes, and the last one is
the one most often overlooked.

---

## 4. Batch the ambiguous ones (V7)

When a run produces several failures, triage all of them first, then present the ambiguous ones
**together in one end-of-run report** — not one interruption per failure.

For each: the test name, what it expected, what actually happened with the real output, the
relevant snippet of source, and a direct question — *"which is correct: should I update the test,
or is this a defect?"*

"Done" for a run means: green, **plus** any real findings clearly labelled as findings, **plus**
this report for anything ambiguous. Never a silent guess in either direction, and never "written
but unrun."

---

## 5. Two attempts, then stop (V6)

Count attempts at the **same** failure. After two, stop.

On the third, do not try a variation. Instead report:

- all attempts side by side — what you changed each time, and what the output was each time
- what you have now **ruled out**, which is real progress and worth stating
- plainly: *"I don't know what's causing this."*
- what you'd need — a log, an env value, a decision, access to something

Then ask how to proceed, and **don't run that command again until they answer**.

Open-ended self-correction loops are expensive, and they get less likely to work with each
iteration, not more: after two failed hypotheses the problem is usually somewhere you haven't
looked, and a third variation on the same guess searches the same wrong place again.

---

## 6. Never force green (V5)

Not available, in any circumstance, as a way to resolve a failure:

- loosening or deleting an assertion
- adding a fixed wait, a sleep, or a retry to paper over a race
- marking a test skipped, `xfail`, or `.only` on everything else
- widening a type, adding `any`, or a blanket `# type: ignore`
- `try/except: pass`, an empty `catch`, or swallowing the error
- lowering a coverage threshold, or adding the file to an ignore list
- re-running until it happens to pass

A flaky test is a defect in the automation or the application — not noise to suppress. Fix the
actual cause, or report it as a finding under §2(b). If the user explicitly asks for a skip as a
deliberate stopgap, that's their call: do it, and say in one line what is now unverified.

---

## 7. Written is not verified (V1)

Code that has been edited but never run has been **guessed at**. A spec file that was written and
never executed has not been verified — it has been drafted.

"I wrote the tests" and "I verified the tests" are two different claims. Only make the second one
having done the second thing.

This is why V2 batches verification and asks rather than running continuously: the point isn't to
run less, it's to run once, deliberately, and report what actually came back.

---

## Rules to enforce everywhere

- **Quote the real output.** Verbatim, never paraphrased into your interpretation of it.
- **Sort every failure into one of three** before touching anything: test wrong / real defect /
  ambiguous.
- **Label a hypothesis as a hypothesis**, and name the alternatives you considered.
- **Ask before changing code on a failure** you haven't conclusively traced.
- **Never assume the code is the wrong side** — the test, the fixture, the environment, and your
  own last edit are equally likely.
- **Two attempts, then stop** and report all of them side by side.
- **Never force green.** No loosened assertion, added wait, skip, widened type, or swallowed error.
- **Ambiguous failures are reported, never resolved by guessing** — batched into one end-of-run
  report.
- **Written is not verified.** Don't report done on unrun code.

---
_Last reviewed: 2026-09-18_
