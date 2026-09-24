---
name: nodejs-architecture
description: >
  Thin architecture-routing adapter for generic Node.js backends (Express,
  Fastify, or a bare http server — not NestJS, which has its own adapter) —
  confirms the stack, routes greenfield vs. existing work to the right entry
  point, and applies the framework-agnostic three-zone model
  (core/modules/shared) to a Node.js service. Deliberately thin: no Node.js
  naming-convention, data-layer, testing, or bootstrap specialist skills
  exist yet in this plugin — this skill says so and asks rather than
  inventing them. Use when the user says things like "structure my Node
  backend", "where does this Express/Fastify code belong", "set up a Node.js
  API project", or "how should I organize this Node service".
---

# Node.js Architecture (thin adapter)

This skill exists so a generic Node.js backend task reliably lands on
*something* in this plugin instead of falling through to nothing, or to
advice borrowed from the FastAPI adapter. It is intentionally minimal — a
routing layer over the framework-neutral model, not a Node specialist.
Deeper Node-specific skills (module scaffolding, naming, data layer,
testing, bootstrap) are future work, not yet written. If the project uses
NestJS specifically, use the sibling `nestjs-architecture` skill instead —
Nest's own module/DI system needs a different translation than a bare
Express/Fastify app.

## Step 0: Consult the codebase map first

If a sibling `codebase-map` plugin is installed, ask its `codebase-map-sync`
skill for cached facts about this repo before checking anything below
yourself. If that plugin isn't installed, fall through to Step 1's own live
check.

## Step 1: Detect the stack

Look for `express` or `fastify` in `package.json` dependencies, with no
`@nestjs/core` present (that's the sibling `nestjs-architecture` skill's
territory) and no frontend framework markers (`react`, `vue`,
`@angular/core`, `next`) in the same `package.json` — a Node.js file inside a
frontend project's build tooling is not a backend.

If none of these resolve and the user wants a new service, say so and ask
which framework (or none — a bare `http`/`node:http` server) before
proceeding, rather than guessing Express by default.

## Step 1a: Check for an existing structure that predates this plugin

If the project already has an existing `core/`/`modules/` split, or any
service structure not scaffolded by this plugin, route to a sibling
`architecture-foundations` plugin's `existing-codebase-adoption` skill first
— it decides whether Kaizen's conventions or the existing structure govern
before the three-zone model below gets applied to anything. If genuinely
greenfield, skip to Step 2 — routing through a sibling
`architecture-foundations` plugin's `project-kickoff` skill for the
sequencing if this is the very start of a new project (there is no
`nodejs-project-bootstrap` skill yet — say so plainly and scaffold the
minimum by hand).

## Step 2: Apply the three-zone model

A sibling `architecture-foundations` plugin's `clean-architecture` skill
defines the three zones for any application. Translate directly for a
Node.js service:

- **`core/`** — app bootstrap: the server factory, config/env loading,
  middleware registration, global error handling. Imported only by the
  entrypoint.
- **`modules/`** — one folder per business domain (e.g. `modules/products/`).
  Modules never import each other. Absent a Node-specific naming skill yet,
  mirror the shape `backend-architecture`'s FastAPI adapter uses as a
  reasonable default — `domain/`, `service.ts`, `infra/` (repository), a
  routes file, DI wiring — but say plainly that this is a borrowed pattern,
  not an established Node.js-specific convention, and ask before treating it
  as fixed.
- **`shared/`** — reusable code with zero business logic: generic
  middleware, base error types, formatting helpers.

## Step 3: What this skill does not yet cover

There is no Node.js-specific naming-convention, data-layer, testing, or
bootstrap skill in this plugin. Don't invent folder skeletons, naming rules,
ORM choices, or testing setup patterns as if they were established
convention — ask the user what they'd like, or point at the closest neutral
guidance (`architecture-foundations`'s `test-pyramid` skill still applies,
since it's concept-level, not stack-specific).

## Step 4: Never assume

Per the `working-agreement` skill's rule 4: this adapter is thin by design,
so silent defaults here are more likely to be wrong than on the FastAPI
adapter. Check for existing project documentation first, and ask before
picking a web framework, ORM, or validation library the project hasn't
already committed to.

---
_Last reviewed: 2026-08-24_
