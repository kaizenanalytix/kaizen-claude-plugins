---
name: nestjs-architecture
description: >
  Thin architecture-routing adapter for NestJS backends — confirms the
  project is genuinely NestJS, routes greenfield vs. existing work to the
  right entry point, and maps the framework-agnostic three-zone model
  (core/modules/shared) onto Nest's own module/DI system, which already
  mirrors it closely. Deliberately thin: no NestJS naming-convention,
  data-layer, testing, or bootstrap specialist skills exist yet in this
  plugin — this skill says so and asks rather than inventing them. Use when
  the user says things like "structure my NestJS app", "where does this Nest
  module belong", "set up a NestJS project", or "how should I organize this
  Nest codebase".
---

# NestJS Architecture (thin adapter)

This skill exists so a NestJS task reliably lands on *something* in this
plugin instead of falling through to nothing, or to advice borrowed from the
FastAPI adapter. It is intentionally minimal — a routing layer over the
framework-neutral model, not a NestJS specialist. Deeper NestJS-specific
skills (module scaffolding, naming, data layer, testing, bootstrap) are
future work, not yet written.

## Step 0: Consult the codebase map first

If a sibling `codebase-map` plugin is installed, ask its `codebase-map-sync`
skill for cached facts about this repo before checking anything below
yourself. If that plugin isn't installed, fall through to Step 1's own live
check.

## Step 1: Detect the stack

Look for `@nestjs/core` in `package.json` dependencies, or a `nest-cli.json`
at the project root. If neither is present, say so and stop — this skill is
NestJS-specific (a bare Express/Fastify app is the sibling
`nodejs-architecture` skill's territory).

## Step 1a: Check for an existing structure that predates this plugin

If the project already has an existing module structure not scaffolded by
this plugin, route to a sibling `architecture-foundations` plugin's
`existing-codebase-adoption` skill first — it decides whether Kaizen's
conventions or the existing structure govern before anything below gets
applied. If genuinely greenfield, skip to Step 2 — routing through a sibling
`architecture-foundations` plugin's `project-kickoff` skill for the
sequencing if this is the very start of a new project (there is no
`nestjs-project-bootstrap` skill yet — say so plainly and use the Nest CLI's
own scaffold as the starting point).

## Step 2: Nest's module system already IS most of the three-zone model

Unlike a bare Node.js app, NestJS ships an opinionated module/DI system that
maps onto `clean-architecture`'s three zones almost without translation:

- **`core/`** → Nest's root `AppModule` plus any module explicitly marked
  global (`@Global()`) — bootstrap, global pipes/guards/filters, and
  cross-cutting config. Imported by the entrypoint (`main.ts`) and by
  feature modules that need shared infrastructure.
- **`modules/`** → Nest feature modules (`ProductsModule`, `OrdersModule`,
  each with its own folder). Feature modules never import each other's
  providers directly — if two need to share something, promote it to a
  module both explicitly import, or route it through a shared module. Within
  each feature module, the existing Nest convention of
  `*.controller.ts` / `*.service.ts` / `*.module.ts` (plus a DTO folder and
  a repository/entity layer if persistence is involved) already lines up
  with `api → service → domain`/`infra` from the FastAPI adapter's
  five-piece shape — don't rename Nest's own generated file suffixes to
  match FastAPI's naming; the zone mapping is what matters, not the file
  names.
- **`shared/`** → a `SharedModule` (or Nest's own "common" convention) for
  reusable, zero-business-logic providers, pipes, and decorators.

Nest's `@Injectable()` DI already gives request/module-scoped state a native
mechanism — don't invent a parallel "module-context" concept the way the
neutral model discusses for UI apps; Nest's provider scopes (`DEFAULT`,
`REQUEST`, `TRANSIENT`) are that answer.

## Step 3: What this skill does not yet cover

There is no NestJS-specific naming-convention, data-layer, testing, or
bootstrap skill in this plugin. Don't invent folder skeletons, ORM choices
(TypeORM vs. Prisma vs. Mongoose), or testing setup patterns as if they were
established convention — ask the user what they'd like, or point at the
closest neutral guidance (`architecture-foundations`'s `test-pyramid` skill
still applies, since it's concept-level, not stack-specific).

## Step 4: Never assume

Per the `working-agreement` skill's rule 4: this adapter is thin by design,
so silent defaults here are more likely to be wrong than on the FastAPI
adapter. Check for existing project documentation first, and ask before
picking an ORM, validation approach (`class-validator` vs. Zod), or
microservice-transport choice the project hasn't already committed to.

---
_Last reviewed: 2026-08-24_
