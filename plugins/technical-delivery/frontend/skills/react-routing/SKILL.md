---
name: react-routing
description: >
  Sets up lazy-loaded, typed, auth-protected React Router routes with path
  constants instead of string literals. Use when the user says things like
  "add a route", "set up routing", "protect a page", "lazy-load pages", or
  "wire this page into the router".
---

# React Routing

Use this skill when adding navigation, wiring a new page into the router, or
protecting a route behind auth. One sentence of the model this depends on:
`core/router/AppRouter.tsx` is the single app-wide router, composed from
routes contributed by each module, per the three-zone model — see
`frontend-architecture` if the actual question is about overall structure.

## 1. Confirm the routing model

This skill describes **React Router in library mode** — a central `AppRouter.tsx`
holding a route table. That is one of several routing models a React app can
have, and the wrong advice for the others. Check `package.json` first:

- **`react-router-dom`** → library mode. Apply this skill as written.
- **`next`** → Next.js file-based routing. **A route is created by adding a file
  in `app/` or `pages/`, not by editing a route table**, so most of this skill
  doesn't apply: there is no `AppRouter.tsx`, `React.lazy` is unnecessary
  (route-level code splitting is automatic), and auth belongs in middleware or a
  layout rather than a `PrivateRoute` element. The path-constants rule in section
  2 still holds and is still worth applying.
- **`@react-router/dev` + a `routes.ts`** → React Router **framework mode**.
  Routes are declared in that config file, not assembled from JSX `<Route>`
  elements. Section 2's rules on path constants and auth still apply; the
  mechanics of how routes get registered do not — read the project's existing
  `routes.ts` and match it.
- **No router at all** → some apps genuinely don't have one. Don't install a
  router to satisfy a request that was really about something else; ask first.
- **Greenfield** → hand off to `react-project-bootstrap`, which installs
  `react-router-dom`.

Say which model you found before giving routing advice — this is the single
easiest thing to get confidently wrong, because every one of these has `react`
and the word "route" in it.

## 2. Rules to follow

- **Every page is lazy-loaded** via `React.lazy`, so each module gets its own
  code-split chunk instead of bloating the main bundle. A page component
  should never be imported eagerly into `AppRouter.tsx`.
- **Auth is a wrapper component**, `PrivateRoute`, not a scattered `if
  (!user)` check inside individual pages. Wrap the routes that need
  protection in a parent `<Route element={<PrivateRoute />}>`.
- **Route paths are constants**, not string literals repeated across
  `<Link>`s, `navigate()` calls, and the route definition itself. Declare
  them once (e.g. in a module's `types/` or a small `routes.ts`) and import
  them everywhere a path is needed, to avoid string drift when a path
  changes.
- **URL params are typed**: use `useParams<{ id: string }>()` rather than
  destructuring `useParams()` untyped and hoping the shape matches.

Read `references/router-patterns.md` for the concrete pattern to follow.

## 3. Where the route lives

The route for a module's page is declared in `core/router/AppRouter.tsx`, but
the page component itself is lazy-imported from the module
(`modules/<name>/pages/...`). `AppRouter.tsx` should only contain routing
wiring — no business logic, no data fetching.

If scaffolding a brand-new module and its routes at the same time, do the
folder/store wiring first (see `react-module-scaffold`) and add the route as
the final step.

## 4. Suspense boundary

Because pages are lazy-loaded, wrap the route tree (or at minimum each lazy
route) in a `<Suspense fallback={...}>` boundary so navigation doesn't blank
the screen while a chunk loads. This typically lives once in
`core/router/AppRouter.tsx` around the whole `<Routes>` tree, rather than
being repeated per-route.

## 5. Testing implication

Route-level auth and navigation are usually covered by integration or e2e
tests rather than unit tests — see `react-testing` for where routing behavior
(e.g. "an unauthenticated user gets redirected") fits in the test pyramid.

---
_Last reviewed: 2026-08-05_
