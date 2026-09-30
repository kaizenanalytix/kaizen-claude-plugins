---
name: state-philosophy
description: >
  Applies the framework-agnostic distinction between server state (remote data fetched
  and cached locally, subject to staleness and invalidation) and client/UI state
  (session-local state genuinely owned by the app), and the general concepts of
  cache invalidation and optimistic updates. This skill should be used when the user
  asks "where should this state live", "client vs server state", "caching strategy",
  or needs help deciding how to model or store a piece of application state.
---

# State Philosophy: Server State vs Client State

This skill is concept-only. It defines a framework-agnostic mental model for
classifying state and reasoning about caching and optimistic updates. Framework-specific
implementation (e.g. a specific data-fetching or state-management library, its APIs, its
config) lives in the `frontend` or `backend` plugin's adapter skills, not here — do not
name or recommend any concrete library, hook, or store implementation in this skill.

## The core distinction

Every piece of state an app holds falls into one of two buckets:

**Server state** — data that lives in a remote system (a database, another service, an
API) and is fetched and cached locally as a copy. Server state:
- Can go stale — the local copy may no longer match the remote source of truth.
- Needs an invalidation strategy — some mechanism for knowing when the local copy is
  outdated and needs to be refetched.
- Is not truly "owned" by the app — the app is only holding a cached view of data that
  another system is the real owner of.

**Client/UI state** — state that exists only for the current session or interaction:
open/closed toggles, selected tab, active filters, a form draft before submission, hover
or focus state, wizard step. Client state:
- Is genuinely owned by the app — there is no remote source of truth it's a copy of.
- Never goes stale in the server-state sense, because nothing external can invalidate it.
- Disappears (by design) when the session/interaction ends, unless explicitly persisted.

Before writing code that stores a piece of data, classify it into one of these two
buckets first. The classification determines how it should be stored and who should own
its lifecycle.

For an expanded decision table with example pieces of state and which bucket they
belong in, read `references/server-vs-client-state.md`.

## The rule adapters must follow

Never hand-copy a fetched server response into a generic, app-wide state container as if
it were client state. Doing so creates a second, independent copy of data that a
framework-specific data-fetching layer should already own and cache. The two copies will
inevitably drift — the hand-copied version has no invalidation hook back to the fetch
that produced it, so it goes stale silently while the "real" cache updates. Any
stack-specific adapter (frontend or backend) must fetch and cache server state through
whatever dedicated data-fetching mechanism that stack provides, and reserve
general-purpose app state containers for genuine client/UI state only.

## Caching and invalidation, as a concept

Cached server state needs a strategy for knowing when it has gone stale and needs to be
refreshed. The general pattern — independent of any specific implementation — is
tag/key-based invalidation: associate cached data with a key or tag that describes what
it represents, and when a mutation changes something that a given tag represents, mark
every cache entry under that tag as stale and trigger a refetch. This keeps the
invalidation logic declarative (describe *what* changed) rather than imperative (manually
patch every place that happened to cache the old value).

For the expanded pattern, including staleness and refetch-on-focus/refetch-on-mutation as
concepts, read `references/caching-and-invalidation.md`.

## Optimistic updates, as a concept

An optimistic update means updating the local view of server state immediately —
before the server has confirmed the change — so the interaction feels instantaneous
rather than waiting on a round trip. This is a UX technique layered on top of server
state, not a replacement for the real fetch/cache cycle.

The risk: because the update is applied before confirmation, every optimistic update
must define an explicit rollback path for the case where the server call fails. What
"rollback" means is specific to the mutation — sometimes it's reverting to the previous
cached value, sometimes it's re-fetching the authoritative state, sometimes it requires
surfacing an error to the user because the optimistic view already changed something
visible. Do not treat "rollback" as automatic or generic — always ask "what does undoing
this specific optimistic change actually look like?" before applying it.

For the expanded pattern and rollback requirement, read `references/optimistic-updates.md`.

## Quick classification check

When asked where a piece of state should live, ask: "If I closed and reopened the app
right now with no data cached, would this state need to come from a fetch, or would it
just reset to a default?" If it needs a fetch → server state. If it just resets → client
state.

---
_Last reviewed: 2026-08-05_
