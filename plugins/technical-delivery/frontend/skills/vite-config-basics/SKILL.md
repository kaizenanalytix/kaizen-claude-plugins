---
name: vite-config-basics
description: >
  Explains the shape of vite.config.ts — the plugins array, resolve.alias
  path aliases, and the server block — independent of which UI framework
  sits on top of Vite. Use when the user says things like "set up
  vite.config", "configure vite", "add a path alias", or "vite dev server
  port".
---

# Vite Config Basics

Use this skill when creating or editing `vite.config.ts` itself — the shape
of the config object, not which framework-specific plugin belongs in it.
This skill is framework-neutral on purpose: it explains the config file the
same way regardless of which UI framework (or none at all) sits on top of
Vite. Which concrete plugin(s) go in the `plugins` array is a framework
adapter's decision (e.g. a sibling skills group for whichever framework is
in use, such as a `vue` group alongside this plugin's own framework
group), not this skill's — treat that array as a slot this skill describes
but doesn't fill.

## 1. The four things every `vite.config.ts` needs to get right

Read `references/vite-config-shape.md` for a fully annotated example. At a
high level, a `vite.config.ts` is built around:

- **`plugins`** — an array, one entry per build-time concern: the UI
  framework's own Vite plugin (whichever framework is in use), plus any
  other build-time transform plugin the project has decided it needs (see
  `vite-plugins` for how to decide whether something belongs here at all).
  This skill only explains that the array exists and holds plugin
  instances — populating it with a specific framework's plugin is the
  adapter's job.
- **`resolve.alias`** — path aliases, most commonly `@` mapped to `src`.
  Set this up before writing any application code that has deep imports.
- **`server`** — the dev server's basics: `port`, `strictPort`, and `host`.
- **`build`** — build output config (`outDir`, `base`, etc.) — covered by
  `vite-build-output`, not repeated here.

## 2. Set up the `plugins` array

Confirm which UI framework plugin (if any) is already present before adding
one — check `package.json` for an existing `@vitejs/plugin-*` dependency or
ask which framework the project uses. Do not default to any particular
framework's plugin. If the project has no framework yet (e.g. it's a
library or a vanilla project), the `plugins` array can be empty or hold only
non-framework transform plugins.

Keep this array's job narrow: it exists so Vite knows what build-time
transforms to run. Don't add an entry here for something that's just a
runtime npm dependency with no build-time transform — see `vite-plugins`
for that distinction.

## 3. Set up `resolve.alias`

Add a path alias — near-universally `'@': path.resolve(__dirname, './src')`
— so application imports read as `@/shared/utils` instead of accumulating
fragile relative paths like `../../../shared/utils` as files move around.
This is worth doing on essentially every project regardless of framework or
size, because the pain of relative-path drift only grows as the codebase
does.

If the project also uses TypeScript, mirror the same alias in
`tsconfig.json`'s `compilerOptions.paths` so imports resolve identically at
type-check time and at build time — a mismatch here is a common source of
"works at runtime, red squiggly in the editor" confusion.

## 4. Set up the `server` block

For the dev server, set:

- `port` — pin a specific port so the team's local URLs, bookmarks, and any
  `vite-dev-proxy` targets stay consistent across machines.
- `strictPort` — set to `true` if the project wants Vite to fail loudly
  instead of silently picking the next free port when the configured port is
  taken; leave `false` (default) if silently falling back is acceptable.
- `host` — set to expose the dev server on the local network (e.g. for
  testing from a phone or another machine); leave unset for localhost-only.

## 5. When the config needs to vary by mode

If different values are needed depending on `--mode` (dev vs. qa vs.
production), define the config as a function instead of a plain object:
`defineConfig(({ mode }) => ({ ... }))`. This is the same `mode` concept
`vite-env-variables` uses for `.env.[mode]` files — see that skill before
branching config logic on mode, since env files are usually the better place
for values that vary per environment, and config-level branching should stay
reserved for things that aren't just values (e.g. conditionally including a
plugin).

Read `references/vite-config-shape.md` for the complete annotated example,
including the `vite.config.ts` vs. `vite.config.js` choice.

---
_Last reviewed: 2026-08-05_
