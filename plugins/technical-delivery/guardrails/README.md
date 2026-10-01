# guardrails

Tier 0 plugin: the authority layer under every other plugin in this marketplace. Defines what the
agent may do on its own, and what it must put in front of the user first. Holds no
stack-specific knowledge and depends on nothing — every other plugin references its rules by ID,
and each of them still works if this one isn't installed.

Where the other technical-delivery plugins answer *how do I build this well*, this one answers *how much rope
does the agent have while doing it*.

## Components

| Skill | Purpose |
|---|---|
| `guardrails` | **The catalog.** 56 rules across seven ID'd families — C (consent), P (preview before permission), D (data and destructive operations), V (verification and the failure loop), O (orchestration), S (scope), T (transparency) — tiered Hard/Soft/Guidance, plus the X1 override rule and an error-handling table. A reference skill: it generates nothing. Other skills point at it by ID rather than restating it. |
| `permission-preview` | **The P and D families in practice.** The six-field preview block, the read-only probe table (what to run before a write, per database client), resolving what a connection string actually points at, the three reversibility verdicts, and the field nothing else in the toolchain provides — what a standing "always allow" would authorise for the rest of the session, versus a one-time yes. Ships six complete worked examples. |
| `failure-triage` | **The V family.** What to do when a test, build, or command fails: quote the real output, sort it into test-was-wrong / real-defect / genuinely-ambiguous, present the hypothesis report *as a hypothesis*, and ask before changing code. Plus the two-attempt cap and the list of ways to force a test green that are never available. Stack- and tooling-agnostic — the general form of a rule a sibling `e2e-testing` plugin applies to Playwright runs. |
| `question-protocol` | **The C family.** How to ask: batched multiple-choice with consequences and a recommendation, understanding restated first, defaults stated out loud when taken, ambiguity re-asked rather than resolved. Includes what does *not* deserve a question, so the asking stays calibrated, and what "stop asking me" actually means. |
| `subtask-orchestration` | **The O family.** A lead that owns a dependency **graph**, specialist agents each handed only their predecessors' handover packets, an independent reviewer per node, and bounded retry loops — built on the Workflow tool, where `schema` enforces the packet and `isolation: 'worktree'` stops concurrent implementers corrupting each other. Decompose into subtasks small enough for one context, checkpoint the plan, dispatch with acceptance criteria declared up front, verify results against those criteria rather than against how the summary reads, memoise verified subtasks to `~/.claude/kaizen/<project-key>/orchestration/` so a retry reuses finished work, and ask before spending another agent. The generalised form of the sub-agent pattern `project-kickoff` uses. |

## Setup

No external dependencies. The plugin ships six hooks (`hooks/hooks.json` plus six plain
CommonJS scripts using node builtins only) — see Enforcement below. Because hooks register at
install time, they only take effect once the marketplace is installed via `/plugin install`, and
editing one requires reinstalling before the change applies.

Two optional settings changes make the guardrails bind harder, both in
`templates/project-settings.json` for repos that adopt it:

- **`permissions.deny`** on `.env*`, private keys, `.git/**`, and `credentials*` — enforces D6
  natively, at zero cost, covering `Read` as well as `Write`/`Edit`.
- **`permissions.ask`** on `npm publish`, `docker system prune`, `kubectl delete`,
  `git push --force`, and writes to `.claude/**` — these are acts where no meaningful preview
  sample exists, so a native prompt gives the guarantee that a preview can't.

Both are opt-in: that template is copied manually into a product repo, and nothing in this
marketplace writes it for you.

## Enforcement — six hooks

| Hook | Event / matcher | What it does |
|---|---|---|
| `scripts/guardrail-contract.js` | `SessionStart` `*` | Prints the four load-bearing rules **plus the skill-routing table** (~660 tokens, once per session). Exits 0 unconditionally. |
| `scripts/scope-first.js` | `UserPromptSubmit` `*` | **Gates** every non-trivial request behind a scope block — understood / what I'd build / not doing / unpinned / which skill — then stops for a go-ahead. Adds a staging note when the ask sweeps across many files. ~250 tokens, silent on trivia. |
| `scripts/preview-gate.js` | `PreToolUse` `Bash\|PowerShell` | Blocks a destructive or database-writing command until a preview has actually been shown to the user. Blocks `git commit` / `push` / `merge` / `rebase` and `gh pr create` **outright** — no preview unlocks those. Exit 2 + stderr; the stderr text *is* the guardrail. |
| `scripts/agent-dispatch-gate.js` | `PreToolUse` `Agent\|Task` | Refuses a substantial sub-agent dispatch that declares no acceptance criteria — nothing could verify what comes back. Recon and short dispatches pass untouched. |
| `scripts/write-gate.js` | `PreToolUse` `Edit\|Write\|NotebookEdit` | **Blocks database work** — migrations, SQL, ORM models, seeds, connection config, or any file whose new content writes raw SQL — until a scope block has been shown and the user has answered it. Ordinary code is not gated. |
| `scripts/failure-triage.js` | `PostToolUse` `Bash\|PowerShell` | When a test/build/lint run fails, injects the triage contract before the model can react. Exit 0 + `hookSpecificOutput.additionalContext`, so a failing test isn't framed as a hook error. |

### Strict where data is, quiet everywhere else — and no git publishing (0.9.0)

**The bug.** In a long session, `write-gate.js` started blocking ordinary edits to work the user
had already approved. The cause was in `lib/transcript.js`: the harness records text it injects,
such as image reads, `<system-reminder>`s, skill loads and command stdout, as `type:"user"` entries
with a text first block. `isRealUserTurn` counted them as the user speaking, so each one moved the
write-gate window past the approval. The same miscount let an injected message stand in for the
user answering a **database preview**, which weakened the gate that matters most. Entries marked
`isMeta` / `isCompactSummary`, or starting with a known injected prefix, no longer count as user
turns, and a real prompt with a reminder in front of it still does.

**Scope.** Even with that fixed, hard-gating every edit was more friction than the team wanted.
`write-gate.js` now blocks only **database work**, found by project-relative path (`migrations/`,
`alembic/`, `db/`, `prisma/`, `*.sql`, `models.py`, Flyway `V1__*`, `alembic.ini`, `knexfile`, …)
or by the content being written (DDL, `DELETE FROM` / `INSERT INTO` / `UPDATE … SET`, SQLAlchemy /
Django / TypeORM / Mongoose model declarations, engine setup, `DATABASE_URL` and connection-string
URLs). Prose files (`.md`, `.txt`) are never content-matched. For everything else the
`scope-first` prompt still asks for a plan, but only as advice.

**Git.** The agent never commits, pushes, merges, rebases, cherry-picks, or opens/merges a PR.
These are classified `git-publish`, checked *before* the read-only probe list (otherwise `git
commit -m "$(cat <<EOF…)"` would pass as a probe because of `cat`), and blocked with no preview
path and no fail-open. `allow_patterns` does not lift the block. Only turning the plugin off
(`KZ_GUARDRAILS=off` / `enabled:false`) does. The block message tells the model to hand over the
commit message or PR description as text, with **no Claude/AI attribution** of any kind. `git add`,
`git stash` and `git checkout -b` are unaffected.

**PowerShell.** The Bash gates also match `PowerShell` now. It is the primary shell on Windows,
and a database write through it used to skip the preview gate completely. The classifier also
handles `& "C:\…\psql.exe"`, `.exe` suffixes, and `Invoke-Sqlcmd`.

To stop the harness asking for attribution lines in the first place, also set this in
`~/.claude/settings.json`:

```json
"includeCoAuthoredBy": false,
"attribution": { "commit": "", "pr": "" }
```

### The stop scales to the change (0.8.0)

C1 always stops, but **C9** sizes the *form* of that stop — P8's counterpart for consent. A
one-property, single-file, trivially-reversible change whose diagnosis is already agreed gets one
line rather than five fields:

> Step 10's placement `'top'` → `'bottom'`. One property, reversible. `'auto'` is the alternative
> — I'd take `'bottom'`, the target is too tall for flip to resolve. Then I'll check it in the
> browser. Go?

Still a gate. `write-gate.js` accepts `PROPOSED CHANGE` as a scope marker so the short form is
actually usable — without that, the user approves the one-liner and the edit gets blocked anyway,
forcing the long form back.

`scope-first.js` also stopped firing on recall. "Give me the list", "explain how X works", "how
many hooks are there" produce an answer, not a deliverable, and a block on those is the noise that
trains people to skip it. Recall phrasing wrapped around a real deliverable still gates — "give me
an artifact of each guardrail" is work.

### The Agent gate matches prose, and that is a real limitation (0.7.0)

`agent-dispatch-gate.js` refuses a sub-agent dispatch with no acceptance criteria, because nothing
downstream can verify what comes back (O4) and a plausible summary then passes for completed work.

But it matches on the **shape of prose inside a prompt** — it cannot tell a good criterion from a
bad one, only that the dispatch says "done when" somewhere. `DONE WHEN: it works` satisfies it. It
is deliberately tuned to be nearly false-positive-free rather than thorough: short prompts pass,
read-only recon passes, any of several markers satisfies it, and everything ambiguous fails open. A
gate that blocks a legitimate dispatch is worse than one that misses a sloppy one, because the
first is what makes people disable the plugin.

### Why the scope block needed a second hook (0.6.0)

`UserPromptSubmit` is **advisory** — it injects context, it cannot stop a turn. So
*"do NOT start building"* was a request the model could read and then ignore, which is exactly
what "it isn't following it" means in practice. Only `PreToolUse` can actually block.

`write-gate.js` closes that. It asks the transcript the same unforgeable question the preview gate
asks: **did a scope block appear before the user's last turn?** If the user asked and the model
went straight to writing, there is no scope block in that window and the write is blocked.

The window is what keeps it to one stop per piece of *work*: once approved, the model writes ten
files with no new user turn in between, so the window never moves and every write passes. When the
user says "now add payments", the window slides past the old approval and the next write blocks
until the new work is scoped.

The subtlety that an earlier draft got wrong: with only **one** user turn it treated the history as
too short to judge and failed open — which meant the first request of every session was never
gated, i.e. precisely the case this exists for.

### Why routing and the scope block are hooks, not rules

Skill auto-matching is probabilistic, and several skills legitimately claim the same words —
`clean-architecture` and `backend-architecture` both answer *"where does this code belong"*, and
both are right. No description can resolve that; only a table stating precedence can, which is
why `guardrail-contract.js` carries one with explicit tie-breaks.

**The scope block is a gate, not a preamble (0.4.0).** It used to end "then proceed if it's
clear" — which made it a report, not a gate, since *"it seemed clear to me"* is precisely the state
in which a misread premise gets built on. Now it stops and waits for a go-ahead, and this applies
to implementation itself, not only to commands and database writes: **nothing gets built silently.**
Paired with C8, no assumptions — a detail the user hasn't given and the repo's docs don't answer
becomes a question, never a quiet default.

The cost is one confirmation round-trip at the start of each piece of work. The bound that keeps
that usable is **one stop at the start, not a stop per file**: once a plan is approved, the whole
thing gets built without re-asking, and "just do it" is itself the go-ahead.

The scope block has a sharper version of the same problem. *"Whatever the user asks, first say
what you'd work on"* can never be triggered by description matching, because it has to apply to
requests that match nothing. `UserPromptSubmit` is the only event that fires on every message
regardless of content.

`scope-first.js` deliberately stays silent on short asks, acknowledgements, and definitional
questions. A scope block on *"what does D3 mean"* is noise, and noise is how a standing
instruction gets trained out of usefulness — the user starts skipping past it, and then it isn't
there for the request that needed it.

**Bulk work stages, pilot first (0.5.0).** A change repeating across more than about five files
applies to **one** first, shows the real diff, and confirms the pattern before the rest — then
proceeds in batches grouped by something meaningful. Writing a script does not exempt it; a script
enlarges the blast radius, it does not shrink the review. This plugin's own history is the worked
example: stamping a guardrail reference into 53 `SKILL.md` files went out as a single scripted
pass. It happened to be right. Had the insertion point been wrong, that would have been 53 broken
files in one commit.

### How the preview gate knows a preview happened

This is the design's load-bearing decision. If the gate simply blocked, the model would preview,
retry, and be blocked again forever. So it has to distinguish "a preview happened" from "it
didn't" — and **everything the model can write by itself is an attestation it can satisfy inside
the same turn without a human ever seeing anything.** A state file, a sentinel in the command, a
marker in the description: all worthless here.

What the model cannot fabricate is a *user turn*. So the gate reads the transcript and looks for
an assistant message containing the preview heading and this command, followed by a **real user
turn**, before the tool call. "A human got a turn between seeing the exact command and it running"
is the only unforgeable signal available.

The subtlety that decides whether this works: **tool results are also recorded as `type: "user"`.**
A real user turn is one whose content is a plain string or whose first block is `type: "text"`.
Count a tool result as the user answering and the gate silently stops enforcing anything — which
is why `selftest.js` tests that case specifically.

**It enforces that a preview happened, not that it was good.** The model can print the heading,
three lines of nothing, and get a user turn. Preview *quality* is what the `permission-preview`
skill and its worked examples are for.

### Read-only probes are never blocked

The gate orders the model to produce a preview containing real probe output. If it blocked the
probes themselves — `SELECT count(*)`, `EXPLAIN`, `terraform plan`, `--dry-run`, `alembic
upgrade --sql` — the model could not produce the preview it is being ordered to produce, and the
loop would be unbreakable. `PROBE_PATTERNS` in `lib/classify.js` exists entirely to prevent that,
and it is checked before anything else.

One real subtlety, caught by the self-test: `EXPLAIN UPDATE …` is a query plan and safe, but
`EXPLAIN ANALYZE UPDATE …` actually **executes** the write. `ANALYZE` anywhere disqualifies the
probe claim.

### Escape hatches — none need a reinstall

1. **`KZ_GUARDRAILS=off`** — per-machine or CI. Required for headless `claude -p`, where a
   deny-loop is unrecoverable because no human can answer.
2. **`~/.claude/kaizen/<project-key>/guardrails.json`** — per user and per checkout, never
   inside the repo. `<project-key>` is the folder name plus a short hash of the repo path;
   `node scripts/lib/project-key.js` prints the folder. A legacy `<repo>/.kaizen/guardrails.json`
   is still read when the user-level file doesn't exist:
   ```json
   {
     "enabled": true,
     "muted_until": null,
     "allow_patterns": ["^npm run db:seed$", "^make reset-local$"],
     "extra_patterns": ["^\\./scripts/deploy-prod\\.sh"]
   }
   ```
   `allow_patterns` is the important one — it's how a team whitelists its own safe wrapper
   scripts, which is the only real answer to the `make migrate` blind spot below.
3. **The native permission dialog**, which is the per-command override and is better at that job
   than anything this plugin could add.

**A muted guardrail is never a silent one** — `SessionStart` prints a `GUARDRAILS ARE OFF` warning
whenever any of these is active. Note that the model can write `muted_until` itself; the mitigation
is that the write is visible in the transcript and the next session announces it.

### Run the self-test after any Claude Code upgrade

```bash
node guardrails/scripts/selftest.js      # 174 checks
```

**This is not optional hygiene.** The gate's most likely failure is silent: it depends on the
transcript JSONL format, and if that changes the gate fails open — turning the guardrail off with
no error anywhere. The `TRANSCRIPT` section of the self-test is the only thing that will surface
it. If those cases fail, fix `textOf`/`roleOf`/`isRealUserTurn` in `preview-gate.js`.

### Known gaps, recorded rather than discovered later

- **MCP database tools bypass all of it.** `mcp__postgres__query` and similar never touch `Bash`,
  so no Bash hook sees them. The P and D rules still apply — they're simply unenforced there.
- **Wrapper scripts are opaque.** `make migrate-prod` hides whatever it calls. There's a
  whole-word heuristic on `npm`/`make`/`task` targets matching
  `migrate|deploy|reset|seed|drop|prune|wipe|restore`, but `allow_patterns` is the real answer and
  it needs a human to write it once per repo.
- **Cost:** two node spawns on every `Bash` call, roughly 120–180 ms, dominated by Windows node
  cold start. Zero tokens when the hooks stay quiet.
- **Hooks register at install time**, so editing one has no effect until the marketplace is
  reinstalled — unlike a `SKILL.md` edit, which is picked up next session.

## Usage

- "What are the guardrails" / "why did you ask me that" / "what does D3 mean" → `guardrails`
- "What happens if I allow this" / "show me before you run it" / "what will this delete" → `permission-preview`
- "The test is failing" / "just make it pass" / "you keep trying the same thing" → `failure-triage`
- "Stop asking me so much" / "you should have checked first" / "I don't know, you pick" → `question-protocol`
- "Break this into smaller pieces" / "use subagents" / "the agent ran out of context" → `subtask-orchestration`

## How other skills reference these rules

Skills do not restate the rules. They carry a one-line reference after their opening paragraph:

```markdown
> **Guardrails:** follows the shared guardrails (C/P/D/V/O/S/T) defined in a sibling
> `guardrails` plugin's `guardrails` skill — ask before consequential acts, preview any command
> before requesting permission, and never resolve a failure by assumption. If that plugin isn't
> installed, those rules still stand; this skill just can't point at their full text.
```

A skill adding a constraint names the underlying rule rather than re-explaining it — `> Per D3:
show the SELECT count(*) result before proposing the UPDATE.` A skill with its own gate keeps it
and annotates which rules it implements; a domain-tuned gate beats a generic restatement.

## Relationship to `working-agreement`

A sibling `architecture-foundations` plugin's `working-agreement` skill covers four rules about
*how work gets done* — batched verification, surfacing pre-existing problems, model-tier
recommendations, and not assuming details. Three of those are also guardrail rules here (V2, S1,
T4), stated once in each place because the two plugins are independently installable.

The split: `working-agreement` is about **working style**, delivered as a `SessionStart` hook so
it's in context before editing starts. This plugin is about **authority** — what needs the user's
say-so at all. Where they overlap, they agree; where a discipline skill is more specific than
either, the specific one wins.
