# Worked preview examples

Six complete previews. Each shows the probe that was actually run, the block presented to the
user, and the grant explanation. Every `Scope` and `Sample` value here stands in for **real probe
output** — in practice you run the probe and paste what came back.

---

## 1. `UPDATE` with a correct `WHERE`

The hard part: the query is right, and it still gets counted first. Seeing the number is the
feature (D3), not a penalty for suspicion. A correct-looking `WHERE` that matches 40,000 rows
instead of 40 is the single most common destructive-database accident.

**Probe run first:**

```bash
psql "$DATABASE_URL" -c "SELECT count(*) FROM orders WHERE batch_id = 42 AND status = 'packed'"
# -> 1284
psql "$DATABASE_URL" -c "SELECT id, status FROM orders WHERE batch_id = 42 AND status = 'packed' LIMIT 3"
```

**Preview:**

```
ABOUT TO RUN — mark batch 42 as shipped

  Command      psql "$DATABASE_URL" -c "UPDATE orders SET status='shipped'
                 WHERE batch_id=42 AND status='packed'"
  Target       orders_dev on localhost:5432 (resolved from .env.local line 3)
  Effect       UPDATE — rewrites the status column on matching rows in orders
  Scope        SELECT count(*) with the same WHERE -> 1,284 rows
  Sample       id=90118  status 'packed' -> 'shipped'
               id=90119  status 'packed' -> 'shipped'
               id=90120  status 'packed' -> 'shipped'
  Reversible   With effort — no automatic undo. Rolling back needs each row's prior
               status, which isn't stored. Suggest snapshotting first:
                 CREATE TABLE orders_backup_20260918 AS
                   SELECT * FROM orders WHERE batch_id=42;

If you approve this:
  "Yes"                -> runs this one UPDATE; I ask again next time.
  "Yes, allow psql"    -> I can run ANY psql command against ANY database for the
                          rest of this session without asking — including DELETE,
                          TRUNCATE, and DROP TABLE.
  A narrower option    -> allowing Bash(psql:*--command=SELECT*) covers reads only.

Not covered — say so explicitly
  - orders in other batches (untouched)
  - the shipping-notification job this status change triggers downstream
  - orders already in 'shipped' (the WHERE excludes them, so re-running is safe)

Shall I run it?
```

---

## 2. Schema migration — `alembic upgrade head`

The hard part: the destructive step is *inside* the migration, invisible from the command. The
probe is what makes it visible.

**Probes run first:**

```bash
alembic current                      # -> 4a1f9c2b1e07 (head: 9de2b71c0a43)
alembic upgrade --sql 4a1f9c2b1e07:head   # prints the SQL, runs nothing
```

**Preview:**

```
ABOUT TO RUN — apply 1 pending migration to the orders database

  Command      alembic upgrade head
  Target       orders_dev on localhost:5432 (from alembic.ini -> env var DATABASE_URL,
               resolved via .env.local line 3)
  Effect       Applies revision 9de2b71c0a43 "drop legacy_status column"
  Scope        alembic current -> 4a1f9c2b1e07; one revision behind head.
               Offline SQL (alembic upgrade --sql) shows:
                 ALTER TABLE orders ADD COLUMN status_v2 VARCHAR(32);
                 UPDATE orders SET status_v2 = legacy_status;
                 ALTER TABLE orders DROP COLUMN legacy_status;   <-- destructive
  Sample       orders currently has 48,201 rows; all carry legacy_status.
               After this, legacy_status no longer exists on the table.
  Reversible   With effort — a down-revision exists (9de2b71c0a43 downgrade), but it
               recreates legacy_status EMPTY. The data in that column is not
               recoverable from the down-migration alone.

  *** This migration violates expand-then-contract (D4): it adds, backfills, and
      drops in one revision. The previous release's code still reads legacy_status
      and will break the moment this runs. Splitting it into two releases is the
      safer path — I can do that instead if you want.

If you approve this:
  "Yes"                  -> runs this migration against orders_dev only.
  "Yes, allow alembic"   -> I can run any alembic command for the rest of the
                            session, including upgrade/downgrade against whatever
                            DATABASE_URL points at when it runs.

Not covered — say so explicitly
  - production (this is the dev database; production has its own pipeline)
  - backing up legacy_status before the drop — say the word and I'll add that step

Shall I run it, split it into two releases, or stop here?
```

---

## 3. `git push --force`

The hard part: the damage is on the *remote*, to commits that may not be yours. The probe is the
two-way log diff.

**Probes run first:**

```bash
git log --oneline origin/feature/orders..HEAD    # what I'd add
git log --oneline HEAD..origin/feature/orders    # what I'd DESTROY
git remote -v
```

**Preview:**

```
ABOUT TO RUN — force-push the rebased orders branch

  Command      git push --force origin feature/orders
  Target       origin = dev.azure.com/KaizenAnalytix/.../ka-skills-library
               branch feature/orders (shared remote, not a personal fork)
  Effect       Overwrites the remote branch history with local history
  Scope        git log HEAD..origin/feature/orders -> 2 commits on the remote that
               are NOT in my local branch:
                 8c1d4a9  fix: null check in order validator   (Priya, 3 hours ago)
                 2f7e0b3  test: add validator regression case  (Priya, 3 hours ago)
  Sample       Those two commits would be destroyed on the remote. They are not in
               my local history, so this push removes them for everyone.
  Reversible   With effort — recoverable via reflog ONLY on a machine that already
               has them. Priya has them locally; I do not. If she re-clones before
               noticing, they're gone.

  *** Someone else has pushed to this branch since I last fetched. A force-push
      here destroys their work. --force-with-lease would refuse this push instead
      of silently overwriting; I'd recommend that, or a rebase onto their commits.

If you approve this:
  "Yes"                      -> force-pushes this branch now, destroying those 2 commits.
  "Yes, allow git push"      -> I can push to any branch, including main, for the rest
                                of the session without asking.

Shall I force-push, switch to --force-with-lease, or rebase onto Priya's commits first?
```

---

## 4. `terraform apply`

The hard part: `apply` on a plan you haven't read is a blind irreversible act. The plan *is* the
probe, and the lines that matter are the `-/+` ones.

**Probe run first:**

```bash
terraform plan -out=tfplan
terraform show tfplan | grep -E '^\s*[-+~/]'
```

**Preview:**

```
ABOUT TO RUN — apply 6 infrastructure changes

  Command      terraform apply tfplan
  Target       workspace "staging", AWS account 4415-xxxx-9902, eu-west-1
               (from terraform workspace show + the configured backend)
  Effect       3 to add, 2 to change, 1 to DESTROY AND RECREATE
  Scope        terraform plan output, the lines that matter:
                 + aws_security_group.api_v2
                 + aws_lb_target_group.api_v2
                 + aws_cloudwatch_log_group.api_v2
                 ~ aws_lb_listener.api           (forwards to the new target group)
                 ~ aws_ecs_service.api           (desired_count 2 -> 4)
                 -/+ aws_db_instance.orders      (FORCES REPLACEMENT)
                     ~ engine_version "14.7" -> "15.3"   # forces replacement
  Sample       aws_db_instance.orders is the staging orders database. Replacement
               means: destroy the instance, create a new one. Data on it does not
               survive unless restored from a snapshot.
  Reversible   NO for the database replacement. The other five changes are
               reversible by reverting the config and re-applying.

  *** The engine_version bump forces a full replacement rather than an in-place
      upgrade. If staging's data matters, take a snapshot first, or use
      allow_major_version_upgrade with an in-place path instead.

If you approve this:
  "Yes"                       -> applies all 6 changes, including the DB replacement.
  "Yes, allow terraform"      -> I can run any terraform command for the rest of the
                                 session, including apply and destroy, against
                                 whichever workspace is selected at the time.

Not covered — say so explicitly
  - production (different workspace, different account)
  - the snapshot — not in this plan; I'd need to add it

Shall I apply, or take a snapshot of the orders DB first?
```

---

## 5. `rm -rf` — when the path is regenerable and when it isn't

The hard part: the same command is routine on one path and catastrophic on another. The
distinction is whether the contents can be regenerated from something committed.

**No preview needed** — regenerable, rebuilt by a documented command:

```bash
rm -rf node_modules dist .venv __pycache__ coverage .next target
```

State it in one line and proceed: *"Clearing `node_modules` and `dist`, both regenerable via
`npm ci` and `npm run build`."*

**Full preview required** — anything else:

```bash
ls -la ./uploads && du -sh ./uploads && git check-ignore ./uploads && echo "NOT tracked by git"
```

```
ABOUT TO RUN — delete the local uploads directory

  Command      rm -rf ./uploads
  Target       <repo>/uploads (absolute: C:/…/ka-skills-library/uploads)
  Effect       Recursively deletes the directory and everything under it
  Scope        du -sh -> 2.3 GB
               ls -la -> 11,847 files
               git check-ignore -> ./uploads IS gitignored, so NOT tracked
  Sample       uploads/2026-08/invoice-88213.pdf
               uploads/2026-08/invoice-88214.pdf
               uploads/2026-09/contract-scan-0041.png
  Reversible   NO. Not tracked by git, so there is no commit to restore from, and
               rm -rf does not use the recycle bin. If these aren't mirrored in
               object storage, deleting them is final.

If you approve this:
  "Yes"                  -> deletes this one directory.
  "Yes, allow rm"        -> I can delete any path for the rest of the session
                            without asking. I'd recommend against this one.

Are these mirrored anywhere? Shall I delete?
```

---

## 6. `npm publish` — irreversible, with no meaningful sample

The hard part: there is nothing useful to sample. The preview's whole job is the grant explanation
and the irreversibility, not a `Sample` field padded with theatre.

**Probes run first:**

```bash
npm publish --dry-run
npm whoami && npm config get registry
```

**Preview:**

```
ABOUT TO RUN — publish @kaizen/order-client to the public npm registry

  Command      npm publish
  Target       registry.npmjs.org (public), as user kaizen-ci
  Effect       Publishes @kaizen/order-client@2.1.0 — public, permanent
  Scope        npm publish --dry-run -> 48 files, 212.4 kB unpacked.
               Includes: dist/, README.md, package.json
               Does NOT include: src/, tests/, .env.example  (per .npmignore)
  Sample       no meaningful sample available — publishing has no dry-run effect
               to show beyond the file list above.
  Reversible   NO. npm unpublish is blocked after 72 hours, and even within that
               window the version number is permanently burned — 2.1.0 can never
               be republished with different contents.

  *** Version 2.1.0 is not yet tagged in git. Publishing a version that doesn't
      correspond to a tag makes the published artifact unreproducible.

If you approve this:
  "Yes"                     -> publishes 2.1.0 publicly, now, permanently.
  "Yes, allow npm publish"  -> I could publish any package version for the rest of
                               the session without asking. Strongly recommend against.

Not covered — say so explicitly
  - the git tag (not created; I'd suggest tagging first)
  - the changelog entry for 2.1.0

Shall I publish, or tag first?
```

---

_Last reviewed: 2026-09-18_
