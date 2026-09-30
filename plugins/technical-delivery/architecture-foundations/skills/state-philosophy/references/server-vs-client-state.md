# Server State vs Client State, In Detail

## Why the distinction matters

Treating server state and client state as the same kind of thing is the single most
common source of subtle state bugs: stale UI, data that "reverts" after a refresh,
duplicated sources of truth, and state that's out of sync across parts of the same
screen. The two kinds of state have fundamentally different lifecycles and need
fundamentally different storage strategies:

- Server state's lifecycle is driven by the remote system — it changes when the remote
  data changes, whether or not the app is even looking at it right now.
- Client state's lifecycle is driven entirely by the user's current interaction — it
  changes only when the user (or the app's own logic) changes it directly.

Storing them the same way — e.g. in one flat, generic store with no distinction — throws
away the fact that server state needs staleness tracking, deduplication of concurrent
fetches, and invalidation, none of which client state needs at all.

## Decision table

Use this table as a template for classifying new pieces of state. For each candidate,
ask "where does this data ultimately come from, and can something outside this session
change it without the user doing anything in this session?"

| Example state | Bucket | Why |
|---|---|---|
| The list of products returned from an API call | Server state | Comes from a remote system; can change if another user/process updates a product; needs to be refetched to detect that change. |
| Which row in a table is currently expanded | Client state | Exists only for this session's interaction; nothing remote defines "which row is expanded." |
| The currently logged-in user's profile fetched from the backend | Server state | Sourced from a remote system; the profile can change server-side (e.g. an admin edits it) independent of this session. |
| The text currently typed into a search box before submitting | Client state | A draft that belongs entirely to this interaction; has no remote counterpart until submitted. |
| The set of filters currently applied to a list view | Client state | The *choice* of filter is local to this session, even though applying it triggers a fetch of (server-state) data that matches it. |
| The result of applying those filters (the filtered list itself) | Server state | It's fetched from — or derived directly from — a remote system in response to the local filter choice. |
| Whether a modal is open | Client state | Pure UI/interaction state with no remote source of truth. |
| A shopping cart persisted server-side for a logged-in user | Server state | Even though it feels like "the user's own data," the system of record is remote — another device or session could see a different cart if this one goes stale. |
| A shopping cart that only exists client-side for an anonymous guest session | Client state | No remote system owns it; it's entirely local until/unless it gets synced to the server. |
| A multi-step form's current step and field values before final submit | Client state | A draft, owned by this interaction, until it's actually submitted to the server. |
| The confirmation/result returned after that form is submitted | Server state | Once submitted, the authoritative record now lives server-side; the local view of it is a cached copy. |

## The recurring trap: "it looks like a simple value, so I'll just store it generically"

The most common misclassification is treating fetched data as client state because, at
the point of use, it's "just a value" (a list, an object, a boolean) with no obvious
remote fingerprint attached. The test is not "does this look like a simple value" — it's
"where did this value come from, and can it change out from under me." A list of
products is exactly as "simple" a value as a boolean modal-open flag, but only one of
them needs a staleness/invalidation strategy.

When in doubt, trace the value back to its origin: if there's a fetch call anywhere in
its history, treat it as server state and let the appropriate data-fetching layer own its
caching — don't hand-copy the result into a separate, general-purpose store.
