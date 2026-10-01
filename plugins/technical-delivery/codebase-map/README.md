# codebase-map

For any discipline working on a project: a lightweight, per-machine cache of
codebase structure facts (stack, modules/routes present, naming conventions
observed) plus a one-line-per-file/per-folder description tree, refreshed via
a git-SHA checkpoint instead of a full re-read every session.
Discipline-agnostic — works the same whether the codebase is `frontend`,
`backend`, both, or neither. Depends on nothing at runtime — no dependency on
`frontend`, `backend`, or `architecture-foundations` in either direction.

## Components

| Skill | Purpose |
|---|---|
| `codebase-map-sync` | Reads (or bootstraps) `~/.claude/kaizen/<project-key>/codebase-map.json`; if the checkpointed SHA is stale, rescans only what changed and updates it, so callers get current facts and a navigable file tree without a full-repo read. Seeds without a permission prompt when a greenfield kickoff has just scaffolded the repo, since a fresh skeleton is nothing to warn about. |

## Setup

Nothing beyond a git repo. The cache lives at
`~/.claude/kaizen/<project-key>/codebase-map.json` — a unified, per-machine
location keyed by folder name plus a short hash of the repo path (so two
checkouts named `frontend` don't collide), not a file inside the project itself,
so it isn't shared across teammates (each developer gets their own). This
skill only maintains facts about what exists; it does not decide whether a
project should adopt this library's conventions (that's a sibling
`architecture-foundations` plugin's `existing-codebase-adoption` skill's job,
gated by both `frontend-architecture` and `backend-architecture`).

A `SessionStart` hook (`hooks/hooks.json` + `scripts/load-cache.js`) can
surface a short pointer to the cache automatically at session start when this
plugin is properly installed via `/plugin install`. For personal/manual
skill-copy setups where plugin hooks don't register, add the hook directly to
`~/.claude/settings.json` instead (see `scripts/load-cache.js` for the
command to run).

### Permissions

The cache deliberately lives outside the project, so reading and writing it
prompts for approval every session unless the consuming repo allows it up
front. Add this to that repo's committed `.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Read(~/.claude/kaizen/**)",
      "Write(~/.claude/kaizen/**)",
      "Edit(~/.claude/kaizen/**)"
    ]
  }
}
```

Use the `~/` prefix, never an absolute `//c/Users/<name>/...` or
`/home/<name>/...` rule. `~/` resolves per-user on every OS, so one committed
file works for the whole team; an absolute rule silently grants nothing on
every machine but the one it was written on. A ready-made version of this
block ships in `templates/project-settings.json` at the marketplace root.

## Usage

- "Map this codebase" / "what's the structure here" → `codebase-map-sync`
- Any discipline orchestrator skill (e.g. `frontend-architecture`,
  `backend-architecture`) about to start work → consults `codebase-map-sync`
  first for cached facts instead of re-deriving them from scratch
- A new project being scaffolded → a sibling `architecture-foundations`
  plugin's `project-kickoff` skill seeds the cache at its step 6, after the
  initial commit. The seed is nearly free at skeleton size, which is the point:
  the first scan otherwise lands months later against a mature repo, when it's
  expensive enough to keep being declined.

**The cache needs a commit to key against.** `last_scanned_sha` comes from
`git rev-parse HEAD`, which fails in a repo with zero commits — so seeding
happens after the initial commit, never before. The `SessionStart` hook reports
that case distinctly rather than misreporting it as a force-push.
