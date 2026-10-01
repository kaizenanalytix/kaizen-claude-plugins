---
name: codebase-map-sync
description: >
  Maintains a per-machine cache of codebase structure facts and a
  one-line-per-file/per-folder description tree
  (~/.claude/kaizen/<project-key>/codebase-map.json) — stack,
  module/route layout, naming conventions, and a navigable file tree with
  purpose notes — refreshed via a git-SHA checkpoint so callers get
  current facts without re-reading the whole codebase every session. Use
  when the user says things like "map this codebase", "what's the
  structure here", "what does this project actually look like", or when a
  discipline orchestrator skill (e.g. frontend-architecture,
  backend-architecture) needs to know what exists before scanning anything
  itself. Also invoked by a sibling architecture-foundations plugin's
  existing-codebase-adoption skill as part of its own run, so any project
  that goes through that decision also ends up mapped.
---

# Codebase Map Sync

A discipline skill that re-derives "is this React, what modules exist, what
naming is in use, what does each file actually do" from scratch every
session is doing the same read-only work over and over. This skill trades
that for one fact-plus-description cache (`codebase-map.json`), refreshed
against a checkpointed SHA instead of a full re-scan.

This skill is discipline-agnostic on purpose: it doesn't care whether the
caller is `frontend-architecture`, `backend-architecture`, both, or neither.

The cache lives in a unified per-machine root, not inside the project
itself: `~/.claude/kaizen/<project-key>/codebase-map.json`, where
`<project-key>` is the repo's folder name plus a short hash of its absolute
path (e.g. `ka-optistream-frontend-a1a0f0`), so two checkouts that share a
folder name get separate maps. The SessionStart hook prints the exact path;
write to that one. A map found under the bare folder name
(`~/.claude/kaizen/<folder-name>/`) is the legacy location: it is read once
as a starting point, and the next write goes to the keyed path. This mirrors where this
library's skills themselves live (`~/.claude/skills/`) — reachable by Claude
regardless of which project folder is currently open, without needing every
project to share a common parent directory. All git commands below
(`git rev-parse HEAD`, `git merge-base`, `git diff`) still run against the
project's own repository; only the cache file itself lives outside it.
Because this cache is per-machine, it is not something teammates share with
each other — each developer gets their own.

## 1. Confirm the artifact exists, bootstrap if not

Check for `~/.claude/kaizen/<project-key>/codebase-map.json`. If it's
missing, this is first adoption:

- Ask the user directly for permission before reading anything: "There's no
  cached map of this codebase yet — scan it now to build one? This reads
  every source file once to write a short description of each, so future
  sessions can jump straight to the right file instead of re-reading the
  whole repo." Don't scan first and ask later — this first scan is real
  work, not a cheap signals-only pass, so the user should know that before
  it starts.
- If they agree, gather two kinds of facts:
  - **Repo-level facts** (cheap, from manifests): stack + key deps from
    `package.json`/`pyproject.toml`/`requirements.txt`; top-level
    module/route folder names per discipline present (e.g. `modules/*`
    under a React or FastAPI app); naming conventions actually observed
    (file casing, a naming pattern that's consistently followed).
  - **The tree** (the real cost): walk every source folder and file under
    each discipline's module/route root, skip generated output
    (`dist/`, `build/`, `node_modules/`, lockfiles) and binary/asset files,
    and for each file write one short line — its actual purpose (main
    export, what it renders/handles/calls), not a restatement of its
    filename. For each folder, write one short line summarizing what the
    files inside it are collectively for. Ground every line in an actual
    look at that file — skim for exports, top-level function/component
    names, and any header comment; never fabricate a description from the
    filename alone.
- Create `~/.claude/kaizen/<project-key>/` if it doesn't exist yet, then
  write `codebase-map.json` there with `last_scanned_sha` set to the current
  `HEAD` of the project's own repo (see the schema in step 4).
- If the scan turns up frontend or backend code that predates this library's
  own conventions, record that as a fact
  (`disciplines.<name>.predates_kaizen: true`) but do not ask the user to
  choose between adopting or deferring to it — that decision belongs to a
  sibling `architecture-foundations` plugin's `existing-codebase-adoption`
  skill, not this one. Recording the fact is enough; let the caller route
  there.

### Seeding a project that was just scaffolded

The permission prompt above exists because a first scan of an unknown repo is
real work. That reasoning doesn't hold when the repo is a skeleton that was
created moments ago — a bootstrap skill's output is a couple of dozen files
whose purpose is already known, so there is nothing expensive to warn about.

When this skill is invoked as part of a greenfield kickoff — a sibling
`architecture-foundations` plugin's `project-kickoff` skill calls it at step 6,
right after the framework bootstrap and the initial commit — skip the
permission prompt and seed the cache directly.

Keep the condition narrow: *this session just scaffolded this project*. A repo
that merely looks small, or one opened for the first time, still gets the
prompt. The prompt protects against an unexpected expensive scan, and only a
just-created skeleton is reliably not one.

Seeding here is worth the step precisely because the alternative is worse: the
first scan otherwise lands months later against a mature repo, at which point
it's expensive enough that it keeps getting declined.

### When a project already has its own index — defer

Some projects already carry a hand-maintained structural index: a project-specific
skill, or a `CLAUDE.md` that documents the real structure, stack, commands, and
conventions. Those exist for exactly the reason this cache does — so nobody has to
re-scan the repo — and they're usually richer, because a person wrote them with
knowledge no file scan can recover.

Where one exists, **say so and don't build a competing map unless the user asks for
one anyway.** Two indexes disagreeing is worse than one that's occasionally out of
date, and the hand-written one will win any argument about which is right.

Two other cases where this skill simply doesn't apply, and should say so rather than
improvise:

- **No git repository.** The checkpoint is a commit SHA; without one there is nothing
  to invalidate against, so a cache here could never be known to be stale.
- **A workspace of several independent repos opened at their shared parent.** The cache
  is keyed by the current folder's name and all git commands run against one repo — so
  map each project from inside that project, not from the parent folder.

### A repo with no commits yet

`git rev-parse HEAD` fails in a repository with zero commits, so
`last_scanned_sha` cannot be filled in. Do **not** write the cache with a null,
empty, or placeholder SHA: the checkpoint logic in step 2 has no way to
validate such a value, so every later session would treat the cache as
permanently stale — or, worse, silently trust facts it can never verify.

Say plainly that the map will be seeded once the first commit exists, and defer.
A caller running the kickoff sequence should commit first and then invoke this
skill; that ordering is specified in `project-kickoff`'s step 6.

## 2. If the artifact already exists, check the checkpoint

Run `git merge-base --is-ancestor <last_scanned_sha> HEAD` against the
project's own repo, the same robustness check `checkpoint-catchup` uses for
rebases and force-pushes:

- **Same SHA already** → check `git status --porcelain` before trusting it.
  Editing a file doesn't move `HEAD`, so a matching SHA on a dirty working tree
  means the cache describes the last commit, not what's on disk. If files are
  modified, re-describe those files (same as the ancestor case below) but leave
  `last_scanned_sha` alone — it still records the commit the rest of the tree was
  scanned at, and overwriting it with the same value would falsely imply the
  uncommitted work had been checkpointed. On a clean tree, return the cached facts
  and tree as-is, no files read.
- **Ancestor (normal forward progress)** → run
  `git diff --name-only <last_scanned_sha> HEAD` to see what actually moved.
  Re-describe only the changed/added files (and their immediate parent
  folder's summary if its contents shifted enough to matter), remove
  entries for deleted files/folders, refresh any repo-level facts a changed
  manifest affects, then bump `last_scanned_sha` to the current `HEAD`.
  Never re-describe files that didn't change — that defeats the entire
  point of checkpointing.
- **Not an ancestor (history was rewritten)** → the checkpoint's base no
  longer exists in history. Fall back to a fresh full scan using the same
  approach as step 1, and treat it as a reseed rather than trying to diff
  against a SHA that's gone.

## 3. Hand back the facts

Whatever path was taken, the caller (typically a discipline orchestrator
skill, or the user directly) gets the current `disciplines` object —
including the `tree` — back and proceeds with its own work using those
facts and descriptions instead of independently checking `package.json`,
walking module folders, or opening files to see what they do.

**Consulting the cache cheaply:** when the goal is finding one specific file
or feature (not a full architectural picture), grep inside
`codebase-map.json` for a keyword instead of reading the whole file — e.g.
`grep -i "kpi" codebase-map.json` returns the exact matching `"file.ext":
"description"` line directly, since every entry sits on its own line. This
is cheaper than reading the entire cache and often cheaper than a fresh
Grep/Glob pass over the real source tree, since the hit already comes with
a description, not just a path. Only read the full file when the task
actually needs the broader picture (e.g. an architecture decision, or
listing everything in a module).

**Adding a new file:** when it should follow an existing sibling's pattern
(e.g. "add another drill panel like the others"), use the tree's one-line
descriptions to compare every candidate sibling cheaply and pick the single
closest match — don't open multiple candidates to decide between them.
Then `Read` only that one winning file as a pattern reference (imports,
prop shapes, composition style) before writing the new file. A one-line
description is never enough to write idiomatic new code from directly; it
only tells you which single file is worth actually reading.

## 4. Schema

```json
{
  "last_scanned_sha": "a1b2c3d4e5f6...",
  "scanned_at": "2026-08-06",
  "disciplines": {
    "frontend": {
      "stack": "react",
      "key_deps": ["react", "react-router-dom", "@reduxjs/toolkit"],
      "modules": ["products", "orders"],
      "naming_observed": "PascalCase components, camelCase hooks",
      "predates_kaizen": false,
      "tree": {
        "src/modules/products": {
          "desc": "Products module: listing page, product card, and the RTK Query API slice for product data.",
          "files": {
            "ProductList.tsx": "Page component rendering the paginated product grid.",
            "ProductCard.tsx": "Single product card: image, price, add-to-cart button.",
            "productsApi.ts": "RTK Query API slice for product list/detail endpoints."
          }
        }
      }
    },
    "backend": {
      "stack": "fastapi",
      "key_deps": ["fastapi", "sqlalchemy"],
      "modules": ["products", "orders"],
      "naming_observed": "snake_case modules and files",
      "predates_kaizen": false,
      "tree": {
        "modules/products": {
          "desc": "Products domain module: routes, service orchestration, and the SQLAlchemy repository.",
          "files": {
            "api.py": "APIRouter with the product list/detail/create endpoints.",
            "service.py": "Business logic orchestrating repository calls and validation.",
            "infra.py": "SQLAlchemy repository implementation for the product table."
          }
        }
      }
    }
  }
}
```

Omit a discipline key entirely if that discipline isn't present in the repo
— don't write an empty placeholder object for it. `tree` keys are folder
paths relative to the project root; nest sub-folders as their own `tree`
entries rather than flattening deep paths into one key.

## 5. Rules to enforce everywhere

- Never do a full-repo re-read when the checkpoint is already current, and
  never re-describe an unchanged file on an incremental update — both
  defeat the entire point of this skill.
- Never fabricate a fact or a file/folder description; every entry must
  come from an actual scan of that file, not a guess from its name or path.
- Keep each description one short line — a pointer for an agent deciding
  where to look next, not a summary of the file's full contents.
- Never write new code by inferring its shape from a one-line description
  alone — descriptions are for choosing which single file is worth reading,
  never a substitute for reading it.
- This file lives under `~/.claude/kaizen/<project-key>/`, never inside the
  project's own directory. It is a per-machine cache, not a team-shared
  artifact.
- This skill owns facts only. It never asks the user to choose between
  adopting this library's conventions or an existing structure — that
  decision, and its persistence, belongs to a sibling `architecture-foundations`
  plugin's `existing-codebase-adoption` skill.

---
_Last reviewed: 2026-08-24_
