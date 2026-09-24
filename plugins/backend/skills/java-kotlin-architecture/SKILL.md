---
name: java-kotlin-architecture
description: >
  Thin architecture-routing adapter for JVM backends written in Java or
  Kotlin (typically Spring Boot) — confirms the stack, routes greenfield vs.
  existing work to the right entry point, and applies the framework-agnostic
  three-zone model (core/modules/shared) to a JVM service. Deliberately
  thin: no Java/Kotlin naming-convention, data-layer, testing, or bootstrap
  specialist skills exist yet in this plugin — this skill says so and asks
  rather than inventing them. Use when the user says things like "structure
  my Spring Boot app", "where does this Java/Kotlin backend code belong",
  "set up a Spring Boot project", or "how should I organize this JVM
  service".
---

# Java/Kotlin Architecture (thin adapter)

This skill exists so a JVM backend task reliably lands on *something* in
this plugin instead of falling through to nothing, or to advice borrowed
from the FastAPI adapter. It is intentionally minimal — a routing layer over
the framework-neutral model, not a Java/Kotlin specialist. Deeper
JVM-specific skills (module scaffolding, naming, data layer, testing,
bootstrap) are future work, not yet written. Java and Kotlin share this one
adapter because on Spring Boot — overwhelmingly the common case for either
language in this context — the architectural shape is identical; only
syntax differs.

## Step 0: Consult the codebase map first

If a sibling `codebase-map` plugin is installed, ask its `codebase-map-sync`
skill for cached facts about this repo before checking anything below
yourself. If that plugin isn't installed, fall through to Step 1's own live
check.

## Step 1: Detect the stack

Look for `pom.xml` (Maven) or `build.gradle`/`build.gradle.kts` (Gradle) at
the project root, and `.java`/`.kt` source files. Check for
`spring-boot-starter*` dependencies specifically — if present, this is
Spring Boot and the mapping below applies directly. If the project uses a
different JVM framework (Micronaut, Ktor, Quarkus), say so explicitly before
applying anything below; the three-zone mapping still holds conceptually,
but DI/bootstrap mechanics differ enough from Spring's that this skill
shouldn't claim familiarity it doesn't have yet.

## Step 1a: Check for an existing structure that predates this plugin

If the project already has an existing package structure not scaffolded by
this plugin, route to a sibling `architecture-foundations` plugin's
`existing-codebase-adoption` skill first — it decides whether Kaizen's
conventions or the existing structure govern before anything below gets
applied. If genuinely greenfield, skip to Step 2 — routing through a sibling
`architecture-foundations` plugin's `project-kickoff` skill for the
sequencing if this is the very start of a new project (there is no
`java-kotlin-project-bootstrap` skill yet — say so plainly and use Spring
Initializr as the starting point).

## Step 2: Apply the three-zone model, in Spring's vocabulary

- **`core/`** → the application entrypoint (`@SpringBootApplication` class),
  global `@Configuration` classes, security config, and global exception
  handlers (`@ControllerAdvice`). Imported only by the entrypoint.
- **`modules/`** → one package per business domain (e.g.
  `com.example.app.products`). Modules never reach into another module's
  package directly. Absent a JVM-specific naming skill yet, a reasonable
  per-module shape (borrowed from the FastAPI adapter's five-piece pattern,
  not an established Java/Kotlin convention — say so plainly): a domain
  entity/record, a `Service` class for orchestration, a `Repository`
  interface (Spring Data) implementing persistence, a `Controller` for the
  HTTP layer, and DTOs for request/response shapes distinct from the JPA
  entity.
- **`shared/`** → a `common`/`shared` package for zero-business-logic
  reusables: generic exception types, pagination helpers, base
  configuration.

Layering rule inside a module: **`Controller → Service → domain`**, with
`Repository` implementing an interface the domain/service layer depends on
— `Controller` never calls `Repository` directly.

## Step 3: What this skill does not yet cover

There is no Java/Kotlin-specific naming-convention, data-layer, testing, or
bootstrap skill in this plugin. Don't invent package-naming rules, ORM
choices (JPA/Hibernate vs. jOOQ vs. plain JDBC), or testing setup patterns
(JUnit vs. Kotest) as if they were established convention — ask the user
what they'd like, or point at the closest neutral guidance
(`architecture-foundations`'s `test-pyramid` skill still applies, since it's
concept-level, not stack-specific).

## Step 4: Never assume

Per the `working-agreement` skill's rule 4: this adapter is thin by design,
so silent defaults here are more likely to be wrong than on the FastAPI
adapter. Check for existing project documentation first, and ask before
picking a persistence approach, validation library, or Java-vs-Kotlin
idiom set the project hasn't already committed to.

---
_Last reviewed: 2026-08-24_
