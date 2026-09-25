# Plugin decision guide

## Decision framework, restated

1. Does the task require Vite to transform a file at build time, inject
   code, or change dev-server behavior? If no — it's a regular npm
   dependency, not a plugin.
2. If yes, is there an existing, well-maintained plugin for it, or does it
   need a custom transform? Prefer an existing plugin over hand-rolling a
   transform.
3. Confirm the plugin is actually needed *now* — don't add a plugin
   category speculatively for a need that doesn't exist yet.

## Need → plugin category

| Need | Plugin category | Why it needs a plugin (not just a dependency) |
| --- | --- | --- |
| Import an SVG file and use it as a component | Asset-as-component transform | Vite needs to transform the raw `.svg` file into an importable module at build time — a plain `import` of an `.svg` only gets a URL/raw string by default. |
| Make the app installable / work offline | PWA tooling (manifest + service worker generation) | The manifest and service worker are generated from the build's actual output files, which only a build-time plugin has visibility into. |
| See what's taking up space in the production bundle | Bundle analysis/visualization | The analysis reads the actual bundled output, which only exists after Vite's build step runs. |
| The UI framework's core rendering support (its component-file syntax, single-file components, or whatever authoring format that framework uses) | The framework's own official Vite plugin | Framework source files need a build-time transform into plain JS/DOM operations before they're valid browser code — this is a build-time transform by definition. |
| Call a REST API, format a date, manage global state | Not a plugin — plain npm dependency | None of this changes how Vite processes files; it's ordinary runtime code the app imports and calls. |

## Plugin ordering

Most plugins are order-independent — they hook into different files or
different pipeline stages and don't interfere with each other. Order
starts to matter when two plugins need to touch the *same* file type in a
specific sequence — most commonly, a transform plugin that needs to run
before the framework plugin sees the file (so the framework plugin
receives already-transformed code), or one that needs to run after (so it
sees the framework plugin's output). When adding a plugin whose
documentation mentions ordering relative to the framework plugin, follow
that documentation's placement instructions in the `plugins` array rather
than guessing.
