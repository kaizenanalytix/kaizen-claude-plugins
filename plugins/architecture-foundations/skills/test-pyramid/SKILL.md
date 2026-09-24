---
name: test-pyramid
description: >
  Applies the tooling-agnostic test pyramid — unit, integration, and end-to-end/contract
  tests — to decide what kind of test a given piece of behavior needs and in what
  proportion each layer should be written. This skill should be used when the user asks
  "what should I test", "testing strategy", "test coverage layers", or needs help
  deciding what kind of test to write for a piece of code.
---

# The Test Pyramid, Tooling-Agnostic

Apply this model to decide what kind of test a given piece of behavior needs, independent
of which testing tool or framework is in use. Do not name any specific testing tool here
(no Vitest, Pytest, Playwright, or similar) — tool-specific setup belongs in the
`frontend` or `backend` adapter plugins.

## The three layers

**Unit tests** — exercise isolated logic with no real I/O (no real network, no real
database, no real filesystem). They test a single function, method, or small unit of
business logic in complete isolation from its collaborators, usually by substituting
fakes/stubs for anything external. Unit tests are cheap to write, fast to run, and
should make up the **largest** layer of the pyramid by a wide margin — most of an
application's logic should be verifiable this way.

**Integration tests** — exercise a slice of the real system wired together: a component
or module connected to its immediate real (or realistically-local) collaborators, rather
than every dependency faked out. For example, testing a module against a real-ish but
local version of a dependency it talks to, rather than the actual production external
system. Integration tests catch problems that only appear when pieces are actually wired
together (mismatched contracts between two internal pieces, real serialization/
deserialization issues, real query behavior) that unit tests, with everything faked,
cannot catch. There should be **fewer** integration tests than unit tests, and they cost
more to write and run.

**End-to-end (e2e) / contract tests** — exercise the full system, or a cross-boundary
contract between two systems, the way a real user or a real caller actually would: driving
the whole app top to bottom, or verifying that one system's output genuinely satisfies
what another system expects at the boundary between them. These are the **fewest** and
most expensive tests to write, run, and maintain — but they are the most valuable for
catching the class of bug that unit and integration tests structurally cannot see: bugs
that only manifest when every real piece is present and interacting, or when two
independently-developed systems' assumptions about each other turn out to be wrong. This
layer is also the one most likely to be skipped or under-invested-in under deadline
pressure, precisely because it is the most expensive per test — flag that as a real risk
to actively watch for, not just a theoretical concern, since skipping it removes the only
layer that catches whole-system and cross-boundary failures. Tool-specific implementation
of this layer lives in the adapter plugins: `react-testing`/`fastapi-testing`'s e2e slice
for single-stack flows, and a sibling `e2e-testing` plugin's `playwright-*` skills for
cross-stack business-workflow e2e that needs a real frontend, backend, and database
together.

For expanded example scenarios mapped to a layer, read `references/what-to-test-where.md`.

## The general rule for what belongs at which layer

Apply this rule when deciding where a new test should live:

- **Pure logic / business rules** — a calculation, a validation rule, a transformation, a
  decision function with no I/O — belongs at the **unit** layer. If it can be exercised
  by calling a function with inputs and asserting on outputs, with nothing real reached
  out to, it belongs here, and it should be the default choice unless there's a specific
  reason to go up a layer.
- **A component or module wired to its immediate collaborators** — verifying that a
  module correctly talks to its adjacent real (or local-realistic) dependency, that data
  flows through a small number of connected real pieces correctly — belongs at the
  **integration** layer. Use this when the thing being tested is specifically the wiring
  or contract between a small number of real pieces, not the business logic each piece
  contains in isolation (that logic should already be unit-tested separately).
- **A full user-facing flow, or a cross-service/cross-boundary contract** — verifying
  that an entire journey works end-to-end, or that what one system produces is actually
  consumable by another system that depends on it — belongs at the **e2e/contract**
  layer. Reserve this layer for the things that can only be verified with the real,
  fully-assembled system or a real cross-boundary check; don't use it as a substitute
  for the logic coverage that unit tests should already provide.

## Applying this when reviewing or planning tests

When asked what to test, or when reviewing test coverage:

1. Identify the pure logic in the change and confirm it has (or gets) unit tests first —
   this should be the majority of new test code for most changes.
2. Identify any points where the change wires previously-separate pieces together, and
   add integration coverage there — but only enough to verify the wiring/contract, not
   to re-verify logic already covered by unit tests.
3. Identify whether the change affects a full user journey or a boundary another system
   depends on, and add (or flag the absence of) e2e/contract coverage — and explicitly
   call out if this layer is being skipped due to time pressure, since that is exactly
   the failure mode to watch for.
4. If the proportions look inverted (e.g. mostly e2e tests and few unit tests, or heavy
   integration tests substituting for missing unit tests), flag that as a structural
   testing-strategy problem, not just a matter of taste — it usually means slow,
   expensive, flaky test suites and weak fast feedback on pure logic.

---
_Last reviewed: 2026-08-05_
