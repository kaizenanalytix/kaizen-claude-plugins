# Triaging a failure: three outcomes, never a fourth

A failing assertion is not, by itself, evidence of anything. It's a
disagreement between what the test expected and what the app actually did,
and it takes tracing the app's own source code to find out which side is
wrong — or whether either side is wrong at all. This file is the decision
procedure `SKILL.md`'s step 11a points to, plus three worked examples that
all start from the same shape of failure (a failing assertion after a UI
action) and land on three different, correct answers.

## The procedure

1. **Reproduce and read the failure.** The trace, the error output, and
   what the app actually rendered or returned.
2. **Trace it back to the app's source.** Find the component, handler, or
   service responsible for the behavior the test disagreed with.
3. **Look for a stated intent.** A code comment, a doc, or a design
   decision that's unambiguous even without a comment (e.g. a security
   check that's clearly deliberate). Then sort into exactly one bucket:

   - **Intentional, test's assumption was wrong → fix the test.** The app
     is doing what it was built to do; the test modeled the wrong
     expectation. Fix the test, re-run, move on.
   - **Clearly not intentional → flag it as a real finding.** The behavior
     contradicts what the code itself claims, or is an obvious defect
     (broken keyboard access, data loss, a security hole) with no
     plausible reading where it's fine. Report it. Never loosen, delete, or
     skip the assertion just to force a pass — that doesn't resolve the
     disagreement, it deletes the evidence of it.
   - **Genuinely ambiguous → collect it, don't guess.** The code doesn't
     make the intent clear either way. Don't fix the app on a guess, and
     don't adjust the test's expectation on a guess. Hold it for the
     end-of-run report and ask.

"I can't tell, so I'll just make it pass" is not a fourth bucket — it's
outcome 1 and outcome 3 confused with each other, and it's worse than
either: it permanently relabels a possible real bug as "expected," and
every future run of that test then falsely confirms the app is fine. There
is no recovering that signal later without someone remembering to go back
and question a test that's now green.

## Worked example 1 — intentional, the test was wrong

**The failure:** a test presses the browser Back button after logging out
and expects to land on the page the user was viewing right before logout.
Instead, Back does nothing — the user stays on the login page.

**Tracing it:** the app's own router setup contains this:

```typescript
// Both the post-login redirect and logout itself use history.replace,
// never history.push. This is deliberate: replace overwrites the current
// history entry instead of adding a new one, so there is no workspace
// entry left in history for Back to return to after logout. A user who
// steps away from a shared machine and hits Back should land on the login
// page, not back inside the account they just signed out of.
navigate('/login', { replace: true });
```

The comment states the intent directly, and it's a reasonable security
decision, not an accident. The test's assumption — that Back should
re-enter the workspace — is simply wrong about what this app does on
purpose.

**Resolution:** fix the test to expect the login page after Back, not the
pre-logout page. Nothing about the app changes.

## Worked example 2 — the test's technique was wrong, not the app

**The failure:** a test simulates "navigate away and back within the app"
using `page.goto()` twice, and finds that some client-side state (an
in-memory filter selection, a draft form value) has reset in between —
which the test reads as a bug.

**Tracing it:** `page.goto()` is not equivalent to clicking a link or
calling the router's own navigation function — it's a full page reload.
Playwright drives the browser to load the URL from scratch, which tears
down and re-initializes the entire JS runtime, including any in-memory
store the app keeps client-side. The app's own in-app navigation (a
`<Link>`, a router `navigate()` call) never does this — it swaps routed
content without reloading the page, and the in-memory store the test
found "reset" is never touched by that real code path at all.

**Resolution:** fix the test's navigation method, not the app — replace
the second `page.goto()` with a real in-app navigation (click the nav
link, or call the router the way a user's click actually would) and
re-run. The app was never wiping this state during genuine in-app
navigation; the test's simulation of "navigate within the app" just
wasn't actually testing in-app navigation.

## Worked example 3 — a real defect, not obvious until traced

**The failure:** a test opens a dialog from a launcher button, closes the
dialog, and expects keyboard focus to return to the launcher button
afterward. It doesn't — focus lands on `<body>` instead.

**Tracing it:** the launcher component unmounts itself entirely while the
dialog is open (it's conditionally rendered based on the same state that
controls the dialog), rather than staying mounted and merely losing focus.
The UI framework's default focus-restore behavior relies on the
previously-focused element still existing in the DOM when the dialog
closes — an element that's been unmounted can't receive focus back, no
matter how the dialog itself handles focus return. And the launcher
component's own code comment claims the opposite is true:

```typescript
// Focus return to this button after the dialog closes comes for free from
// the framework's dialog primitive - no extra handling needed here.
```

That comment is the app's own stated intent, and the actual behavior
contradicts it — this is exactly the "clearly not intentional" bucket, not
the "ambiguous" one, because the code itself asserts the opposite of what
it does. It's also a genuine accessibility defect: a keyboard user closing
the dialog loses their place entirely.

**Resolution:** neither side gets touched by guessing. Flag it to the user
as a real finding — the launcher's unmount timing breaks focus restoration,
contradicting the component's own comment — and let the user decide how to
fix the app. Don't weaken the test's focus assertion to match the current
(broken) behavior.

---
_Last reviewed: 2026-08-17_
