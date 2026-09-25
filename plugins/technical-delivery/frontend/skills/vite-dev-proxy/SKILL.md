---
name: vite-dev-proxy
description: >
  Explains Vite's server.proxy option for forwarding local API requests to
  a backend during development, and why it's a dev-only convenience, not a
  substitute for real CORS/gateway configuration. Use when the user says
  things like "proxy API calls in vite", "CORS in local dev", "connect
  frontend to backend locally", or "dev server proxy".
---

# Vite Dev Proxy

Use this skill when the frontend needs to call a backend API during local
development (`vite dev`) and either hasn't configured CORS on the backend
yet, or wants to avoid needing to.

## 1. What `server.proxy` does

`vite.config.ts`'s `server.proxy` option forwards requests matching a path
prefix (e.g. `/api`) to a target server while the Vite dev server is
running. Concretely: the frontend code calls `fetch('/api/products')`, and
Vite — transparently, on the dev server itself — forwards that request to
the configured target (e.g. `http://localhost:8000/api/products`) and
returns the response as if it came from the same origin.

This works regardless of which UI framework issues the request — `fetch`,
axios, or any other HTTP client — since the proxying happens at the dev
server level, below any framework code.

## 2. Why this matters: no CORS needed in local dev

Because the browser only ever sees a same-origin request (to the Vite dev
server's own origin), it never triggers a cross-origin request and never
needs CORS headers from the backend. Without the proxy, calling a backend
running on a different host/port from the frontend's dev server would
require the backend to send the right `Access-Control-Allow-*` headers just
to unblock local development — `server.proxy` sidesteps that entirely for
the dev workflow.

## 3. Set it up

Read `references/proxy-config.md` for the full annotated example. In
short, add a `server.proxy` entry keyed by the path prefix to forward,
pointing at a `target` URL. Read that target from an env variable (see
`vite-env-variables`) rather than hardcoding it, so the target can differ
between developers' machines or between local/dev-container setups without
editing `vite.config.ts` itself.

## 4. This is dev-only — never treat it as a production answer

`server.proxy` only exists inside the Vite dev server process (`vite dev`).
It has no effect on the built output (`vite build` / `dist/`) and does not
run at all in a real deployment. In a deployed environment:

- The frontend and backend are reached through their actual, real URLs, or
- A reverse proxy / API gateway plays the equivalent forwarding role.

Either way, that setup must be configured separately (real CORS headers on
the backend, or a gateway/reverse-proxy rule) — it is a distinct piece of
infrastructure, not something `server.proxy` in `vite.config.ts` produces
or replaces. Never point to `server.proxy` as "handled" when someone asks
how production CORS or routing is configured; that's out of scope for this
skill and needs to be solved at the deployment layer.

## 5. Multiple backends

If the frontend talks to more than one backend service locally (e.g. a
main API and a separate auth service), add one `server.proxy` entry per
path prefix, each with its own `target`. Keep prefixes non-overlapping so
routing stays unambiguous.

---
_Last reviewed: 2026-08-05_
