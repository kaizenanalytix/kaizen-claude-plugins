---
name: project-kickoff
description: >
  Orchestrates the start of a brand-new project end to end — asks the shape of
  the build up front, establishes the design system before any component
  exists, then routes to the framework bootstrap, the architecture skeleton,
  the API contract, and finally seeds the codebase-map cache. Writes nothing
  into the project's `.claude/` directory and creates no CLAUDE.md — plugin
  enablement stays user-level. The greenfield counterpart to
  existing-codebase-adoption. Use when the user says things like "start a new
  project", "bootstrap a new build", "set up a new app from scratch", "we're
  starting a new application", "new greenfield project", or "kick off a new
  repo".
---

# Project Kickoff

This skill owns the first hour of a new project. Without it, a new build gets a
framework skeleton and nothing else — no design foundation, no architecture, no
cached map — and each of those gets bolted on later at several times the cost.

It is deliberately an orchestrator: it decides *what happens in what order* and
hands each step to the skill that owns it. It writes almost nothing itself.

## Why the order is the whole point

Every step below is cheap now and expensive later, and the ordering reflects
exactly that:

- **Tokens before components.** Once one component ships with `text-[13px]`
  hardcoded, that value is permanent — nobody goes back. Establishing the scale
  against an empty `src/` costs nothing; retrofitting it into 200 components is
  a migration project.
- **Architecture before the first feature.** The first module silently becomes
  the template for every module after it, whether or not anyone intended that.
- **The codebase map seeded at the skeleton stage.** Scanning ~20 files is
  free; scanning a mature repo is the expensive first-run that gets deferred
  indefinitely.

Do not let a step be skipped for speed. Each one is at its cheapest right now.

## Step 0: Confirm this is genuinely greenfield

Check for existing source — `src/`, `app/`, a populated `package.json`, a
`pyproject.toml` with real dependencies.

If code already exists for a discipline, this skill does not apply to that
discipline. Route to a sibling `architecture-foundations` plugin's
`existing-codebase-adoption` skill, which decides whether this suite's
conventions or the project's own structure govern before anything is
scaffolded. (If that plugin isn't installed: ask the user directly whether new
code should follow this suite's conventions or match what's already there, and
carry that answer for the rest of the session.)

A repo can be split — an existing backend with a brand-new frontend is common.
Handle each discipline on its own track; see `references/kickoff-sequence.md`
for the partial-kickoff path.

**Don't bounce a young project back and forth.** If a project has real code but
clearly skipped this skill — a hand-scaffolded app with no design tokens, no
zone split, and no cached map — `existing-codebase-adoption` owns that case
directly (see its "young project that skipped kickoff" section). Route there
once and let it handle the conversation; routing it here again because it
"looks nearly greenfield" produces two skills handing the user back and forth.

## Step 1: Ask the shape of the build, as explicit options

Ask these **before** exploring or scaffolding anything, as multiple-choice
rather than open-ended questions. Everything downstream keys off the answers,
and each one is expensive to reverse once files exist.

1. **Stack** — frontend only / backend only / both.
2. **Product shape** — enterprise dashboard (desktop-primary, dense, responsive
   throughout) / public-facing site / mobile-first application. This sets the
   responsive posture and the type scale's centre of gravity.
3. **Design source** — reuse an existing theme from another Kaizen app / work
   from a Figma handoff / start from the default token set.

Wait for the answers. Do not infer them from the folder name or start
scaffolding while asking — a wrong guess here is rewritten, not adjusted.

## Step 2: Design system first, before any component exists

Only if the stack answer includes a frontend.

This step is purely mechanical once Step 1 is answered — none of the four
design-system skills below need to ask the user anything new, so delegate it
to a background sub-agent instead of loading all four skills' bodies into
this conversation:

Use the Agent tool (subagent_type: general-purpose, run in background) with a
prompt that:

- states Step 1's answers verbatim (stack, product shape, design source);
- instructs the subagent to invoke, in this order, a sibling `design-system`
  plugin's skills — `typography-system`, `design-tokens`,
  `responsive-breakpoints`, then `tailwind-theme-setup` — and write their
  files directly;
- if Step 1's design source was an existing Kaizen app, tells it to read that
  app's theme file and carry its values across rather than generating new
  ones — the point is consistency between products, not a fresh palette per
  repo;
- tells it to make no further user-facing decisions (every input it needs is
  already in the prompt) and to return only a short summary — files written,
  the chosen scale/token names — not its full reasoning.

Wait for that result, relay the short summary to the user, then continue to
Step 3. This is the only way this step should run: the four skills' combined
bodies (600+ lines) never need to load into the main conversation at all.

If the `design-system` plugin isn't installed, don't skip the step: at minimum,
establish an explicit type scale, a colour set named by role rather than by
appearance, and a spacing scale in one central file before writing any
component — do this directly, in-context, since there's nothing to delegate
without that plugin's skills to invoke. The rule that matters is *values are
defined once, centrally, and consumed by name.*

## Step 3+4: Bootstrap and architecture skeleton, per side

Per Step 1's stack answer, each side needs its bootstrap skill followed by its
architecture skill, in that order, before that side's skeleton is real. A
frontend side and a backend side never read each other's output at this
stage, so when the stack answer is "both," this is a genuine fork/join: run
both sides' chains at once instead of one after another.

**Frontend only** or **backend only** — dispatch the one applicable chain
below as a single background sub-agent. **Both** — dispatch both chains as
two separate `Agent` tool calls in the *same* message (two tool_use blocks),
then wait for both to return before continuing. Do not run them in separate
messages, one after the other — that silently reintroduces the sequential
cost this step exists to remove.

Each side's chain, whether dispatched alone or as one of the pair, uses the
same prompt shape — use the Agent tool (subagent_type: general-purpose, run
in background) with a prompt that:

- states Step 1's answers verbatim (stack, product shape, design source);
- states that Step 2 already wrote the theme file, and gives its path, so
  this side's bootstrap wires it into the entry point instead of generating a
  competing one;
- assigns this side its own top-level directory — `frontend/` for the
  frontend chain, `backend/` for the backend chain — and instructs it never
  to read or write inside the other side's directory (this matters even for
  a single-sided dispatch, so the layout stays consistent if a second side is
  added later);
- instructs it to invoke, in this order, inside itself: first that side's
  bootstrap skill (a sibling `frontend` plugin's `react-project-bootstrap`,
  or a sibling `backend` plugin's `fastapi-project-bootstrap`), then that
  side's architecture skill (`frontend-architecture` or
  `backend-architecture`) — and to write their files directly;
- instructs it to lay in `core/`, `modules/`, and `shared/` but leave
  `modules/` empty — no first business module gets created here. A
  speculative module invented at kickoff becomes the pattern everything
  copies;
- instructs it to make no further user-facing decisions, and to never create
  `.claude/`, `.claude/settings.json`, or a `CLAUDE.md`;
- tells it to return only a short summary — files written, entry-point
  wiring confirmation, and (frontend side only) confirmation the Step 2
  theme was consumed rather than regenerated — not its full reasoning.

These constraints (modules stay empty, no `.claude/` writes) used to be
enforced just by one agent doing the work in order. With two independent
sub-agents now able to write into the repo at once, state them explicitly in
every dispatch — don't rely on them being obvious from context the sub-agent
doesn't have.

**If dispatched as a pair**, once both return: if either result is missing,
`null`, or doesn't match the expected summary shape, treat that side as
failed. Do not proceed to Step 5 on a guess, and do not fabricate a plausible
summary for the failed side. Report which side succeeded (with its summary)
and which failed (with whatever error information is available), and ask the
user whether to retry the failed side's dispatch or stop here. Only continue
to Step 5 once both sides have a genuine result.

## Step 5: API contract — only if the stack is "both"

A sibling `api-contract` plugin's `contract-first` skill establishes the
OpenAPI schema both sides generate types from. Skip entirely for a single-sided
project; it can be added the day a second side appears.

## Step 6: Seed the codebase map

**Make the initial commit first.** The cache is keyed to a commit SHA, and a
repo with no commits has no `HEAD` to key it to — seeding before the first
commit produces a cache entry that can never be validated for staleness.

Then invoke a sibling `codebase-map` plugin's `codebase-map-sync` skill to
build `~/.claude/kaizen/<project-name>/codebase-map.json`.

Seeding here rather than on first use is the point: a skeleton is a handful of
files, so the scan is nearly instant, and every later `Step 0: consult the
codebase map` across the other plugins hits a warm cache from day one instead
of paying for a cold scan of a mature repo.

## Step 7: Say what comes next, then stop

The scaffold is done and `modules/` is deliberately empty, which means the
project has no tests and no way to ship yet. **Name the three next moves before
handing back**, in one or two lines each — not as work to start now, but so
nothing is left orphaned:

- **The first business module** — via `react-module-scaffold` /
  `fastapi-module-scaffold`, when there's an actual domain to model. The first
  one becomes the template for every module after it, so it's worth doing
  deliberately rather than in a hurry.
- **Tests, once that module exists** — a sibling `frontend` plugin's
  `react-testing` and `backend` plugin's `fastapi-testing` for the unit and
  integration layers. They wait for a module because there is nothing to test
  against an empty skeleton. A sibling `e2e-testing` plugin's
  `playwright-test-design` comes later still, once a *workflow* spans both
  sides — it's the most expensive layer and needs a real business flow to be
  worth writing.
- **Deployment, before the first deploy and ideally before the first feature
  ships** — a sibling `deployment` plugin's `deployment-strategy` skill. It
  asks what ships, who uses it, and what it does to data, then decides the
  shape (static hosting, a container, serverless, a VM) with reasoning. Worth
  raising early for the same reason everything else in this skill is ordered
  the way it is: the shape is cheap to choose now and expensive to reverse
  once there's a pipeline and an environment built on it.

Then stop. **Do not start any of them in the same turn as the kickoff** —
naming them is the deliverable here, and each one has its own questions to ask
when it's actually time.

If the relevant plugin isn't installed, still say what the project is missing
rather than staying silent about the gap.

## What this skill does not write

The sequence ends at step 7 — and steps 0–6 are the only ones that *build*
anything; step 7 only points. **This skill never creates a `.claude/` directory,
a `.claude/settings.json`, or a `CLAUDE.md` in the project.** Which plugins a
developer has enabled is their own machine's business, configured once in
`~/.claude/settings.json`, not something a scaffold decides on their behalf.

If the user *wants* the repo to carry a committed settings file so teammates get
these plugins on clone, that's a deliberate choice they make — point them at this
marketplace's `templates/project-settings.json` and let them opt in. Don't create
it as a side effect of scaffolding.

One consequence worth mentioning once, at step 6: the map cache lives at
`~/.claude/kaizen/`, outside the repo, so reading and writing it will prompt for
approval unless the user has allowed that path in their own settings. Say so
rather than letting the prompt surprise them.

## Rules to enforce everywhere

- **Never scaffold before Step 1 is answered.** The three answers change what
  gets built, not just how it's configured.
- **Never write a component before Step 2 exists.** This is the single rule the
  whole skill is built around.
- **Step 2 runs as a background sub-agent, not in-context.** It's a chained,
  non-interactive multi-skill sequence once Step 1 is answered.
- **Step 3+4 runs as one background sub-agent per side.** When the stack is
  "both," dispatch two `Agent` calls in the same message — frontend's
  bootstrap-then-architecture chain and backend's bootstrap-then-architecture
  chain — since neither side reads the other's output at this stage. Wait
  for both before continuing; if either result is missing or malformed, stop
  and surface it rather than proceeding to Step 5 on a guess. When the stack
  is single-sided, dispatch that one side's chain the same way, alone. Every
  other step (interactive, or a genuine single skill hop) stays in-context.
- **`modules/` stays empty** through kickoff.
- **Seed the map after a commit, never before.**
- **Never end a kickoff silently.** Step 7 names the first module, the testing
  layers, and the deployment shape decision — a project handed back as a bare
  skeleton with no idea what comes next is an incomplete kickoff, even when
  every earlier step was done correctly.
- **Never start step 7's work in the kickoff turn.** Naming those next moves is
  the deliverable; each one asks its own questions when its time comes.
- **Never write into `.claude/` or create a `CLAUDE.md`.** Plugin enablement is
  user-level configuration; a scaffold has no business setting it.
- **Every hand-off is to a skill that owns that step.** This skill does not
  write theme files, configs, or scaffolding itself — where it starts doing
  that, it has become a second source of truth for something another skill
  already owns.
- If a step's plugin isn't installed, say which step is being skipped and what
  the project is missing, rather than silently dropping it.

The full ordered sequence, the reasoning per step, and the partial-kickoff path
are in `references/kickoff-sequence.md`.

---
_Last reviewed: 2026-08-24_
