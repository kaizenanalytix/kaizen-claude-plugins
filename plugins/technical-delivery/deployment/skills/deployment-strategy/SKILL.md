---
name: deployment-strategy
description: >
  Decides how an application should ship before anything gets written — asks
  what ships, who uses it, and what it does to data, then maps those answers
  onto a deployment shape (static hosting, PaaS, a container on a managed
  runtime, serverless, container plus orchestrator, or a VM) with explicit
  reasoning for why that shape and not the others, and presents a deployment
  plan for confirmation before a Dockerfile, a pipeline file, or an
  environment exists. Never assumes a container. Use when the user says
  things like "how should we deploy this", "do we need Docker", "should we
  containerize", "where should this run", "set up deployment", "we need a
  staging environment", or "what's the best way to ship this".
---

# Deployment Strategy

This skill owns one decision: **what shape does this deployment take, and
why.** It writes nothing itself — no Dockerfile, no pipeline, no environment
— and hands each of those to the skill that owns it, only after the shape is
confirmed.

It exists because the expensive mistake in deployment is not a badly-written
Dockerfile. It's writing a Dockerfile at all for something that should have
been static files on a CDN, or reaching for an orchestrator to solve a
problem that was never about scheduling. Both get discovered months later,
and both are a rebuild rather than an edit.

## The one thing this skill refuses to do

**Assume a container.** "Deploy this" is not a request for Docker. A built
frontend with no server code of ours is better served as static files; a
short, stateless, event-triggered job is better as a function; a service that
needs a specific kernel is a baked VM image. Containerizing all three is a
habit, not a decision.

So the first output of this skill is never a file — it's a recommendation with
its reasoning, including the reasoning for what was *rejected*.

## 0. Consult the codebase map first

If a sibling `codebase-map` plugin is installed, ask its `codebase-map-sync`
skill for cached facts about this repo — the stacks present, whether there's a
frontend, a backend, or both, and the dependency manifests — before exploring
the code yourself. It already knows most of what step 1 would otherwise have
to grep for, refreshed cheaply via a checkpoint rather than a full re-read. If
that plugin isn't installed, look at the manifests directly; nothing here
requires it.

Reading the repo tells you what *exists*. It does not tell you the load or the
write profile — only the user knows those, which is what step 1 is for. Never
infer step 1's answers from the code.

## 1. Ask what ships, who uses it, and what it does to data

Ask these three as multiple-choice options, not open-ended ones, **before**
recommending a shape or writing anything. Each asks about something a person
who doesn't work on infrastructure can still answer — business facts, not
technology choices:

**1. What ships:**
- A browser bundle only — a built frontend, no server code of ours.
- A service with a server-side runtime — an API, background jobs, scheduled
  work, or long-lived connections.
- Both — a frontend plus our own backend service.

**2. Who uses it, and how hard:**
- An internal team: tens of users, business hours (recommended default).
- Hundreds to a few thousand users, steady daytime traffic.
- Public or bursty — traffic we don't control and can't predict.

**3. What it does to data:**
- Mostly reads and displays (recommended default).
- Steady writes tied to user actions — forms, orders, edits.
- High-volume or machine-generated writes — ingest, telemetry, uploads,
  webhooks, batch jobs.

Wait for the answers. Do not infer them from the repo contents, and do not
start writing a Dockerfile, a pipeline file, or an environment matrix while
asking — a wrong guess here is rebuilt, not adjusted.

**If the user answers "I don't know" to 2 or 3** — which is common and
reasonable, especially before launch — take the recommended default and *say
explicitly that the plan is sized for that answer*, so they can correct it
when reality arrives. Silently assuming low traffic and never mentioning it is
how a project discovers its own ceiling in production.

Skip asking only where the request already answers a question unambiguously
("we need to dockerize the FastAPI service so it runs on Cloud Run" answers 1,
and names a target) — and even then, confirm the unanswered ones.

## 2. Detect the CI platform and environments before asking about them

Two more answers are needed, but check the repo first — asking about something
already sitting in the tree reads as not having looked.

**CI platform.** Look for `.github/workflows/`, `.gitlab-ci.yml`,
`azure-pipelines.yml`, `cloudbuild.yaml`, and `Jenkinsfile`. If exactly one is
present, state it as the assumed answer rather than asking. If several are
present, ask which is authoritative. If none are, ask which platform the team
uses — GitHub Actions / GitLab CI / Azure DevOps / Cloud Build / Jenkins.
**Never default to GitHub Actions silently**; a pipeline written for the wrong
platform is a total rewrite, not a port.

**Environments that exist today:**
- All three (dev, staging, prod) already exist.
- Production only — staging is to be created (recommended default for an
  existing project).
- Local and production only, no CI yet.

## 3. Pick the shape, and say what you rejected

Two rules govern the table below:

- **The cheapest shape that meets the requirement wins.** Operability is a
  running cost paid by whoever is on call, not a one-time setup cost.
- **An orchestrator is justified by the number of services and teams, not by
  traffic.** A single service under heavy load does not need Kubernetes; ten
  services with four teams might.

| What ships | Load / data profile | Recommend | Why this, and not the others |
|---|---|---|---|
| Browser bundle | any | **Static hosting / CDN** | The artifact is already immutable content-hashed files. A container would only add a web server to patch, an image registry to run, and a CVE treadmill — to serve files a CDN serves faster and cheaper. |
| Service | Internal + read-mostly | **PaaS or managed container runtime, scale-to-zero allowed** | Cheapest route to a real URL with TLS, logs, and rollback. An orchestrator's control plane costs more to operate than this app costs to run. |
| Service | Steady traffic + steady writes | **Container on a managed runtime, minimum instances ≥ 1** | The container earns its keep here: it fixes "works on my machine" and makes one artifact promotable across environments. Scale-to-zero is dropped because cold starts would land on interactive requests. |
| Service | Bursty / unpredictable | **Managed runtime with autoscaling; serverless functions if the work is short and stateless** | Burstiness is a scaling problem, not an operability problem. A fixed-size VM either wastes money at idle or falls over at peak. |
| Service | **High-volume or machine-generated writes** | **Managed runtime — *but go to step 4 first*** | Packaging is not the constraint here, and choosing it first hides the real problem. See step 4. |
| Both | any | **Split: static hosting for the frontend, one of the above for the backend** | Two artifacts with different lifecycles and different cache semantics. One container serving both couples a CSS change to an API deploy and throws away the CDN. |
| Service | Needs a specific kernel, a GPU, licensed software, or lands in an existing VM estate | **VM, with the image baked in CI** | The one case a VM genuinely wins — and baking the image in CI keeps it reproducible instead of hand-configured. |
| Service | Stateful, sticky sessions, or a long-lived local disk | **Container plus an orchestrator, or a managed stateful service** | Managed request-scoped runtimes assume instances are replaceable and stateless. But ask first whether that state can move to a managed store — usually it can, and then the row above applies instead. |

State the rejected options out loud, briefly. "Static hosting, not a
container" with one clause of reasoning is what stops the same question being
re-litigated in three months.

## 4. When it's an architecture problem, not a packaging problem

If the answer to question 3 was high-volume or machine-generated writes, say
this plainly before recommending anything:

> **Write volume is an architecture problem before it is a packaging
> problem.** No Dockerfile fixes an exhausted connection pool.

What actually decides whether this workload holds up:

- **Connection pooling, and where the pooler lives.** Horizontally scaling
  instances against a fixed database connection ceiling makes the problem
  worse, not better — each new instance takes connections the existing ones
  needed.
- **Queue-and-drain versus synchronous writes.** Whether an incoming write has
  to reach the database before the request returns is the single biggest lever
  on how much traffic the system absorbs.
- **Backpressure.** What the service does when it cannot keep up — shed load
  deliberately, or fall over.
- **Idempotency keys.** Retried writes are guaranteed at this volume, and a
  retry that double-writes is a data-correctness bug, not a performance one.
- **Batch sizing** for machine-generated ingest.

Route those to the skills that own them — a sibling `backend` plugin's
`fastapi-data-layer` (repository and connection handling),
`fastapi-best-practices` (async and N+1 concerns),
`fastapi-common-packages` (background jobs and queues), and a sibling
`architecture-foundations` plugin's `state-philosophy` — and come back here
for packaging once the write path is settled. Recommending a container shape
first isn't wrong, it's just not the answer to the question they asked.

## 5. Present the deployment plan, then stop

Do not create a Dockerfile, a pipeline file, an environment, or a compose file
in the same turn the shape is decided. Present a **deployment plan** and wait.

Keep it to one fenced block that can be reacted to in under a minute — this is
a list to correct, not a document to review:

```
Deployment shape
  Static hosting + CDN for the frontend (dist/), managed container runtime
  for the API.
  Not a container for the frontend: no server code of ours, so an image
  would add a web server to patch for no benefit. Not an orchestrator:
  one service.

Environments
  dev      auto-deploy on merge to main; ephemeral data
  staging  the same artifact as dev, promoted; seeded data; e2e runs here
  prod     the same artifact as staging, promoted on manual approval

Pipeline (GitHub Actions) — gates in order
  1. lint + typecheck + unit/integration tests   -> blocks everything
  2. OpenAPI diff gate (existing scripts/diff_schema.py) -> blocks everything
  3. build once, tag by commit SHA, push, scan image -> blocks everything
  4. deploy dev
  5. Playwright e2e against deployed staging (E2E_BASE_URL) -> blocks prod
  6. manual approval -> deploy prod, canary, then full rollout

Config and secrets
  One artifact, no build-time env baking; values injected at deploy from the
  platform's secret store. CI authenticates by OIDC federation — no
  long-lived keys in repo secrets.

Rollback
  Redeploy the previous SHA tag. Migrations are forward-only and remain
  backward-compatible for one release.

Not covered — say so explicitly
  - DNS, TLS certificates, and the CDN account itself (needs platform access)
  - the queueing/load-shedding design for the ingest endpoint — routed to the
    backend plugin, see step 4
  - cost estimates, and the observability/SLO setup
```

That last section is not optional. **Always state what is out of scope**,
because it is reliably where the user finds the thing they actually cared
about — a certificate nobody owns, a cost nobody costed, an architecture
decision that got routed elsewhere.

**A hard stop, not a suggestion.** Even when the request sounded like "just
dockerize it" or "just add a deploy step", produce this plan, present it, and
wait for confirmation before creating a Dockerfile, a pipeline file, or an
environment. The shape decision is the one that's expensive to reverse: a
wrong container-or-orchestrator call is a rebuild plus a migration, and it's
cheap to correct while it's still six lines of text.

**Keep it proportionate.** For a single static site with one environment,
three lines and a question is the whole gate. The block above is sized for a
two-sided app with three environments — don't inflate a small deployment into
a document to match it.

## 6. Hand off

Only after the user confirms or edits the plan:

| Confirmed shape | Route to |
|---|---|
| Container on a managed runtime, orchestrator, or a baked VM image | `container-authoring`, then `pipeline-authoring` |
| Static hosting, PaaS buildpack, or serverless zip | **`pipeline-authoring` directly — skip `container-authoring` entirely** |
| Any shape, once the pipeline exists | `deployment-environments` for the per-environment config and secret handling |
| Reviewing something that already exists | `deployment-best-practices` |

The second row matters most: a static-hosting project must never be walked
through container authoring. If the shape has no image in it, that skill has
nothing to contribute and reading it invites a Dockerfile nobody needed.

## Rules to enforce everywhere

- **Never assume a container.** "Deploy this" is not a request for Docker.
  Establish the shape from step 1's answers first, every time.
- **Never write a file before the plan is confirmed.** The plan is cheap to
  correct; a Dockerfile and a pipeline built on the wrong shape are not.
- **Always name what you rejected, and why.** A recommendation without its
  alternatives is indistinguishable from a habit, and gets re-litigated later.
- **Never let a default pass silently.** If the user didn't know their traffic
  or write volume, say which answer the plan assumed.
- **Never solve a write-volume problem with packaging.** Route it to the
  architecture and backend skills first, then come back.
- **Detect the CI platform before asking about it**, and never default to
  GitHub Actions just because it's common.
- **The cheapest shape that meets the requirement wins.** Operability is a
  cost someone pays every week, not a one-time setup.
- **Always include the "not covered" section.** What's out of scope is
  information, not an omission.

---
_Last reviewed: 2026-08-24_
