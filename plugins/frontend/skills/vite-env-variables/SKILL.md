---
name: vite-env-variables
description: >
  Explains Vite's .env file convention, mode-based loading, the VITE_
  prefix rule for client exposure, and typing import.meta.env for
  TypeScript. Use when the user says things like "environment variables
  in vite", ".env files", "config for dev/qa/prod", or "import.meta.env".
---

# Vite Environment Variables

Use this skill when adding, reading, or typing environment configuration in
a Vite project — regardless of which UI framework is in use, since Vite
loads and exposes env files identically either way.

## 1. The env file convention

Vite loads env files based on the `--mode` flag passed to its CLI, not just
`NODE_ENV`. For a given mode, Vite loads (later files override earlier
ones):

1. `.env` — loaded in every mode.
2. `.env.local` — loaded in every mode, meant to be gitignored (local
   overrides, never committed).
3. `.env.[mode]` — e.g. `.env.development`, `.env.qa`, `.env.production` —
   loaded only when running in that mode.
4. `.env.[mode].local` — mode-specific local override, also gitignored.

The mode comes from `vite dev` (defaults to `development`), `vite build`
(defaults to `production`), or an explicit `--mode <name>` flag — so a
project can define as many named modes as it has real environments (e.g.
`qa`, `staging`) beyond just dev/prod. Read
`references/env-file-conventions.md` for the full precedence table and an
example `.env.qa`.

## 2. The `VITE_` prefix rule — and why it exists

Only variables whose name starts with `VITE_` are exposed to client code,
via `import.meta.env.VITE_*`. Every other variable in an env file is loaded
for Vite's own config-time use (e.g. inside `vite.config.ts`) but is
filtered out of what actually reaches the browser bundle.

**This is a safety boundary, not a naming convention to follow loosely.**
State this rule plainly whenever env variables come up:

- A `VITE_`-prefixed variable gets bundled directly into the client-side
  JavaScript that ships to the browser. Anyone who opens dev tools (or just
  views the built `dist/` output) can read its value.
- Never put a secret, API key, database credential, or anything
  security-sensitive in a `VITE_` variable, no matter how convenient it
  seems in the moment.
- If a value must stay server-only, it does not belong in the frontend's
  env files at all — it belongs in the backend's own config/secrets
  handling. The frontend should reach that value only indirectly, e.g. by
  calling a backend endpoint that uses the secret server-side.

## 3. Reading env variables in code

Access loaded variables via `import.meta.env.VITE_SOMETHING` — never via
Node's `process.env` (Vite doesn't populate that in client code). A handful
of built-in variables are always available without a prefix, such as
`import.meta.env.MODE` and `import.meta.env.DEV` / `import.meta.env.PROD`.

## 4. Type it for TypeScript

If the project uses TypeScript, add a `vite-env.d.ts` (or `env.d.ts`) at
the `src/` root declaring the shape of `ImportMetaEnv` so custom `VITE_*`
variables get autocomplete and type errors instead of resolving to `any` /
`string | undefined` silently. Read
`references/env-file-conventions.md` for the exact declaration block to
use — it's a small, copy-once addition per project.

## 5. Where this connects to other skills

- `vite-config-basics` covers defining `vite.config.ts` as a function of
  `mode` when the config itself (not just a value) needs to differ per
  environment.
- `vite-dev-proxy` uses a `VITE_`-prefixed variable as the recommended way
  to configure the local backend target per environment.
- `vite-build-output` covers building once per environment with
  `vite build --mode qa` (consuming that mode's `.env.qa`) as one of two
  valid deployment strategies.

---
_Last reviewed: 2026-08-05_
