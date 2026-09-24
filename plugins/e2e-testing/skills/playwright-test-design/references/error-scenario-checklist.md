# Error-scenario checklist

Never design a plan that is happy-path-only. For each critical workflow,
check whether each of these applies, and if it does, add a scenario for it.

| Scenario | Why it matters |
|---|---|
| Invalid input | The most common real-world failure — confirms validation actually rejects bad data instead of the backend silently accepting or crashing on it. |
| Empty required fields | Distinct from "invalid" — many forms validate format but not presence; this catches a whole separate bug class. |
| HTTP 400 (bad request) | Confirms the client surfaces a malformed-request error usefully instead of a generic failure. |
| HTTP 401 (unauthenticated) | Confirms an unauthenticated caller is actually blocked, not just that the "happy" authenticated path works. |
| HTTP 403 (forbidden) | Confirms role/permission checks are enforced server-side, not just hidden in the UI (a hidden button is not a security control). |
| HTTP 404 (not found) | Confirms the app handles a reference to a since-deleted or nonexistent resource gracefully. |
| HTTP 409 (conflict) | Catches concurrent-edit and duplicate-resource bugs that only show up under real contention. |
| HTTP 500 (server error) | Confirms the frontend degrades to a real error state instead of hanging or showing a blank screen. |
| Network failure | Real users lose connectivity mid-flow; confirms the app recovers or fails visibly instead of silently. |
| Slow response | Confirms loading states actually appear and the UI doesn't double-submit or appear frozen while waiting. |
| Duplicate submission | Confirms a double-click or resubmit doesn't create two records or double-charge. |
| Expired authentication | Confirms a session that expires mid-workflow re-prompts or redirects instead of silently failing every subsequent call. |
| Missing permissions | Distinct from 403 on a single call — confirms a role change mid-session (or a role without a given permission at all) is handled consistently across the whole flow, not just one endpoint. |

Map each applicable row to a Playwright implementation pattern in the
`playwright-test-implementation` skill's `references/error-path-patterns.md`
once these scenarios move from design to code.

---
_Last reviewed: 2026-08-07_
