# Example `dist/` folder

```
dist/
  index.html
  assets/
    index-4f3a9c2b.js
    index-7d1e6a90.css
    vendor-9a12ff3e.js
    logo-3c8b21aa.svg
```

- `index.html` — the entry point; references the hashed files above by
  their exact built names (Vite rewrites these references automatically
  during the build, so the source `index.html` never hardcodes a hash).
- `assets/index-4f3a9c2b.js` / `assets/index-7d1e6a90.css` — the app's own
  hashed JS/CSS bundle(s).
- `assets/vendor-9a12ff3e.js` — a separate vendor/dependency chunk (Vite
  and Rollup split some dependencies into their own chunk automatically;
  exact splitting behavior depends on the project's build config).
- `assets/logo-3c8b21aa.svg` — a static asset that was imported/referenced
  from source and got copied into the build with its own content hash.

Every filename containing a hash changes only when that file's content
changes — that's what makes it safe to serve these with a far-future cache
header (e.g. `Cache-Control: max-age=31536000, immutable`) while serving
`index.html` itself with a short or no-cache header, so browsers always
fetch the current `index.html` and then trust the (correctly named) hashed
files it points to.

## Setting `base` for a subpath deployment

If the app is deployed at `https://example.com/app/` rather than the
domain root:

```ts
// vite.config.ts
export default defineConfig({
  base: '/app/',
  // ...
});
```

Without this, the built `index.html` would reference assets as
`/assets/index-4f3a9c2b.js` (root-relative), which 404s when the actual
app is served under `/app/`. With `base: '/app/'` set, the same reference
becomes `/app/assets/index-4f3a9c2b.js`, matching where the files are
actually served from.

This can also be passed at build time without touching the config file:

```
vite build --base=/app/
```

Useful when the deployment path is only known at deploy time (e.g. varies
per environment) rather than being fixed for the project.

## Environment-specific builds

**Approach A — build once per environment:**

```
vite build --mode qa
```

Loads `.env.qa` (layered over `.env` / `.env.local`, per
`vite-env-variables`), so any `VITE_*` value referenced in the source code
gets baked into that build's output as a literal value. Running this again
with `--mode production` produces a different `dist/` with production's
values baked in instead. Each `dist/` is only valid for the environment it
was built for — deploying a `qa`-built `dist/` to production would ship
QA's baked-in config.

**Approach B — build once, configure at runtime:**

Produce a single `dist/` (typically via a plain `vite build` with no
mode-specific env baked in for the values that need to vary), and have the
app fetch or read its environment-specific config at runtime instead —
e.g. a small `config.json` fetched on load, or values injected into
`index.html` by the deploy step for that environment. The same built
`dist/` artifact is then promoted across environments unchanged, with only
the runtime config differing per place it's deployed.

Build-once-per-environment is simpler to reason about per build but means
re-building for every target; build-once-configure-at-runtime means one
artifact is promoted everywhere but requires the app to support
fetching/reading runtime config.

A sibling `deployment` plugin settles this in favour of the second —
build once, promote the same artifact, configure at deploy time — because
separately-built environments mean staging never tested the bytes production
runs, and rollback has no well-defined target. See `SKILL.md` §4 and that
plugin's `pipeline-authoring` skill.
