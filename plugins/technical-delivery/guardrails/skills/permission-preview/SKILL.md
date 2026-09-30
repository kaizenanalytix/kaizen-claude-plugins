---
name: permission-preview
description: >
  Shows the user what a command will actually do — and what approving it will actually authorise —
  before the permission prompt appears. Covers the six-field preview block, running a read-only
  probe first to get a real sample instead of an invented one, resolving what a connection string
  or context actually points at, stating reversibility honestly, and explaining the difference
  between a one-time "yes" and a standing "always allow" for the rest of the session. Implements
  the P and D guardrail families.
  Use when the user says things like "what does this command do", "what happens if I allow this",
  "why are you asking me to approve this", "show me before you run it", "is this safe to run",
  "what will this delete", "preview that query", "don't run anything against the database yet",
  or before any command that writes to a database, deletes files, deploys, or rewrites git history.
---

# Permission Preview

A permission prompt asks *"do you allow this?"* without answering *"what is **this**, and what
happens after I say yes?"* Those are the two questions that actually matter, and the prompt asks
neither. This skill answers both, before the prompt appears.

> **Guardrails:** implements the P (preview-before-permission) and D (data and destructive
> operations) families defined in a sibling `guardrails` plugin's `guardrails` skill. If that
> plugin isn't installed, the rules below still stand on their own.

The cost asymmetry that justifies the friction: a preview costs one round-trip. A `DELETE` that
matched 40,000 rows instead of 40 costs a restore from backup, if there is one.

---

## 1. The preview block

Six fields. Fill every one. If you can't fill one, write `unknown` and say why — never guess, and
never invent a sample.

```
ABOUT TO RUN — <one-line plain-English summary>

  Command      <the exact command, verbatim, as it will be executed>
  Target       <host / database / cluster / registry / path it actually reaches>
               <and where you read that from>
  Effect       <one concrete sentence: what changes, and to what>
  Scope        <the probe you ran, and its real output>
  Sample       <2-3 concrete rows/files/resources this will affect>
  Reversible   <Yes + the exact undo | With effort + what it takes | NO — no undo>

If you approve this:
  "Yes"              -> <what the one-time approval covers>
  "Yes, allow <x>"   -> <what a standing session grant would cover, specifically>

Not covered — say so explicitly
  - <what this deliberately leaves untouched>
```

Then ask **"Shall I run it?"** and stop.

**Keep it proportionate (P8).** An `ls` gets no preview. A `git status` gets no preview. The block
scales with reversibility — a reversible command might warrant three fields and one line; only an
irreversible one earns all six.

---

## 2. Run the read-only probe first

The `Scope` and `Sample` fields must contain **output you actually got**, not a plausible
illustration. A fabricated sample is worse than no sample: it looks like evidence and isn't.

| Client | Probe before a write |
|---|---|
| `psql` / `mysql` / `sqlcmd` / `snowsql` / `bq` | `EXPLAIN <stmt>` and `SELECT count(*)` with the **same** `FROM`/`WHERE` |
| `sqlite3` | `.schema <table>` and `SELECT count(*)` with the same `WHERE` |
| `mongosh` | `db.<coll>.countDocuments(<same filter>)` |
| `redis-cli` | `DBSIZE`, and `--scan --pattern '<same pattern>'` |
| `alembic` | `alembic current` and `alembic upgrade --sql <rev>` (prints SQL, runs nothing) |
| `prisma` | `prisma migrate diff --script` |
| `terraform` | `terraform plan` |
| `kubectl delete` | `kubectl get <resource> <selector>` |
| `rm -rf` | `ls -la <path>` and `du -sh <path>` |
| `git push --force` | `git log --oneline origin/<branch>..HEAD` and `git log --oneline HEAD..origin/<branch>` |

**If a probe itself needs permission**, ask for the probe alone first. Say it is read-only and say
why you need it. It is the cheapest approval in the session and it unblocks everything after.

**If no probe exists**, write `no probe available` in the Scope field and say why. That is an
honest answer; an invented row is not.

---

## 3. Resolve the target — a name is not a target

`localhost` is not a target. `$DATABASE_URL` is not a target. `staging` is not a target. Each is a
label whose meaning lives somewhere else, and "it looks like a staging URL" is exactly the
assumption that puts a suite through production data.

Read the actual source of truth and say where you read it:

- the env file, and which line
- the deploy config or secret reference that generates it
- `kubectl config current-context` for a cluster
- `git remote -v` for a push target
- the `--registry` / `--profile` / `--project` flag actually in effect

Then state the resolved value in the `Target` field **with its provenance**:

> `Target  orders_dev on localhost:5432 (resolved from .env.local line 3)`

If the string contains `prod`, `prd`, `production`, or `live` anywhere, **say so in the first line
of the preview**, not buried in the Target field.

If you cannot determine what it points at after checking, say that, say what you checked, and ask.
Never proceed on a name that merely looks safe (D1).

---

## 4. State reversibility honestly

Three answers, and only three:

| Verdict | Means | Must also give |
|---|---|---|
| **Reversible** | A single command puts it back | The exact undo command |
| **With effort** | Recoverable, but not by one command | What recovery actually requires, and whether the inputs for it exist |
| **NO — no undo** | Gone | Say it plainly. Offer a snapshot/backup step first. |

"With effort" is where most destructive database work lands, and the honest form names what is
missing: *"rollback needs the prior status per row, which isn't stored anywhere — suggest
snapshotting to `orders_backup_20260918` first."*

**Never soften an irreversible verdict.** "Should be fine to redo" is not a reversibility
statement.

---

## 5. Explain the grant, not just the command (P5)

This is the field nothing else in the toolchain provides, and it is the reason this skill exists.
The permission dialog offers options whose *scope* differs enormously, and describes neither.

Be specific about what the broad option would then permit **unprompted**:

```
If you approve this:
  "Yes"                     -> runs this one command; I ask again next time.
  "Yes, allow psql"         -> I can run ANY psql command against ANY database for the
                               rest of this session without asking — including DELETE,
                               DROP TABLE, and TRUNCATE.
```

Write what it *could* do, not what you *intend* to do. The user is deciding about the grant, not
about your intentions.

Where a narrower grant exists, name it — a more specific allow-rule is usually the right answer:

> A narrower option: allowing `Bash(psql:*--command=SELECT*)` would cover reads only and still
> require approval for every write.

---

## 6. One approval per irreversible act (P6)

Never bundle. Two destructive commands in one approval request means the user is approving the one
they read and the one they didn't.

- A destructive command never shares a request with safe setup commands.
- A migration and a data backfill are two approvals, not one.
- "Run these four cleanup commands" is four previews, or it is a script the user reviews as a
  file first.

---

## 7. Worked examples

`references/worked-examples.md` carries six complete previews, each with the probe, the block, and
the grant explanation:

| Example | The hard part it demonstrates |
|---|---|
| `UPDATE` with a `WHERE` | Counting first even when the query is correct |
| Schema migration (`alembic upgrade head`) | Showing the offline SQL and the down-revision |
| `git push --force` | Showing what commits would be destroyed on the remote |
| `terraform apply` | Reading a plan for the destroy-and-recreate lines |
| `rm -rf` outside a build directory | When the path is regenerable and when it isn't |
| `npm publish` | An irreversible act with no meaningful sample |

---

## 8. When this does not apply

Real carve-outs, because a preview demanded for everything gets ignored for everything:

- **Read-only commands.** `ls`, `cat`, `git status`, `git log`, `SELECT`, `EXPLAIN`, `--dry-run`,
  `terraform plan`. These are how previews get built; gating them is self-defeating.
- **Regenerable artefacts.** `rm -rf node_modules`, `dist`, `build`, `.venv`, `__pycache__`,
  `target`, `coverage`. Deleting build output is a daily operation, not a destructive act.
- **`git reset --hard` with a clean worktree.** Nothing is lost; reflog recovers it.
- **Local-only infrastructure.** `kubectl` against `docker-desktop`/`minikube`/`kind-`,
  `docker` against local containers.
- **Work the user just explicitly asked for, in the same turn, naming the command.** If they said
  "run `pytest tests/orders`", that is the task, not a decision.

Everything else gets a preview sized to its reversibility.

---

## Rules to enforce everywhere

- **The command goes in the preview verbatim.** A prose description is not a preview.
- **The sample is output you actually got.** Never invent one; `no probe available` is honest.
- **Resolve the target and say where you read it.** A name that looks safe is not a check.
- **`prod` anywhere in the target string goes in the first line**, not the fourth field.
- **Reversibility is one of three verdicts**, and the undo is named for the first two.
- **Say what "always allow" would authorise**, in terms of what it could do, not what you'd do.
- **One approval per irreversible act.** Never bundle.
- **Ask for the read-only probe alone** rather than skipping the sample.

---
_Last reviewed: 2026-09-18_
