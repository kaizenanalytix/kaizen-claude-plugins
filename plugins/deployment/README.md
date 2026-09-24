# deployment

Tier 2 cross-cutting plugin for deciding how an application ships, then
writing the files for it. Sits between the `frontend` and `backend` plugins the
same way `api-contract` and `e2e-testing` do — it serves either side, and
neither owns it.

## Overview

This plugin's defining property is that **it asks before it writes, and it
never assumes a container.** "Deploy this" is not a request for Docker: a built
frontend with no server code of ours belongs on a CDN, a short stateless job
belongs in a function, and a service needing a specific kernel belongs in a
baked VM image. Containerizing all three is a habit, not a decision.

So the entry point is a questionnaire, not a Dockerfile. `deployment-strategy`
asks three things a non-infrastructure person can actually answer — what ships,
who uses it and how hard, what it does to data — maps those onto a deployment
shape, states why that shape and **not the others**, and presents a deployment
plan for confirmation before any file exists. On a static-hosting answer,
`container-authoring` is skipped entirely.

Recommendations are grounded in Google's published guidance: the Cloud
Architecture Framework pillars for the cost-and-operability framing, their
container build practices, the SRE Book/Workbook for canarying and SLO-based
release decisions, DORA's four key metrics as what a pipeline optimizes, and
SLSA for supply-chain practice. Practices are named and explained rather than
cited, so the reasoning travels with the rule.

## What this plugin does and doesn't generate

| Concern | Status |
|---|---|
| Dockerfile, `.dockerignore` | Generated — when the shape includes an image |
| `docker-compose.yml` | Generated — **local development only**, never a deploy mechanism |
| CI/CD pipeline file | Generated — for whichever of five platforms the project uses |
| Kubernetes manifests, Helm charts | **Not generated.** Dead weight on a managed runtime; only earns its keep with a real cluster, and then it's the cluster team's shape to own |
| DNS, TLS certificates, CDN accounts | Out of scope — needs platform access, and `deployment-strategy`'s gate says so explicitly |
| Cost estimates, observability/SLO setup | Out of scope, and named as such rather than silently omitted |

It conceptually depends on a sibling `architecture-foundations` plugin (the
working agreement, and `state-philosophy` for the write-path questions a
deployment shape can't answer), and wires into two existing plugins rather than
duplicating them — see below — but every skill here works standalone.

## Integration points

- **`api-contract`'s OpenAPI diff gate.** `contract-first` already defines a
  schema-diff CI step calling `scripts/diff_schema.py`. `pipeline-authoring`
  places that existing script as a gate; it does not write a second differ.
- **`e2e-testing`'s deployed-staging posture.** That plugin runs Playwright
  against an already-deployed environment via `E2E_BASE_URL`/`E2E_API_BASE_URL`.
  The pipeline's staging stage matches that and never builds the backend inside
  the e2e job.
- **`frontend`'s `vite-build-output`.** That skill declares `dist/` the deploy
  artifact and leaves build-per-environment vs. build-once explicitly open.
  This plugin resolves it — build once, promote the same artifact, inject config
  at deploy — and explains why.
- **`backend` and `state-philosophy`.** When the questionnaire surfaces
  high-volume writes, `deployment-strategy` routes there first, because
  connection pooling and queueing decide whether the workload holds up and no
  Dockerfile fixes an exhausted pool.

## Layout

```
skills/
├── deployment-strategy/       # entry point — questionnaire, shape decision, hard-stop gate
├── container-authoring/       # image + local compose — SKIPPED when the shape has no image
├── pipeline-authoring/        # CI/CD for the platform the project actually uses
├── deployment-environments/   # the dev/staging/prod contract — applies on every shape
└── deployment-best-practices/ # review checklist for a setup that already exists
```

Skills sit flat at `skills/<name>/SKILL.md`, which is the only depth Claude
Code discovers — a skill nested one level deeper still auto-triggers off its
`description` but loses its `/deployment:<skill>` invocation form entirely.

`pipeline-authoring` restates the environment contract in brief, because it
can't design stages without it; `deployment-environments` is where that
contract lives in full.

## Components

| Skill | Purpose |
|---|---|
| `deployment-strategy` | The entry point and the only skill that decides anything. Asks what ships / who uses it / what it does to data as multiple-choice options, detects the CI platform and existing environments before asking about them, maps answers onto a shape via a decision table that carries its own reasoning per row, routes write-volume problems to the architecture skills instead of answering them with packaging, then presents a deployment plan — including a mandatory "not covered" section — and **stops** for confirmation. |
| `container-authoring` | The image, and only when the shape includes one. Multi-stage builds, minimal non-root runtime bases with an explicit high UID, layer ordering that makes the cache work, `.dockerignore` (including its secret-leak property), exec-form `CMD` so `SIGTERM` actually reaches the app, readiness-vs-liveness (and why a liveness probe that checks the database causes outages), no secrets in layers or build args, commit-SHA tags rather than `:latest`, and a local-dev compose file. |
| `pipeline-authoring` | The pipeline, for GitHub Actions / GitLab CI / Azure DevOps / Cloud Build / Jenkins. Stage ordering cheapest-first, gates that fail rather than warn, build-once-then-promote, OIDC federation with per-environment least-privilege identities instead of long-lived keys, provenance/signing/SBOM, platform-enforced approval, canary rollout with automatic abort, and a rollback path that has actually been exercised. |
| `deployment-environments` | The dev/staging/prod contract, on every shape including static. What must differ (secret values, endpoint URLs, scale, approvers, log verbosity) and what must not (the artifact, the runtime, the config *keys* — so a missing one fails in dev, not prod). Where secrets actually live and the three places they leak; config validated at startup rather than first use; expand-then-contract migrations so code can roll back past a schema change; why production data never moves downward; and environment parity as a reliability property worth writing down where it's deliberately broken. |
| `deployment-best-practices` | Review checklist for a setup that already exists, grouped by severity and framed by DORA's four key metrics. Leads with what causes incidents — mutable tags, rebuild-per-environment, an untested rollback, a liveness probe that checks the database, non-backward-compatible migrations, shell-form `CMD`, scaling against a fixed connection-pool ceiling — then security, cost/speed, and operability. Reports rather than fixes, caps the list, and has an explicit "what not to flag" section so a small service with a small pipeline isn't written up as a defect. |

## Setup

No dependencies of its own. Docker is only needed if the confirmed shape
includes an image — which is a question the plugin asks, not an assumption it
makes.

## Usage

- "How should we deploy this" / "do we need Docker" / "should we containerize" / "where should this run" → `deployment-strategy`
- "We need a staging environment" / "set up deployment" → `deployment-strategy` (it establishes the shape first)
- "Write a Dockerfile" / "containerize this" / "our image is huge" / "docker build is slow" → `container-authoring`
- "Run the stack locally" / "set up docker compose" → `container-authoring`
- "Set up CI/CD" / "write a GitHub Actions workflow" / "GitLab pipeline" / "Jenkinsfile" → `pipeline-authoring`
- "Automate the deploy" / "add a deploy step" / "how do we roll back" / "our pipeline is too slow" → `pipeline-authoring`
- "Set up staging" / "environment variables per environment" / "how do we manage secrets" / "dev vs prod config" → `deployment-environments`
- "Our staging doesn't match prod" / "we can't roll back this migration" → `deployment-environments`
- "Review our deployment" / "is this pipeline any good" / "we keep breaking prod" / "why are our deploys risky" → `deployment-best-practices`

Start at `deployment-strategy` even when the request names a file. A request
for a Dockerfile on a project that should ship static files is best answered by
saying so — which is the one thing a skill that starts at the Dockerfile can't
do.
