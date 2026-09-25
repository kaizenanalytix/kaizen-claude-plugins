# Optimistic Updates, In Detail

## What an optimistic update is

An optimistic update changes the locally cached view of server state immediately, in
response to a user action, before the server has confirmed that the corresponding
mutation succeeded. The bet being made is: "this action will almost certainly succeed,
so update the UI now rather than making the user wait for a round trip, and correct
course if it turns out to fail."

This is a UX responsiveness technique layered on top of the normal fetch/mutate/cache
cycle — it does not replace sending the real mutation to the server, and it does not
replace eventually reconciling the local cache with whatever the server actually
returns.

## The general shape of the pattern

1. **User takes an action** that will result in a mutation (e.g. toggling something,
   submitting an edit, deleting an item).
2. **Before the server responds**, apply the equivalent change to the locally cached
   server state directly, so the UI reflects the "as if it already succeeded" outcome
   immediately.
3. **Send the real mutation** to the server as normal.
4. **On success**, reconcile the local cache with whatever the server actually returned
   (which may differ slightly from the optimistic guess — e.g. server-generated fields,
   computed values, timestamps).
5. **On failure**, roll back the optimistic change so the local view returns to
   accurately reflecting the real server state, and surface the failure appropriately.

## The rollback requirement

Every optimistic update must define, explicitly and in advance, what "rollback" means
for that specific mutation. This cannot be treated as a generic, automatic operation,
because different mutations require different rollback strategies:

- **Simple revert** — if the optimistic change was a straightforward flip of a known
  prior value (e.g. toggling a boolean flag from false to true), rollback can just be
  "set it back to what it was before."
- **Re-fetch the authoritative state** — if the optimistic change was more complex or
  derived (e.g. reordering a list, recalculating a total), it may be safer to discard the
  optimistic guess entirely and refetch the real state from the server rather than trying
  to compute an exact local reversal.
- **Surface a visible correction** — if the optimistic change was already visible to the
  user in a way that a silent revert would feel confusing or jarring (e.g. an item
  appeared to be deleted and the list re-arranged around the gap), rollback may need to
  include an explicit error message or undo indicator, not just a silent snap-back.
- **Partial rollback** — some mutations affect multiple pieces of cached state at once
  (e.g. an action that both updates an item and updates a summary/count). Rollback needs
  to account for every piece of state the optimistic update touched, not just the most
  obvious one.

## The risk to flag

The general risk with optimistic updates is applying them without having answered "what
does undoing this specific change actually look like" ahead of time. Skipping this step
leads to one of two failure modes in production:

- The rollback is missing entirely, so a failed mutation leaves the UI permanently
  showing a change that never actually happened server-side — the local cache and the
  remote source of truth are now silently out of sync until the next unrelated refetch
  (if one ever happens).
- The rollback is implemented but incomplete — it reverts the most visible piece of
  state but misses a secondary piece (a count, a derived value, a related cache entry),
  leaving a subtler inconsistency.

Before applying an optimistic update to a mutation, always answer explicitly: "if this
call fails, what exactly needs to change back, and how will the user perceive that
change?" Only apply the optimistic update once that answer is concrete — never leave
rollback as an afterthought to be handled generically "the same way for every mutation."
