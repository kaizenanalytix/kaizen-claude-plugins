# What to Test Where, In Detail

This reference expands the general rule with concrete example scenarios mapped to a
layer. It is intentionally tooling-independent — no specific testing framework or runner
is named anywhere here, since that mapping belongs to the stack-specific adapter plugins.

## Unit test scenarios

- A function that calculates a discount given a price and a set of rules — pure
  input/output, no I/O. Unit test.
- A validation function that checks whether a submitted form's fields meet business
  rules (required fields, valid ranges, cross-field consistency) — pure logic. Unit test.
- A function that transforms one data shape into another (e.g. normalizing a raw payload
  into an internal representation) — pure transformation. Unit test.
- A decision function that determines which of several code paths should run based on
  input state (e.g. "is this order eligible for expedited processing") — pure branching
  logic. Unit test.
- A class's internal state machine (e.g. valid transitions between statuses) tested by
  driving it through transitions and asserting on resulting state, with no real
  persistence or network involved. Unit test.
- Edge cases and boundary conditions of any of the above (empty input, maximum values,
  malformed input) — still pure logic, still unit tests, and usually where unit tests
  provide the most value per test written.

## Integration test scenarios

- A module that reads from and writes to a real-ish local dependency (e.g. a local
  instance of the kind of datastore it uses in production) — verifying the module's
  queries/writes actually behave as expected against something real, not a fake standing
  in for it. Integration test.
- Two internal modules or layers wired together through their real interface (not a
  stubbed one), to verify that the contract between them — the shape of data passed, the
  sequencing of calls — actually holds when both sides are real. Integration test.
- A piece of code that depends on real serialization/deserialization (e.g. does the
  object survive being written to and read back from a real local store, or serialized to
  and parsed back from a real format) with the same shape it went in with. Integration
  test.
- Verifying that a module's error handling actually triggers correctly against a real
  (local) failure condition from its dependency, rather than a hand-constructed fake
  error. Integration test.
- A configuration or wiring path that only manifests when several real internal pieces
  are actually assembled together, even though each piece's own logic is already
  unit-tested separately. Integration test — the goal here is testing the wiring, not
  re-testing the logic.

## End-to-end / contract test scenarios

- A full user journey from start to finish (e.g. "a user completes an entire checkout
  flow") exercised through the real, fully assembled system, the way an actual user would
  interact with it. E2E test.
- Verifying that a real request made the way a real caller would make it, against the
  fully running system, produces the expected real outcome — not verifying pieces in
  isolation, but the whole path. E2E test.
- A contract test between two independently developed systems: verifying that what one
  system actually produces (a real message, a real response shape) is genuinely
  consumable by what the other system actually expects, catching the case where each side
  independently assumed something different about the boundary between them. Contract
  test.
- A critical business flow that spans multiple domains/modules and where a failure would
  be severe enough (e.g. a payment flow, an irreversible action) that verifying it
  end-to-end, exactly as a real caller would exercise it, is worth the higher cost and
  slower feedback. E2E test — but keep the count of these deliberately small and
  reserved for the highest-value flows, since the cost per test is much higher than the
  other two layers.
- Any scenario that specifically depends on multiple real systems' actual behavior
  interacting together, where no combination of unit and integration tests (each testing
  one piece with the rest faked or localized) could have caught the failure. This is the
  precise justification for paying the e2e/contract cost at all — if a cheaper layer
  could have caught it, prefer the cheaper layer instead.

## A note on proportion

These example counts are illustrative, not prescriptive of an exact ratio, but the shape
should always taper sharply: many unit tests, a meaningfully smaller number of
integration tests, and a small, carefully chosen set of e2e/contract tests reserved for
what only that layer can catch. If a codebase's e2e/contract suite is doing the job that
integration or unit tests should be doing (e.g. re-verifying pure business logic that
happens to be reachable from a full user flow), that's wasted cost — push that coverage
down to the cheapest layer that can actually catch it, and reserve the expensive layers
for what only they can catch.
