# architecture-foundations

Tier 1 plugin: framework- and stack-agnostic principles that a sibling
`frontend` plugin and a sibling `backend` plugin both build on, plus the two
entry points a project can arrive through — greenfield kickoff and existing-code
adoption. Holds no library-specific code. Depends on nothing (it names sibling
plugins' skills when routing, but works standalone if they aren't installed).

## Components

| Skill | Purpose |
|---|---|
| `clean-architecture` | The three-zone model (core/modules/shared), the one-way dependency rule, and how to spot module-level duplication that accumulated silently, independent of any framework. |
| `ui-architecture` | The three-zone model applied specifically to a UI app, in framework-neutral vocabulary (presentation units, composers, a logic layer) — a framework adapter (e.g. a sibling `frontend` plugin) translates this into its own concrete terms. |
| `state-philosophy` | Server-state vs. client-state, caching/invalidation, and optimistic updates as concepts — no specific library. |
| `test-pyramid` | Unit/integration/e2e shape and what belongs at each layer, independent of tooling. |
| `working-agreement` | How work gets done, independent of stack: verification is batched and asked for rather than run continuously, pre-existing problems near a change are surfaced rather than silently fixed, a model tier is recommended at decision points, and no implementation detail is assumed without checking existing docs or asking. Delivered as a `SessionStart` hook so the rules are in context *before* editing starts; the skill carries the reasoning and edge cases. |
| `project-kickoff` | **Greenfield orchestrator.** Owns the first hour of a new project: asks stack/product shape/design source up front, establishes the design system *before* any component exists (delegated to a background sub-agent — see Orchestration below), then routes to the framework bootstrap, the architecture skeleton, the API contract, and seeds the codebase-map cache. Writes nothing into the project's `.claude/` and creates no `CLAUDE.md` — plugin enablement stays user-level. |
| `existing-codebase-adoption` | The brownfield counterpart to `project-kickoff`. Decides, once, whether a project that already has its own structure for a discipline should adopt Kaizen's conventions or keep its existing ones — gated by `frontend-architecture`/`backend-architecture` (and, on a non-trivial edit, by this plugin's own `PreToolUse` gate — see Enforcement below) before any structural skill applies. Also triggers a sibling `codebase-map` plugin's scan as part of its own run, and keeps handling one-off inconsistencies found later during implementation the same way. |

## Setup

No external dependencies. Two things to know: this plugin ships a `SessionStart`
hook (`hooks/hooks.json` + `scripts/working-agreement.js`) that prints the
working agreement into context at the start of every session, and a
`PreToolUse` hook (`scripts/adoption-gate.js`, matcher `Edit|Write|NotebookEdit`)
that enforces part of it mechanically — see Enforcement below.

Those hooks are the whole delivery mechanism for `working-agreement` and the
adoption gate, and they only register when the plugin is installed properly via
`/plugin install`. For a manual skill-copy setup where plugin hooks don't
register, add them directly to `~/.claude/settings.json` instead (see
`scripts/working-agreement.js` and `scripts/adoption-gate.js` for the commands).
And because hooks register at install time, **editing a hook or its script
requires reinstalling the plugin** before the change takes effect.

Everything else in this plugin is pure conceptual knowledge with no scripts.

## Enforcement: the adoption gate

`working-agreement`'s rules are prose a model can choose to follow; one of them
— never editing an existing codebase before `existing-codebase-adoption` has run
— is mechanically enforced instead, via `scripts/adoption-gate.js`. On an `Edit`,
`Write`, or `NotebookEdit`, it resolves the touched file's discipline (frontend
vs. backend, via nearby manifests — `package.json`, `pyproject.toml`, `pom.xml`,
etc.), and blocks with a one-line message if that discipline has no
`~/.claude/kaizen/<project-key>/adoption.json` entry yet, the project has real commit history, and more
than ~20 tracked files already exist for that discipline. It fails open on
anything ambiguous — no resolvable discipline, no git repo, no `HEAD` yet, a
tiny scaffold, or any script error — so it can only ever block a genuine,
non-trivial existing codebase, never a greenfield one. Running
`existing-codebase-adoption` once per project/discipline satisfies it for every
later edit, this session and all future ones.

## Orchestration: what runs in-context vs. as a sub-agent

`project-kickoff` delegates its one purely mechanical multi-skill chain — the
four `design-system` skills in Step 2 — to a background sub-agent via the Agent
tool, once Step 1's answers are known, so those skills' combined bodies never
load into the orchestrating conversation. Step 3+4's bootstrap-then-architecture
chain is delegated the same way — as one background sub-agent per side, dispatched
as a parallel pair (two `Agent` calls in one message) when the stack is both
frontend and backend, since neither side depends on the other's output at that
point; a partial failure stops the sequence rather than guessing at the missing
side. Every other step either needs live user judgment (Step 0, Step 1) or is
already a single skill hop, and stays in-context. This is the template for any
future orchestrator in this suite that grows a multi-skill mechanical chain, or
a genuinely independent pair of them, of its own.

## Usage

- "Structure the app" / "where does this code belong" → `clean-architecture`
- "Structure my frontend/UI" / "how should I organize this UI app" → `ui-architecture`
- "Where should this state live" / "client vs server state" → `state-philosophy`
- "What should I test" / "testing strategy" → `test-pyramid`
- "Should I run the build" / "why didn't you lint" / "should I fix this dead code while I'm here" / "which model should I use" → `working-agreement`
- "Start a new project" / "bootstrap a new build" / "set up a new app from scratch" → `project-kickoff`
- "This project already has a frontend/backend" / "should I follow this repo's conventions or Kaizen's" → `existing-codebase-adoption`

`project-kickoff` and `existing-codebase-adoption` are the two doors into a
project and are mutually exclusive per discipline: greenfield goes through the
first, pre-existing code through the second. A half-and-half repo (an existing
backend, a brand-new frontend) uses one per side.
