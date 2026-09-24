---
name: vite-build-output
description: >
  Explains what vite build produces in dist/, how content-hashed asset
  names enable caching, and how the base config option controls the URL
  prefix for subpath deployments. Use when the user says things like "what
  does vite build produce", "deploy the vite build", "vite build base
  path", or "dist folder".
---

# Vite Build Output

Use this skill when explaining what a production build produces, or when
configuring the build so its output is deployable at the correct URL path.
This is framework-neutral — the shape of `dist/` is the same regardless of
which UI framework produced the source.

## 1. What `vite build` produces

Running `vite build` produces a `dist/` folder (the name is configurable
via `build.outDir`, but `dist/` is the default and by far the most common)
containing:

- **Hashed, content-addressed static assets** — JS, CSS, and other
  referenced assets, each with a content hash in its filename (e.g.
  `index-4f3a9c2b.js`). The filename only changes when the file's content
  changes, which is what lets these be served with aggressive,
  long-lived cache headers safely — a browser (or CDN) that already cached
  `index-4f3a9c2b.js` will never need to re-fetch it, because a change to
  the code produces a different filename entirely.
- **`index.html`** — references the hashed assets by their actual
  (post-hash) filenames, so it's the one file in the output that must
  *not* be cached as aggressively as the hashed assets — it's the thing
  that tells the browser which hashed files to load for the current
  deployed version.

Read `references/build-output-shape.md` for an example `dist/` folder
listing.

## 2. `dist/` is the deployment artifact

`dist/` is what a deployment step picks up and serves as static files (or
uploads to a CDN/object store configured to serve static files). Producing
or wiring the actual CI/CD pipeline that does that upload/deploy step is out
of scope for this skill — a sibling `deployment` plugin owns it: its
`deployment-strategy` skill decides the shape (for a pure browser bundle, that
is normally static hosting on a CDN rather than a container), and its
`pipeline-authoring` skill writes the pipeline. This skill only covers what
the build produces and how to make sure the paths inside it are correct for
wherever it ends up served from.

## 3. `base` — get this right or assets 404

The `base` config option controls the URL prefix that all asset references
in the built `index.html` (and in hashed files that reference other hashed
files) are generated with. It defaults to `/`, which is correct when the
app is served from the domain root (e.g. `https://example.com/`).

If the app is instead served from a subpath (e.g.
`https://example.com/app/`), set `base: '/app/'` in `vite.config.ts` (or
pass `--base=/app/` to the build command). Getting this wrong is a common,
very visible failure mode: the built `index.html` loads fine (it's usually
served with a route/rewrite that doesn't depend on `base`), but every
asset it references 404s, because the browser requests them at the domain
root instead of under `/app/`. Read `references/build-output-shape.md` for
a concrete before/after example.

## 4. Environment-specific builds

Two approaches exist for producing a build that's correct for a specific
target environment (dev/qa/production):

- **Build once per environment**: run `vite build --mode qa`, which loads
  that mode's `.env.qa` (see `vite-env-variables`) and bakes those
  `VITE_*` values into that specific build's output. Produces a distinct
  `dist/` per environment; each is only valid for the environment it was
  built for.
- **Build once, configure at runtime**: produce a single build and inject
  environment-specific values at deploy/serve time (e.g. via a runtime
  config file the app fetches, or values injected into `index.html` at
  deploy time) rather than at build time. Produces one artifact that's
  environment-agnostic until deployed.

Both are technically workable, and this skill used to leave the choice open.
It no longer does: a sibling `deployment` plugin settles it in favour of the
**second** — build once, promote the same artifact, configure at deploy time —
and the reason is a deployment property rather than a build one. If each
environment is built separately, staging never tested the bytes production
runs, the artifact that passed every CI gate is not the artifact deployed, and
rollback has no well-defined target. Baking `VITE_*` values at build time is
what makes an artifact non-promotable.

So prefer a runtime config for anything environment-specific. Read that
plugin's `pipeline-authoring` skill for how the promotion works, and
`deployment-environments` for the config-injection mechanics. The narrow
exception — a per-tenant-domain build where build-time inlining genuinely
can't be avoided — should be stated out loud when taken, not assumed.

---
_Last reviewed: 2026-08-24_
