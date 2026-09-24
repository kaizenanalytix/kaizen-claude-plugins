# Annotated `vite.config.ts`

```ts
import { defineConfig } from 'vite';
import path from 'node:path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    /* framework plugin here */
    // e.g. vue() from '@vitejs/plugin-vue', or the equivalent official
    // Vite plugin for whichever other UI framework this project's
    // adapter installs. Any other build-time transform plugin
    // (SVG-as-component, PWA manifest, bundle analyzer — see
    // vite-plugins) also goes in this array.
  ],

  resolve: {
    alias: {
      // The near-universal alias: lets every file import from '@/...'
      // instead of counting '../' segments back to src/. Keep this in
      // sync with tsconfig.json's compilerOptions.paths if the project
      // uses TypeScript.
      '@': path.resolve(__dirname, './src'),
    },
  },

  server: {
    port: 5173,       // pin a stable port for the whole team
    strictPort: false, // true = fail instead of silently choosing another port
    host: false,       // true (or '0.0.0.0') to expose on the local network
    // proxy: { ... }  — see vite-dev-proxy for forwarding API calls in dev
  },

  // build: { ... } — see vite-build-output for outDir/base/etc.
});
```

## `vite.config.ts` vs. `vite.config.js`

Vite supports both. Prefer `vite.config.ts` when the project is already
TypeScript — it lets the config itself benefit from `defineConfig`'s types
(catching typos in option names at author-time) and keeps the whole project
consistent in one language. A plain JavaScript project can use
`vite.config.js` with the same shape; the options themselves don't change,
only the file extension and the absence of type-checking on the config
file itself.

## Defining config as a function

When the config needs to differ by mode (dev vs. qa vs. production), pass a
function instead of an object literal:

```ts
export default defineConfig(({ mode, command }) => ({
  plugins: [
    /* framework plugin here */
  ],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    port: 5173,
  },
  // conditionally add something only for a build, or only for a
  // particular mode, using `mode` / `command` here.
}));
```

`command` is `'serve'` during `vite dev` and `'build'` during `vite build`;
`mode` is whatever was passed via `--mode` (defaults to `development` for
serve and `production` for build). Reach for this form only when something
structural needs to change (e.g. conditionally including a plugin) — plain
values that vary by environment usually belong in `.env.[mode]` files
instead (see `vite-env-variables`), not branched here.
