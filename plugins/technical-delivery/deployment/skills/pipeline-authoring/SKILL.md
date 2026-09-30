---
name: pipeline-authoring
description: >
  Writes the CI/CD pipeline for whichever platform the project actually uses —
  GitHub Actions, GitLab CI, Azure DevOps, Cloud Build, or Jenkins — with
  stages ordered cheapest-first, gates that block the right things, one
  artifact built once and promoted across dev/staging/prod, OIDC federation
  instead of long-lived cloud keys, signed artifacts and an SBOM, manual
  approval as a platform control, canary rollout, and a rollback path that has
  actually been exercised. Use when the user says things like "set up CI/CD",
  "write a GitHub Actions workflow", "GitLab pipeline", "Jenkinsfile", "add a
  deploy step", "automate the deploy", "how do we roll back", or "our pipeline
  is too slow".
---

# Pipeline Authoring

A pipeline exists to make shipping boring. The four things it's optimizing are
DORA's key metrics: how often you can deploy, how long a change takes to reach
production, how often a deploy breaks something, and how fast you recover when
one does. Every rule below trades against one of those four — if a proposed
step doesn't improve one of them, it's ceremony.

## 0. Know the platform and the shape first

Two things must already be settled, and this skill does not guess at either:

- **The deployment shape** — established by a sibling `deployment-strategy`
  skill and confirmed by the user. A pipeline that pushes an image for a
  project that should publish static files is the wrong pipeline, not a
  fixable one.
- **The CI platform** — detected from the repo (`.github/workflows/`,
  `.gitlab-ci.yml`, `azure-pipelines.yml`, `cloudbuild.yaml`, `Jenkinsfile`)
  or answered by the user. **Never default to GitHub Actions because it's
  common.** The concepts below are identical across all five; only the syntax
  differs, and writing for the wrong one is a rewrite.

If either is unsettled, stop and route to `deployment-strategy`.

## 1. Stage order: cheapest and fastest first

Order stages so the failure a developer is most likely to hit is also the one
they hear about soonest. A lint error should surface in thirty seconds, not
after an eleven-minute image build.

```
1. lint + typecheck            seconds        cheapest signal
2. unit + integration tests    a minute or two
3. contract / schema gate      seconds        (see section 4)
4. build image or bundle       minutes        the expensive step
5. scan the artifact           a minute
6. deploy dev                  ~a minute
7. e2e against staging         minutes        the slowest signal
8. approval -> deploy prod     human time
```

Two things follow from this ordering. **Run 1 and 2 in parallel** where the
platform allows — they don't depend on each other. And **never build before
the tests pass**; the build is the expensive step and a failing test has
already told you not to bother.

## 2. Build once, promote the same artifact

This is the rule the rest of the pipeline hangs off: **the artifact is built
exactly once, tagged by commit SHA, and that same artifact is promoted through
every environment.**

Not rebuilt per environment. If staging and production are separate builds,
then staging never tested the bytes production runs, the artifact that passed
every gate is not the artifact deployed, and "roll back" has no well-defined
target. Rebuilding also quietly reintroduces nondeterminism — a base image
that moved, a dependency that resolved differently — at the exact moment you
least want a new variable.

For a frontend bundle this has one real consequence worth stating plainly:
**environment values cannot be baked in at build time.** A Vite build that
inlines `VITE_API_URL` produces an artifact that is only valid for one
environment, which is incompatible with promoting it. The fix is a small
runtime config — a `config.json` the app fetches on boot, or values injected
into `index.html` at deploy time — and that cost buys a single verified
artifact identity. A sibling `frontend` plugin's `vite-build-output` skill
describes both approaches; this is the pipeline's reason for choosing the
second.

## 3. The environment contract, in brief

Three environments, one artifact moving through them. A sibling
`deployment-environments` skill owns this in full — config injection, secret
storage, migration safety, data handling — but a pipeline can't design its
stages without the shape of it:

| | dev | staging | prod |
|---|---|---|---|
| Trigger | merge to main | promote from dev | promote from staging, manual approval |
| Artifact | built here, tagged by SHA | **the same SHA**, not rebuilt | **the same SHA**, not rebuilt |
| Data | ephemeral, disposable | seeded, representative | real — never copied downward |
| Config | injected at deploy | injected at deploy | injected at deploy |

**Must differ between environments:** secret values, endpoint URLs, replica
counts and autoscaling bounds, instance size, who may approve a deploy, log
verbosity.

**Must not differ:** the artifact, the runtime and base image, the dependency
versions, the deploy mechanism, and the config *keys* — only their values.
Keeping the keys identical is what makes a missing one fail in dev instead of
production.

## 4. Gates, and what each one blocks

A gate that warns is not a gate. Each of these fails the pipeline:

- **Lint, typecheck, unit and integration tests** — block everything.
- **The OpenAPI contract gate.** A sibling `api-contract` plugin's
  `contract-first` skill already defines this: export the current schema, diff
  it against the committed one with `scripts/diff_schema.py`, and fail on a
  breaking change. **Wire that existing script in as a step — do not write a
  second schema differ.** It belongs early, because it's fast and it catches
  the change most likely to break the other side of the stack.
- **Artifact scan** — image or dependency vulnerability scan, plus a secret
  scan. A secret finding is a build failure, not a warning; by the time it's a
  warning it's in the registry.
- **Migration dry-run** against staging, before prod.
- **End-to-end tests** — these run against **deployed staging**, which is a
  sibling `e2e-testing` plugin's stated posture: point `E2E_BASE_URL` and
  `E2E_API_BASE_URL` at the real staging deployment. **Do not build or boot the
  backend inside the e2e job.** A suite that spins up its own stack tests a
  stack that doesn't exist anywhere, and it's the slowest, flakiest way to get
  a worse signal.
- **Manual approval** — before prod only. Section 7.

## 5. Authenticate with OIDC, not long-lived keys

A long-lived cloud credential in CI secrets is the highest-value, longest-lived
secret most teams have, and it's readable by anyone who can edit a workflow
file.

Use **OIDC / workload identity federation**: the CI platform mints a
short-lived token, the cloud provider trusts it based on the repository,
branch, and environment it came from, and nothing durable is stored anywhere.
All five platforms support this.

Two things to get right beyond turning it on:

- **Scope the trust condition narrowly** — to the specific repository *and*
  branch or environment. A trust policy that accepts any workflow from the
  whole org means any repo in the org can deploy your production service.
- **A separate, least-privilege identity per environment.** The dev deploy
  identity must not be able to touch production. Sharing one identity across
  environments means the approval gate in section 7 protects nothing — the dev
  path could already do it.

## 6. Supply chain: provenance, signing, SBOM

Three cheap steps that together let you answer "what is running, and where did
it come from" — the SLSA framework's concern:

- **Provenance** — record what built this artifact, from which commit, with
  which inputs.
- **Signing** — sign the artifact in CI and verify the signature at deploy, so
  the runtime only accepts artifacts your pipeline actually produced.
- **SBOM** — generate and retain a bill of materials per build. Its value shows
  up on the day a CVE lands and the only question that matters is "are we
  affected, and where" — answerable in seconds with an SBOM, and a multi-day
  audit without one.

## 7. Approval is a platform control, not a message

Production approval must be enforced by the platform — GitHub Actions'
protected environments with required reviewers, GitLab's protected
environments, Azure DevOps' environment approvals, and so on — so the deploy
job *cannot start* until a named person approves.

"Ask in the team channel first" is not an approval gate; it's a convention that
holds until the first urgent Friday. Wire the same distinction into the
deploy identity: the environment's credentials should only be issuable by an
approved run.

## 8. Progressive rollout, and a rollback path you've actually used

Deploy to a slice, watch, then widen — canary a small percentage of traffic,
hold long enough for real signal, then shift the rest. This is the SRE
practice of canarying, and the reason for it is arithmetic: a bad release
caught at 10% of traffic costs a tenth as much as one caught at 100%.

- **Automate the abort.** Watch error rate and latency against the SLO during
  the canary window and roll back automatically on regression. A canary nobody
  is watching is just a slower deploy.
- **Rollback is redeploying the previous SHA** — which works only because of
  section 2. Immutable tags are what make rollback a lookup instead of a
  rebuild.
- **Test the rollback path.** An untested rollback is a hypothesis, and the
  first time you'd find out is during an incident. Exercise it deliberately.
- **Migrations constrain rollback**, and this is the part most often missed:
  code can roll back in seconds, a schema cannot. Keep migrations forward-only
  and backward-compatible for at least one release, so the previous version of
  the code still runs against the new schema. Expand first, contract later, in
  a separate release.

## 9. Platform notes

The concepts above are identical everywhere. What differs:

- **GitHub Actions** — `.github/workflows/*.yml`. Protected environments carry
  the approval gate and the environment-scoped secrets; OIDC via
  `permissions: id-token: write`. Already the assumed platform in
  `contract-first`'s diff-gate excerpt.
- **GitLab CI** — `.gitlab-ci.yml`. Stages and `needs:` for the DAG, protected
  environments for approval, `id_tokens` for OIDC.
- **Azure DevOps** — `azure-pipelines.yml`. Stages and deployment jobs;
  environment approvals and checks; workload identity federation for OIDC.
- **Cloud Build** — `cloudbuild.yaml`. Steps run in order and share a
  workspace; approvals are a build-trigger setting; it authenticates as a
  service account natively, so the OIDC concern mostly falls away *within* GCP
  but still applies for anything outside it.
- **Jenkins** — `Jenkinsfile`, declarative pipeline. `input` for approval, but
  credential handling is the weak point: it's the platform where long-lived
  secrets are most likely to already be in use, so the OIDC/short-lived
  migration in section 5 matters most here.

## Rules to enforce everywhere

- **Write for the platform the project actually uses.** Detect it; never
  default to GitHub Actions because it's the most common.
- **Cheapest, fastest signal first.** Nothing expensive runs before the cheap
  thing that would have failed anyway.
- **Build once; promote the same SHA.** Rebuilding per environment invalidates
  every gate that ran before it and makes rollback undefined.
- **Never bake environment values into a promotable artifact.** Inject at
  deploy; use a runtime config for frontends.
- **Reuse the existing contract gate.** `contract-first`'s
  `scripts/diff_schema.py` is the schema differ — don't write a second one.
- **E2E runs against deployed staging.** Never build or boot the backend
  inside the e2e job.
- **A gate fails the build.** A gate that only warns is documentation.
- **OIDC, never long-lived cloud keys** — with the trust condition scoped to
  the repo and environment, and a separate least-privilege identity per
  environment.
- **Approval is enforced by the platform**, not by a message in a channel.
- **Rollback is redeploying the previous SHA, and it has been tested.** An
  untested rollback is a hypothesis.
- **Migrations stay backward-compatible for one release.** Code rolls back in
  seconds; a schema does not.

---
_Last reviewed: 2026-08-24_
