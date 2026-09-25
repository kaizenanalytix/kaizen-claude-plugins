# Caching and Invalidation, In Detail

## Why cached server state needs a strategy at all

Once server state is cached locally, the cache is by definition a copy that can drift
from the remote source of truth. Without an explicit strategy for detecting and
correcting drift, the app will silently show outdated data — a list that doesn't include
a just-created item, a status that doesn't reflect a change made elsewhere, a value that
still shows the pre-edit number. The goal of a caching strategy is not to avoid caching
(caching is necessary for performance and responsiveness) — it's to make staleness
detectable and correctable in a predictable way.

## Tag/key-based invalidation as the general pattern

The general, implementation-independent pattern is:

1. **Associate cached data with a key or tag** that describes what it represents, not
   just how it happened to be fetched. E.g. "the list of products," "product #42,"
   "the current user's cart" — described in terms of the *resource*, not the specific
   request URL or function call that produced it.
2. **When a mutation changes something, declare which tags it affects.** Creating a new
   product affects the "list of products" tag. Editing product #42 affects both the
   "product #42" tag and (likely) the "list of products" tag, since the list's contents
   or summary might now be different.
3. **Mark every cache entry under an affected tag as stale.** This doesn't necessarily
   mean deleting the cached value immediately — it means flagging it as no longer
   trustworthy.
4. **Refetch stale entries the next time they're needed** — either eagerly (right away,
   because something is actively displaying that data right now) or lazily (only when
   something next asks for it).

The power of this pattern is that the mutation code only needs to know *what it
affected*, not *which specific screens, components, or callers currently have that data
cached*. The invalidation logic fans out automatically to every consumer of that tag.

## Staleness as a first-class concept

Every piece of cached server state should be thought of as having an implicit
"freshness" state, not just a value:

- **Fresh** — recently fetched or confirmed accurate; safe to display without refetching.
- **Stale** — known or suspected to no longer match the remote source of truth; should be
  refetched before (or shortly after) being displayed again.
- **Absent** — never fetched, or evicted from the cache entirely; must be fetched from
  scratch.

Different data can tolerate different amounts of staleness. A list of product categories
that rarely changes can be treated as fresh for a long time. A live order status during
active fulfillment should be treated as stale almost immediately. When designing a
caching strategy, make an explicit judgment call per type of data about how long "fresh"
should last — don't apply one blanket staleness window to everything.

## Refetch-on-focus / refetch-on-mutation as concepts

Two common triggers for moving cached data from "stale" (or "maybe stale") back to
"fresh" are worth naming as concepts, independent of how any specific tool implements
them:

- **Refetch-on-focus** — when the user returns attention to a view (e.g. switches back
  to a browser tab, reopens a screen, resumes an app from the background), treat that
  as a signal worth checking freshness: has enough time passed, or is this data
  important enough, that it should be silently refreshed now that someone's looking at
  it again? This catches drift caused by changes that happened elsewhere while the user
  wasn't looking.
- **Refetch-on-mutation** — after any mutation completes, treat every tag that mutation
  declared as affected as stale, and trigger a refetch of whichever of those tags is
  currently being displayed. This is the direct application of tag-based invalidation
  described above: the mutation itself is the trigger, not a timer or a focus event.

These two triggers cover the two broad ways data drifts: something changed because of an
action *this session* took (refetch-on-mutation), or something changed because of an
action *some other session or process* took while this session wasn't watching
(refetch-on-focus, or a periodic/background refresh). A complete caching strategy
usually needs both, not just one.
