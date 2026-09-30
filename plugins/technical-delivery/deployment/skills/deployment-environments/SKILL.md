---
name: deployment-environments
description: >
  Defines the dev/staging/prod contract — what differs between environments
  (secret values, endpoint URLs, scale, approvers, log verbosity) and what must
  never differ (the artifact, the runtime, the config keys) — plus where
  secrets actually live, how config gets injected at deploy rather than baked
  at build, how migrations stay safe to roll back, and why production data
  never moves downward. Applies on every deployment shape, including static
  hosting. Use when the user says things like "set up staging", "environment
  variables per environment", "promote to production", "how do we manage
  secrets", "dev vs prod config", "our staging doesn't match prod", or "we
  can't roll back this migration".
---

# Deployment Environments

Three environments, **one artifact moving through them.** That single sentence
is the whole contract, and most environment problems are a violation of it
wearing a different hat.

This applies whatever shape a sibling `deployment-strategy` skill landed on —
a container, a static bundle on a CDN, a serverless function. The artifact
differs; the promotion discipline doesn't.

## 1. The three environments

| | dev | staging | prod |
|---|---|---|---|
| Purpose | does it work at all | would this release be safe | serves real users |
| Trigger | merge to main | promote from dev | promote from staging, after approval |
| Artifact | built here once, tagged by commit SHA | **the same SHA** | **the same SHA** |
| Data | ephemeral, disposable, synthetic | seeded, representative, synthetic | real |
| Approval | none | none | a named human |
| Who can deploy | CI, automatically | CI, automatically | CI, only after approval |

**Staging's job is to be the last place a bad release is cheap.** If staging
differs from production in ways that matter, it stops doing that job, and
every difference you add is a class of bug it can no longer catch.

## 2. What must differ

These are the only things that should vary between environments:

- **Secret values** — different database credentials, different API keys.
  Different *values*, same *keys* (section 3).
- **Endpoint URLs** — which database, which upstream service, which bucket.
- **Scale** — replica counts, autoscaling floor and ceiling, instance size.
  Production is bigger; staging doesn't need to be, and paying for a
  full-size staging is rarely the best use of that money.
- **Who may approve a deploy** — nobody for dev and staging, a named person
  for production.
- **Log verbosity and trace sampling** — debug logging and 100% tracing are
  affordable in dev and are not in production.

## 3. What must not differ

- **The artifact.** Same digest or commit-SHA tag promoted through all three,
  never rebuilt per environment. This is the rule everything else rests on —
  see section 4.
- **The runtime, base image, and dependency versions.** A staging run on a
  different Python patch or a different base image is testing something that
  will never be deployed.
- **The deploy mechanism.** If production is deployed by a different path than
  staging, then staging never tested the deploy — and the deploy is a common
  place for things to go wrong.
- **The config *keys*.** This one is subtle and worth stating plainly: every
  environment reads the *same set* of variable names, only the values change.
  If production needs `REDIS_URL` and dev doesn't define it, then the missing
  variable is discovered in production. Keep the keys identical and a missing
  one fails in dev, where it's free.

Validate config at startup rather than on first use. A service that boots
happily and then fails an hour later when some code path first reads an unset
variable has converted a config error into an incident.

## 4. Build once, promote the same artifact

**Build the artifact exactly once, tag it by commit SHA, and promote that same
artifact through every environment.**

The argument, in the order it actually bites:

1. If each environment is built separately, **staging never tested the bytes
   production runs.** It tested a different build of the same source, which is
   not the same claim.
2. **Rebuilding reintroduces nondeterminism** at the worst moment — a base
   image that moved, a dependency that resolved differently — so the thing you
   promote isn't the thing you validated.
3. **Rollback stops being well-defined.** "Redeploy the previous version"
   requires there to *be* a previous artifact, identified. Rebuild-per-deploy
   makes rollback a rebuild, which is slow and may not even reproduce.

### The frontend consequence, stated plainly

For a bundled frontend this has a specific cost: **environment values cannot
be baked in at build time.** A Vite build that inlines `VITE_API_URL` produces
an artifact valid for exactly one environment, which is by definition not
promotable.

Two ways to fix it, both fine:

- **A runtime config file** the app fetches on boot (`/config.json`), written
  per environment at deploy time.
- **Deploy-time injection** into `index.html` — the deploy step substitutes
  values into a placeholder before upload.

A sibling `frontend` plugin's `vite-build-output` skill covers the mechanics of
both. The narrow exception where build-time inlining genuinely can't be
avoided — a per-tenant-domain build, for instance — should be **stated out loud
when taken**, along with the fact that each build is then environment-specific
and must be versioned by SHA *plus* environment.

## 5. Where secrets actually live

**In the platform's secret manager, injected at deploy time.** Not in the
repo, not in the image, not in CI variables if the platform offers something
better.

Three places secrets leak that people don't expect:

- **Image layers persist.** A secret copied in and deleted in a later layer is
  still extractable from the image, and now also lives in your registry.
  `ARG`/`--build-arg` values are recorded in image metadata too.
- **Committed `.env` files.** Once pushed, a secret is in git history forever
  and rotating it is the only real fix. `.env.example` with dummy values is
  the pattern; `.env` belongs in `.gitignore` and `.dockerignore` both.
- **Logs.** A config dump at startup, or an exception rendering a connection
  string, puts credentials in a log aggregator that is usually readable by
  more people than the secret store is.

Rotation should be a config change, not a deploy. If rotating a credential
requires rebuilding an artifact, the credential was baked in somewhere it
shouldn't have been.

## 6. Migrations, and what they do to rollback

**Code rolls back in seconds. A schema does not.** This asymmetry is the thing
that makes an otherwise-clean rollback plan fail in practice.

The rule: **a migration must leave the previous release's code still working.**
Forward-only, backward-compatible for at least one release. Concretely, the
expand-then-contract sequence:

1. **Expand** — add the new column as nullable, or add the new table.
   Old code ignores it; new code can use it. Safe to roll back.
2. **Deploy** the code that writes both old and new shapes.
3. **Backfill** existing rows, as a separate operation.
4. **Contract** — only once you're confident you won't roll back past step 2,
   drop the old column in a *later* release.

What breaks this: renaming a column in place, adding a `NOT NULL` column
without a default, or dropping anything the currently-deployed code still
reads. Each turns a rollback into a restore-from-backup.

Run migrations as their own step, before the new code is serving traffic, and
dry-run them against staging first. **Never against production data from a
developer machine.**

## 7. Production data does not move downward

Copying production data into staging or dev is the fastest way to get
representative test data, and it's usually the wrong call:

- Every person with dev access now effectively has production data access,
  which is rarely what any access review assumed.
- Under GDPR-style regimes, personal data in a lower environment is still
  personal data, with the same obligations and now a wider blast radius.
- Lower environments have weaker controls, less monitoring, and more
  short-lived credentials, by design.

Use **generated or anonymized seed data** that matches production's *shape* —
volume, cardinality, distribution, awkward edge cases — without carrying real
records. Where a specific production bug can only be reproduced with real
data, treat that as a narrow, time-boxed, logged exception with the data
removed afterwards, not as the standing arrangement.

## 8. Environment parity is a reliability property

Every difference between staging and production is a bug staging cannot catch.
That makes parity worth tracking deliberately — and worth *writing down* where
it's deliberately broken.

The differences that most often cause "worked in staging" incidents:

- **Scale**: one replica in staging, six in production — so nothing sticky,
  nothing racing, and no cross-instance cache problem ever shows up.
- **Data volume**: a query that's instant against 500 rows and unusable
  against 5 million. Staging with realistic *cardinality* catches this;
  staging with 500 rows never will.
- **Managed-service tiers**: a different database tier with different
  connection limits, or a cache that's real in production and in-memory in
  staging.
- **Network shape**: no CDN, no WAF, no load balancer in staging — so
  header handling, timeouts, and redirects behave differently.

You will not achieve full parity, and chasing it isn't the goal. Knowing
exactly where it's broken is.

## Rules to enforce everywhere

- **One artifact, promoted.** Same SHA through dev, staging, and prod — never
  rebuilt per environment.
- **Never bake environment values into a promotable artifact.** Inject at
  deploy; use a runtime config for frontends.
- **Same config keys everywhere, different values.** A missing key must fail
  in dev, not production.
- **Validate config at startup**, not on first use.
- **Secrets live in the platform's secret manager** — never in the repo, the
  image, or a log line. Rotation is a config change, not a deploy.
- **Migrations stay backward-compatible for one release.** Expand, deploy,
  backfill, contract — in separate releases.
- **Never run a migration against production from a developer machine.**
- **Production data never moves downward.** Generate or anonymize instead.
- **Write down where parity is deliberately broken.** An unknown difference is
  the one that causes the incident.
- **Staging must be the last cheap place to find a bad release.** Every
  difference you add takes something away from it.

---
_Last reviewed: 2026-08-24_
