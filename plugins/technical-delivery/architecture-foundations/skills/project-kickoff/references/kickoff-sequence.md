# The kickoff sequence

The full ordered table, why each step sits where it does, and how to handle a
project that is only partly greenfield.

## The sequence

| # | Step | Owned by | Why here and not later |
|---|---|---|---|
| 0 | Confirm greenfield | this skill | Applying a greenfield sequence to an existing repo means fighting its structure for the rest of the project. |
| 1 | Ask stack / product shape / design source | this skill | All three change *what* gets built. Guessing means rewriting, not adjusting. |
| 2 | Design system | `design-system` plugin | The one step that becomes near-impossible later. See below. |
| 3+4 | Bootstrap + architecture skeleton, per side | `react-project-bootstrap`→`frontend-architecture` / `fastapi-project-bootstrap`→`backend-architecture` | Each needs the stack answer from step 1 and consumes the theme from step 2; the first module copies whatever shape exists when it's written. When the stack is "both," neither side's chain reads the other's output, so both dispatch as parallel background sub-agents rather than running one after the other. |
| 5 | API contract (only if both sides) | `api-contract` → `contract-first` | Cheap while there are zero endpoints; a migration once there are forty. |
| 6 | Seed the codebase map | `codebase-map` → `codebase-map-sync` | A skeleton scans in seconds. A mature repo doesn't, which is why the first scan otherwise never happens. |
| 7 | Name what comes next | this skill (points only, builds nothing) | A skeleton with empty `modules/` has no tests and no way to ship. Naming the first module, the testing layers, and the deployment shape decision keeps them from being orphaned — the deployment one especially, since its shape decision follows exactly the cheap-now/expensive-later logic this whole table is ordered by. |

Steps 0–6 build; step 7 only points, and starts nothing in the same turn.
The build sequence stops there. There is no step that writes into the project's
`.claude/` directory or creates a `CLAUDE.md` — see "What this skill does not
write" in `SKILL.md`. Enabling plugins is user-level configuration
(`~/.claude/settings.json`), and a scaffold shouldn't decide it for whoever
clones the repo next.

## Why step 2 is the one that can't move

Steps 3–7 are all recoverable. A bootstrap can be redone, an architecture can
be refactored, a contract can be introduced late, a map can be seeded whenever.

Step 2 is different, because it isn't undone by editing a config file — it's
undone by editing every component that was written before it existed. And that
cost scales with how successful the project is: the more it ships, the more
expensive its own design debt becomes to service.

The concrete failure, in order:

1. No scale exists, so a developer needs a size and picks `13px`. Reasonable.
2. Another developer, another component, picks `14px` for the same kind of
   text. Also reasonable — there was nothing to consult.
3. Repeat across a year and a team. The app now has a dozen near-identical
   sizes, four blues, and three card shadows.
4. Someone asks to darken the brand colour, and it is now a multi-day audit
   across every file rather than a one-line edit.

Nothing in that sequence is a mistake by anyone. It's the guaranteed outcome of
starting without a scale — which is why the scale comes before the first
component, not after the first complaint.

## Partial kickoff

Real projects are frequently half-greenfield: an existing FastAPI service that
needs a new React frontend, or an existing UI that needs its first real backend.

Handle each discipline on its own track:

- **The existing side** → a sibling `architecture-foundations` plugin's
  `existing-codebase-adoption` skill decides adopt-vs-defer, once, and records
  it in `.kaizen/adoption.json`. This kickoff skill does not touch that side.
- **The new side** → the full sequence above, minus the steps the repo already
  has.

Which steps still apply when only the frontend is new:

| Step | Applies? |
|---|---|
| 1 — Ask scope | Yes, but the stack answer is already known; still ask product shape and design source. |
| 2 — Design system | **Yes.** A new frontend needs its foundation regardless of the backend's age. |
| 3 — Bootstrap | Yes, frontend only. |
| 4 — Architecture | Yes, frontend only. The backend keeps whatever `existing-codebase-adoption` decided. |
| 5 — Contract | Yes — this is exactly when a contract earns its keep, since the backend's shapes already exist and are about to be consumed by a second codebase. |
| 6 — Seed the map | Yes. The repo is bigger, so the scan costs more, but it's still the cheapest it will ever be. |

Mirror this for a new backend against an existing frontend, dropping step 2
(the design system belongs to the frontend that already has one).

## When to stop and ask instead of proceeding

- Step 1's answers conflict with what's on disk — e.g. "frontend only" in a
  repo that already has a `pyproject.toml`. Surface the contradiction; don't
  pick one.
- The design source is "an existing Kaizen app" but that app's theme file
  can't be located. Ask for the path rather than generating a fresh palette —
  a near-miss palette is worse than an obviously-new one, because it looks
  intentional.
- The stack is a thin adapter, not the deep React/FastAPI one (Vue, Angular,
  Node.js, NestJS, Django, Java/Kotlin). Steps 1, 2, and 6 still apply
  unchanged, and step 3+4 has an owner — the matching `<stack>-architecture`
  skill in `frontend`/`backend` — but that skill has no bootstrap step of its
  own yet. Say so plainly and let the user drive the framework bootstrap by
  hand before handing off to the architecture skill for the zone layout.
- The stack is something none of the above covers (Go, Ktor outside a
  Java/Kotlin context, etc.). Steps 1, 2, and 6 still apply — the
  design-system skills are framework-neutral by design. Step 3+4 has no
  owner at all; say so plainly and let the user drive both the bootstrap and
  the architecture decision.

---
_Last reviewed: 2026-08-24_
