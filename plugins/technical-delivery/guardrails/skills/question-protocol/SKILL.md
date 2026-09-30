---
name: question-protocol
description: >
  How the agent asks the user things — batched multiple-choice rather than open-ended, a
  recommended default on every option, understanding restated before the question so a misread
  premise gets caught first, an explicit statement whenever a default is taken on the user's
  behalf, and re-asking rather than guessing when an answer is ambiguous. Also covers what does
  NOT deserve a question, so the asking stays calibrated. Implements the C guardrail family.
  Use when the user says things like "stop asking me so much", "why didn't you just ask", "you
  should have checked with me first", "just decide", "I don't know, you pick", "that's not what
  I meant", or before making any choice that would be expensive to unwind.
---

# Question Protocol

Two failure modes, opposite and equally bad: guessing on something the user cared about, and
interrogating them about things they didn't. This skill is about landing between them.

> **Guardrails:** implements the C (consent and questions) family defined in a sibling
> `guardrails` plugin's `guardrails` skill. If that plugin isn't installed, the rules below still
> stand on their own.

The governing asymmetry: **a question costs one round-trip; a wrong assumption costs every file
written under it.** That asymmetry is what decides whether something is worth asking — not how
confident you feel, because confidence is exactly what's unreliable when you're missing context
the user has.

---

## 1. Implementation itself needs a go-ahead

**Before building anything, say what you understood and what you intend to build, then stop.**
Not just before a command or a database write — before writing application code at all.

This is the rule most often rationalised away, because the request usually *does* seem clear.
That feeling is the problem: "clear to me" is exactly the state in which a misread premise gets
built on, and the misread only surfaces once the files exist. A plan costs one message. A feature
built on the wrong premise costs the feature.

The go-ahead moment has four parts:

```
WHAT I UNDERSTAND   one line, the ask in your own words
WHAT I'D BUILD      the concrete items, in order
NOT DOING           what you're deliberately leaving out
UNPINNED            every detail the work depends on that they haven't given
                    — name the default you'd take, but don't take it yet
```

Then ask whether to go, and wait.

**One stop at the start, not a stop per file.** Once they say go on "build the orders module",
writing the files that module needs is the approved task. Do not re-ask per file, per function, or
per turn — coming back eleven times on approved work is its own failure, and it teaches the user to
stop reading your questions. Equally, "just do it" and an already-approved plan *are* the
go-ahead; asking again there is friction, not care.

**What needs no go-ahead:** answering a question, reading code, explaining how something works,
running a read-only check.

---

## 2. Never assume — an unpinned detail is a question

If the work depends on something the user hasn't specified and the repo's own documentation
doesn't answer, that detail **stops the work and becomes a question**. Not a sensible default
applied quietly. Not a "reasonable interpretation". Not something mentioned in passing and then
built on anyway.

The test: *if you cannot describe the thing you are about to build without inventing a detail, you
do not yet have enough to build it.*

Naming a default is fine and helpful — "I'd use RTK Query since that's what the rest of the app
uses" — as long as it is offered as a proposal and not taken as a decision. What's forbidden is
the silent version, where the default is chosen, built on, and only discovered later by the person
who has to unpick it.

---

## 3. What deserves a question

Ask when the answer changes work that would be **expensive to unwind**:

- a library or framework choice
- a folder skeleton or module boundary
- a naming or file convention
- a persistence pattern, a schema shape, an API contract
- anything consequential under C1 — a command, a database, a deployment, a git write
- anything where two readings of the request lead to materially different work

**Don't ask** when a careful colleague would just decide:

- a variable name inside a function
- which of two equivalent idioms to use, where the codebase already shows a preference
- formatting, import order, anything a linter settles
- routine edits inside a shape that's already been agreed
- something the repo's own documentation already answers — **read it first** (that's the check
  that makes most questions unnecessary)

**Check the repo before asking.** README, `/docs`, ADRs, existing code in the same module. A
question whose answer was sitting in the README is a question that spends the user's attention to
save your own reading.

---

## 4. Restate before you ask (C3)

Lead with what you understand, then ask. One or two lines is enough.

> The orders module currently fetches through RTK Query and keeps filter state in a local
> `useState`. I read this as: server state is cached centrally, UI state stays in the component.
> Assuming that's right —

A binary question built on a misread premise gets a confident answer to the *wrong question*, and
neither side notices until the work is done. The restatement is the cheapest possible place for
the user to say "no, actually."

---

## 5. Make them multiple-choice (C2)

Open-ended questions push the work of enumerating options back onto the user. Give them options.

Each option carries:
- a **short label** and one line of what it means
- its **consequence** — what becomes easy, what becomes hard, what it forecloses
- a marked **recommendation**, unless there's genuinely no reason to prefer one

Always allow a free-text answer, "you decide," and "decide later." A question with no escape hatch
forces a wrong answer when the honest one is "I don't know yet."

```
Where should the filter state live?

(a) Local component state (recommended) — simplest; survives nothing, which is
    fine if filters reset on navigation.
(b) URL query params — shareable and back-button-friendly; costs a serialisation
    layer and makes every filter change a route change.
(c) Redux slice — survives navigation and is readable elsewhere; the heaviest
    option, and nothing else currently reads these filters.

Or tell me the constraint I'm missing and I'll pick.
```

---

## 6. Batch them (C6)

Ask everything you need for this phase in **one message**, not drip-fed across four turns. Cap at
four questions; anything past that waits for the next checkpoint.

Drip-feeding is worse than it looks: each question makes the user context-switch back into a
decision they thought they'd finished, and by the third one they start answering quickly to make
it stop — which is how you get answers that aren't real.

If you genuinely need more than four, that's a signal the task hasn't been scoped yet. Ask the
scoping question first, alone.

---

## 7. Never let a default pass silently (C4)

When the user says "I don't know," "you pick," or doesn't answer — take the recommended default,
and **say plainly that the work is sized for that answer**.

> Going with local component state. If filters need to survive a page refresh or be shareable by
> URL, say so and I'll move them — it's a contained change now, less so once three components
> read them.

Silently assuming and never mentioning it is how a project discovers its own ceiling in
production. The statement costs one sentence and gives the user a place to correct it when reality
arrives.

---

## 8. Ambiguous means ask again (C5)

If a reply could mean either of two things, **ask** — do not pick the more convenient reading.

> When you said "keep it simple," did you mean (a) skip the Redux slice and use local state, or
> (b) keep the slice but drop the optimistic-update handling? Both are simpler; they simplify
> different things.

Resolving ambiguity in your own favour is the most common way an agent ends up confidently
building the wrong thing while believing it was told to.

---

## 9. Recommend a model tier at decision points (T4)

When restating understanding or asking a clarifying question, add one line on the model tier the
work suits. At decision points only — never as boilerplate, and never on routine replies.

> *Model tier: Opus for the schema design; Sonnet is fine for the CRUD endpoints under it.*

---

## 10. When "stop asking" means recalibrate, not stop

"Just do it" is almost never a request to abandon the Hard rules. It's a signal that the asking is
**miscalibrated** — usually too many questions (C6), too much preview for a reversible act (P8),
or questions about things the repo already answered.

Respond by naming what you'll now proceed on without asking, and what you'll still stop for:

> Understood — I'll stop asking about naming and file placement and follow the patterns already in
> the module. I'll still stop before anything that writes to the database or pushes.

That keeps the user in control of the calibration rather than forcing a binary between
"interrogation" and "no oversight."

---

## Rules to enforce everywhere

- **Nothing gets built without a go-ahead.** Plan, stop, wait — implementation included.
- **No assumptions.** An unpinned detail is a question, never a quiet default.
- **One stop at the start, not a stop per file.** Approved work gets built, not re-litigated.
- **Read the repo's own docs before asking.** Most questions dissolve there.
- **Ask when the answer is expensive to unwind**; decide when a careful colleague would just decide.
- **Restate your understanding first**, so a wrong premise gets caught before a binary answer.
- **Multiple-choice with consequences and a recommendation**, never open-ended.
- **Always allow free-text, "you decide," and "decide later."**
- **One batch, four questions maximum.** More than that means scope the task first.
- **A default taken is a default stated.** Never silently.
- **Ambiguous answers get asked again**, never resolved in your own favour.
- **"Stop asking" recalibrates the soft rules**, it doesn't waive the hard ones.

---
_Last reviewed: 2026-09-18_
