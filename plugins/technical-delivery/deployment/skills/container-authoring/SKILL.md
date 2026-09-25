---
name: container-authoring
description: >
  Writes and reviews the container image for a service — multi-stage builds, a
  minimal non-root runtime base, layer ordering that makes the build cache
  actually work, .dockerignore, signal handling so shutdown is graceful,
  health probes, immutable commit-SHA tags rather than :latest, and a
  docker-compose file for running the stack locally. Only applies when the
  deployment shape actually includes an image. Use when the user says things
  like "write a Dockerfile", "containerize this", "our image is huge", "docker
  build is slow", "review this Dockerfile", "run the stack locally", or "set
  up docker compose".
---

# Container Authoring

An image is a build artifact, and the properties that matter are the same ones
that matter for any artifact: it should be small, reproducible, identifiable,
and safe to run. Most bad Dockerfiles are bad in the same handful of ways, all
of which are cheap to avoid at authoring time and expensive to retrofit once
something is deployed from them.

The practices here are the widely-published container build practices — Google's
*Best practices for building containers* is the canonical write-up of most of
them, and the security items line up with the Cloud Architecture Framework's
security pillar. They are named and explained below rather than cited, so the
reasoning travels with the rule.

## 0. First: does this project even need an image?

**If a sibling `deployment-strategy` skill's confirmed shape is static
hosting, a PaaS buildpack, or a serverless zip, stop — this skill does not
apply.** Writing a Dockerfile for a built frontend that a CDN should serve
adds a web server to patch and a registry to operate, in exchange for nothing.
Say so and hand back.

If no shape has been decided yet, don't start here at all. Route to
`deployment-strategy` first; it establishes whether an image is the right
answer, and this skill assumes that question is already settled.

The one legitimate exception for containerizing a static frontend: the project
already runs an orchestrator and the team wants a single uniform deploy
mechanism for everything. That's an operability argument, not a technical one —
and it's worth naming as the reason so nobody later mistakes it for a
requirement.

## 1. Multi-stage, always

A build needs compilers, dev dependencies, and source. A runtime needs none of
those. Putting them in one stage ships your toolchain to production — a larger
image, a larger attack surface, and more CVEs to patch, for no runtime benefit.

```dockerfile
# ---- build stage ----------------------------------------------------------
FROM python:3.12-slim AS build
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1

# Dependency manifests first — see section 3 on why this ordering matters.
COPY requirements.txt ./
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --require-hashes -r requirements.txt

# ---- runtime stage --------------------------------------------------------
FROM python:3.12-slim AS runtime

# A real user with an explicit, high, non-colliding UID — see section 5.
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home app

COPY --from=build /opt/venv /opt/venv
WORKDIR /app
COPY --chown=app:app . .

USER 10001
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1
EXPOSE 8000

# Exec form, not shell form — see section 6.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 2. Choose the runtime base deliberately

Smaller is better, for three concrete reasons rather than as an aesthetic:
fewer packages means a smaller attack surface, fewer CVEs to triage every time
a scanner runs, and faster pulls on every scale-up and cold start.

The ladder, and when each rung is right:

- **`-slim` variants** (`python:3.12-slim`, `node:22-slim`) — the sensible
  default. Small, but still has a shell and a package manager, so debugging in
  place still works.
- **Distroless** — no shell, no package manager, no busybox. Materially
  smaller attack surface and the right choice for a hardened production
  service. The cost is real: you cannot `exec` into it to poke around, so it
  demands that your logs and health endpoints are actually good.
- **Alpine** — small, but built on musl rather than glibc. Fine for Go or
  static binaries; for Python it can mean slower builds and subtly different
  behaviour in wheels expecting glibc. Don't reach for it reflexively.
- **Full base images** (`python:3.12`, `ubuntu`) — only when something you
  genuinely need lives there.

**Pin the base image.** `python:3.12-slim` rather than `python:latest`, and
pin by digest (`python:3.12-slim@sha256:…`) where the project wants builds to
be byte-reproducible. An unpinned base means the image you build today and the
one you build after a rollback are not the same image.

## 3. Order layers so the cache actually works

Docker caches per layer and invalidates every layer after the first change. So
the order is: **things that rarely change first, things that change every
commit last.**

That means dependency manifests get copied and installed *before* application
source is copied in:

```dockerfile
COPY requirements.txt ./          # changes rarely
RUN pip install -r requirements.txt   # the expensive layer, now cached
COPY . .                          # changes every commit
```

Invert those and every one-line source change reinstalls every dependency.
This is the single most common cause of "why does our build take nine
minutes", and the fix is two lines in a different order.

**Install from a lockfile**, not a loose range — `requirements.txt` with
pinned versions (ideally `--require-hashes`), `npm ci` rather than
`npm install`, `poetry install --no-root` against a committed `poetry.lock`.
A build that resolves versions at build time is a build whose output changes
without its input changing.

## 4. `.dockerignore` — smaller context, and one real security property

Everything in the build context is sent to the daemon and is available to
`COPY`. Without a `.dockerignore`, `COPY . .` can pull in `.git` (your whole
history), `.env` (your actual secrets), `node_modules` from the host, and test
fixtures — some of which then persist in a layer.

Start from:

```
.git
.gitignore
node_modules
__pycache__
*.pyc
.venv
.env
.env.*
dist
build
coverage
.pytest_cache
*.md
Dockerfile
docker-compose.yml
```

The `.env` and `.git` lines are the ones that matter beyond build speed.

## 5. Run as a non-root user

A process that doesn't need root shouldn't have it — a container escape from a
root process is a materially worse day than one from an unprivileged process,
and many managed runtimes and cluster policies reject root containers outright.

Create a real user with an **explicit, high UID** (10001 above rather than
letting the system pick), because cluster security policies frequently assert
"must run as non-root with UID > 10000" and a system-assigned low UID will
fail that check. Put the `USER` line after the last instruction that needs
write access, and use `COPY --chown` rather than a separate `chmod` layer.

Files the app must write at runtime need explicit ownership. If the app writes
nothing, keep the filesystem read-only at the runtime level — that's a
platform setting, but it's this file's job not to depend on writability it
doesn't need.

## 6. PID 1, signals, and graceful shutdown

The process your `CMD` starts becomes PID 1, and PID 1 does not get default
signal handlers. Get this wrong and every deploy, scale-down, and rollback
kills in-flight requests instead of draining them.

- **Use the exec form**: `CMD ["uvicorn", "main:app"]`, never
  `CMD uvicorn main:app`. The shell form runs your process as a child of
  `/bin/sh -c`, which does not forward `SIGTERM` — so the platform sends
  `SIGTERM`, nothing happens, and it gets `SIGKILL`ed at the end of the grace
  period, mid-request, every single time.
- **Handle `SIGTERM` in the app**: stop accepting new work, finish what's in
  flight, close pool connections, exit. Uvicorn and Gunicorn do this already;
  custom entrypoints and shell wrappers usually don't.
- **If you need an init**, use the platform's (`--init`, or the orchestrator's)
  rather than writing a shell wrapper that reaps children badly.
- **One concern per container.** One process group doing one job. Two
  unrelated processes in one image means the platform's health checking,
  restarts, and scaling all apply to the wrong unit — and you can no longer
  scale or roll back one without the other.

## 7. Readiness and liveness are different questions

They get conflated constantly, and conflating them causes outages in both
directions.

- **Readiness** — "can this instance serve traffic *right now*?" Fails during
  startup, while warming a cache, or when a required dependency is unreachable.
  Failing readiness removes the instance from the load balancer; it does not
  restart it.
- **Liveness** — "is this process wedged and beyond recovery?" Failing
  liveness *restarts the container*.

The dangerous mistake is a liveness probe that checks a downstream dependency:
when the database has a blip, every instance fails liveness, every instance
restarts simultaneously, and a brief dependency problem becomes a full outage
plus a thundering herd of reconnects. **Liveness checks the process. Readiness
checks the dependencies.**

Expose both as cheap endpoints that don't authenticate and don't touch
expensive work — a readiness check that runs a real query is a self-inflicted
load generator.

## 8. Never put a secret in an image

Image layers persist. A secret `COPY`d in and deleted in a later layer is
still in the image, still extractable, and now also in your registry and in
every cache that pulled it. The same goes for `ARG`/`--build-arg` values,
which are recorded in image metadata.

- Runtime configuration and secrets are **injected at deploy time** by the
  platform's secret store, never baked in. That's `deployment-environments`'
  territory.
- If the *build* needs a credential (a private package registry), use the
  build backend's secret mount (`RUN --mount=type=secret`), which is not
  persisted in a layer — not `ARG`.
- Scan the built image in CI, and treat a secret finding as a build failure
  rather than a warning. `pipeline-authoring` places that gate.

## 9. Tag immutably

**Never deploy `:latest`.** It's a mutable pointer, which means you cannot say
what's running, cannot reproduce it, and cannot roll back to a specific thing
— "roll back to latest" is not a sentence.

Tag by **commit SHA** (`myapp:9f3c1a7`), and reference by **digest**
(`myapp@sha256:…`) where the platform supports it. This is what makes
build-once-then-promote possible: the same SHA moves from dev to staging to
prod, so staging tested exactly the bytes production runs. A human-readable
tag (`v1.4.2`) alongside the SHA is fine as an alias; it just isn't the
identity.

## 10. The local compose file

`docker-compose.yml` is for **local development only** — the thing that makes
a containerized project actually pleasant to work on, and the thing that lets
a new joiner get a working stack in one command. It is not a deployment
mechanism, and it should never be the source of truth for production config.

```yaml
services:
  api:
    build:
      context: .
      target: build          # dev tooling present; prod builds `runtime`
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./:/app              # live reload; not a production pattern
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://app:localdev@db:5432/app
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16-slim
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: localdev     # local-only, never a real secret
      POSTGRES_DB: app
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app"]
      interval: 5s
      retries: 10
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

Three things worth noting in that file: it targets the **`build` stage** so
dev tooling is present, it uses `depends_on: condition: service_healthy` so
the API doesn't race the database, and its password is obviously local. Never
put a real credential in a compose file — it's committed.

If a sibling `e2e-testing` plugin's Playwright suite needs a real backend
locally, this file is what provides it; in CI, that suite runs against a
deployed staging environment instead, not against compose.

## Rules to enforce everywhere

- **Don't write a Dockerfile until the shape calls for one.** A static site or
  a buildpack deploy has no image; adding one is pure cost.
- **Always multi-stage.** The toolchain never ships to production.
- **Dependency manifests before source, always.** Layer ordering is the
  difference between a nine-second and a nine-minute build.
- **Install from a lockfile.** A build that resolves versions at build time
  isn't reproducible.
- **Pin the base image**, by tag at minimum and by digest where
  reproducibility matters. Never `:latest` in a `FROM`.
- **Non-root, with an explicit high UID.** Cluster policies reject root, and
  a low system-assigned UID fails the common `> 10000` assertion.
- **Exec-form `CMD`.** Shell form breaks `SIGTERM` and turns every deploy into
  killed in-flight requests.
- **Liveness checks the process; readiness checks the dependencies.** A
  liveness probe that pings the database converts a blip into an outage.
- **One concern per container.** Health checks, restarts, and scaling all
  assume one job per image.
- **No secrets in layers or build args, ever.** Layers persist, and metadata
  records `ARG` values. Inject at deploy time.
- **Tag by commit SHA, never deploy `:latest`.** Immutable identity is what
  makes promotion and rollback mean anything.
- **Compose is for local development only.** Never a deployment mechanism,
  never a home for a real credential.

---
_Last reviewed: 2026-08-24_
