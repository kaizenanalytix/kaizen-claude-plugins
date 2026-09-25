---
name: deployment-best-practices
description: >
  Reviews an existing Dockerfile, pipeline, or deployment setup against a
  concrete checklist — mutable :latest tags, rebuild-per-environment, secrets
  in images or logs, long-lived cloud keys, containers running as root, a
  liveness probe that checks the database, no tested rollback path, no
  approval gate on production, migrations that can't roll back, and scaling
  instances against a fixed connection-pool ceiling. Use when the user says
  things like "review our deployment", "is this pipeline any good",
  "deployment best practices", "why are our deploys risky", "we keep breaking
  prod", "review this Dockerfile", or "our deploys are slow".
---

# Deployment Best Practices

A review checklist for a deployment setup that already exists. Sibling skills
in this plugin write things correctly the first time; this one reads what's
there and reports what's wrong.

Findings are framed by DORA's four key metrics — deployment frequency, lead
time for changes, change failure rate, and time to restore service — because
they're what a deployment setup is actually for, and they turn a stylistic
opinion into a claim about outcomes. If a finding doesn't move one of the four,
say so and rank it low.

## How to run this review

1. **Read what exists** before commenting on it: the Dockerfile and
   `.dockerignore`, the pipeline file(s), any compose file, and the
   environment/secret configuration.
2. **Group findings by severity**, using the sections below.
3. **Report, don't silently fix.** This mirrors the working agreement's rule 2
   — surface each finding with a concrete suggestion and let the user decide.
   A deployment change is exactly the kind of thing that shouldn't be applied
   as a side effect of asking for a review.
4. **Cap it.** Three well-explained findings beat fifteen that turn into a
   backlog. Lead with anything in the "will cause an incident" section.

## Will cause an incident

- **`:latest` or any mutable tag in a deploy.** You cannot say what's running,
  cannot reproduce it, and "roll back to latest" is meaningless. → Tag by
  commit SHA, reference by digest.
- **Rebuilt per environment.** Staging never tested the bytes production runs,
  and rollback has no defined target. → Build once, promote the same artifact.
- **No rollback path, or an untested one.** An untested rollback is a
  hypothesis you'll first evaluate during an incident. → Make it redeploying
  the previous SHA, and exercise it deliberately.
- **A liveness probe that checks a downstream dependency.** When the database
  blips, every instance fails liveness, every instance restarts at once, and a
  brief dependency problem becomes a full outage plus a reconnect storm. →
  Liveness checks the process; readiness checks dependencies.
- **Migrations that aren't backward-compatible.** A renamed column or a new
  `NOT NULL` without a default means code can roll back and the schema cannot.
  → Expand, deploy, backfill, contract — across separate releases.
- **Shell-form `CMD`/`ENTRYPOINT`.** `SIGTERM` never reaches the app, so every
  deploy, scale-down, and rollback kills in-flight requests at the end of the
  grace period. → Exec form, plus real signal handling.
- **Scaling instances against a fixed connection-pool ceiling.** Each new
  instance takes connections the existing ones needed, so adding capacity
  makes the outage worse. This is the write-heavy anti-pattern, and it is an
  architecture problem — route to a sibling `backend` plugin's
  `fastapi-data-layer` and `architecture-foundations`' `state-philosophy`, not
  to a pipeline change.
- **Single replica described as highly available.** One instance means every
  deploy and every node event is downtime. → Two minimum, behind a load
  balancer, if the claim is to hold.

## Security

- **Secrets in image layers, build args, committed `.env` files, or logs.**
  Layers persist and `ARG` values land in metadata; a pushed `.env` is in git
  history forever and rotation is the only fix. → Platform secret manager,
  injected at deploy.
- **Long-lived cloud credentials in CI.** Usually the highest-value,
  longest-lived secret a team has, readable by anyone who can edit a workflow.
  → OIDC / workload identity federation.
- **An OIDC trust condition scoped too broadly** — to a whole org rather than
  a specific repo, branch, or environment. Any repo in the org can then deploy
  your production service.
- **One deploy identity shared across environments.** The production approval
  gate protects nothing if the dev path already had the permissions.
- **Container running as root**, or without an explicit high UID. Many cluster
  policies reject it outright, and a low system-assigned UID fails the common
  `> 10000` assertion.
- **No `.dockerignore`.** `COPY . .` then pulls in `.git`, `.env`, and host
  `node_modules` — some of which persist in a layer.
- **A scan that warns instead of failing.** A secret or critical CVE finding
  that doesn't fail the build is documentation, not a gate.
- **No image or dependency scanning at all**, and no SBOM — so the day a CVE
  lands, "are we affected and where" is a multi-day audit instead of a query.

## Slow, expensive, or annoying

- **Source copied before dependencies installed.** Every one-line change
  reinstalls everything. The most common cause of a nine-minute build, and the
  fix is two lines in a different order.
- **Single-stage build**, shipping the whole toolchain to production — a bigger
  image, a bigger attack surface, more CVEs to triage, slower pulls.
- **Expensive stages running before cheap ones** — an image build that starts
  before lint has had a chance to fail.
- **No dependency caching between runs**, or a cache key that never hits.
- **Full-size staging** paid for around the clock when a smaller one would
  catch the same bugs — with the caveat from `deployment-environments` that
  *data cardinality* still needs to be realistic even when instance size
  isn't.
- **Unpinned base images.** `FROM python:latest` means today's build and
  tomorrow's rollback aren't the same image.
- **Dependencies resolved at build time** rather than from a lockfile — the
  build's output changes without its input changing.

## Operability

- **No structured logging.** Grepping unstructured text is the difference
  between a two-minute and a two-hour diagnosis.
- **No health endpoint**, or one that authenticates, or one that runs a real
  query and becomes its own load generator.
- **No SLO**, so there's no defined threshold for "this release is bad" — and
  therefore no basis for an automatic canary abort.
- **A canary nobody watches.** Without an automated abort on error-rate or
  latency regression, a canary is just a slower deploy.
- **Approval as a chat message** rather than a platform-enforced gate. Holds
  until the first urgent Friday.
- **Compose used as a deployment mechanism.** It's a local-development tool;
  as production config it's an unversioned, unmonitored, single-host deploy.
- **A pipeline that can't be run from a clean clone** — undocumented manual
  steps, or a deploy that only works from one person's machine.

## What not to flag

Keep the review honest by leaving these alone:

- **A missing orchestrator.** Kubernetes is justified by the number of
  services and teams, not by traffic or by its absence being a gap.
- **Not containerized.** If it's a static bundle on a CDN, that's correct —
  see `deployment-strategy`. Don't report the absence of a Dockerfile as a
  finding.
- **A simple pipeline for a simple service.** Missing canary deploys on an
  internal tool with twelve users is proportionate, not a defect.
- **Anything that doesn't move one of the four DORA metrics.** Say why it's
  low priority rather than padding the list.

## Rules to enforce everywhere

- **Report findings, don't silently fix them.** Surface each with a concrete
  suggestion and let the user decide — deployment changes especially.
- **Lead with what causes incidents.** Mutable tags, rebuild-per-environment,
  broken rollback, and liveness-probes-checking-dependencies before anything
  stylistic.
- **Cap the list.** Three explained findings beat fifteen listed ones.
- **Tie each finding to an outcome.** If it doesn't affect deploy frequency,
  lead time, failure rate, or recovery time, rank it low and say so.
- **Route architecture problems out.** Connection-pool exhaustion and write
  throughput belong to the backend and architecture skills, not here.
- **Don't flag proportionate simplicity.** A small service with a small
  pipeline is not a finding.

---
_Last reviewed: 2026-08-24_
