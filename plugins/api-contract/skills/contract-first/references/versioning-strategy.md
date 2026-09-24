# Versioning Strategy

## Recommended default: URL versioning

Put the version in the URL path: `/api/v1/...`, `/api/v2/...`. This is the
recommended default for the API contract because:

- **Old and new contracts can run side by side.** `/api/v1` and `/api/v2` are
  served by the same deployment (or different deployments behind the same
  gateway) simultaneously. Clients migrate at their own pace instead of being
  forced to move the instant `v2` ships.
- **It's visible everywhere.** The version is in every request log, every
  generated types file's originating schema, every API doc URL — no need to
  inspect headers or a payload envelope to know which contract you're looking
  at.
- **It composes cleanly with the diff gate.** `openapi.json` for `v1` and
  `openapi.json` for `v2` are two separate committed artifacts; `diff_schema.py`
  compares within a version, and a breaking change is simply never applied to
  an existing version's file — it goes into the next version's file instead.

Alternatives (header-based versioning, content negotiation via `Accept`,
query-param versioning) are viable but are not the default here: they hide
the version from casual inspection and don't give you the same "two versions,
two files, two OpenAPI documents" clarity that makes the diff gate simple to
reason about.

## The core rule: breaking changes ship as a new version, never in place

A breaking change (see `breaking-change-policy.md` for the exact list) must
never be applied to the `openapi.json` of a version that's already shipped.
Instead:

1. Copy the current version's schema/routes to the next version
   (`v1` → `v2`).
2. Make the breaking change only in `v2`.
3. `v1` keeps serving its old contract, unchanged, until it's deprecated.
4. `diff_schema.py` run against `v1`'s previous and current `openapi.json`
   should show *zero* breaking changes, always — if it doesn't, the change
   landed in the wrong version.

## Deprecation timeline once a new version ships

A reasonable default timeline (adjust to the consuming teams' release
cadence and any contractual/SLA obligations):

| Milestone                                  | Action                                                        |
|---------------------------------------------|----------------------------------------------------------------|
| `v2` ships                                  | `v1` marked deprecated in docs and in `openapi.json` (`deprecated: true` on affected operations); both versions fully supported |
| +30 days                                    | Deprecation warning added to `v1` responses (e.g. a `Deprecation`/`Sunset` HTTP header); consuming teams notified via the changelog |
| +90 days                                    | `v1` enters a support-only freeze: bug fixes only, no new features backported |
| +180 days (or per contractual SLA)          | `v1` sunset — routes return `410 Gone` or are removed entirely; final changelog entry recorded |

Track "who still calls `v1`" before sunsetting — if a sibling `frontend` plugin (or
any other known consumer) hasn't migrated, extend the timeline rather than
breaking them silently. The versioning scheme itself is contract-visible (see
SKILL.md), so changing these timelines is a coordination event, not a
unilateral backend decision.

## Minor, non-breaking evolution within a version

Additive changes (new endpoint, new optional field, new enum value where
consumers are documented to ignore unknown values) do NOT require a new
version — they land directly in the current version's `openapi.json` and
pass the diff gate silently. Versioning is reserved for breaking changes
only; don't bump the version for every schema change or you lose the benefit
of URL versioning's stability signal.
