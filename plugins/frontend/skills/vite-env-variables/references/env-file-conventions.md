# Env file conventions

## Files Vite loads, and precedence

For a given `mode` (e.g. `development`, `qa`, `production`, or any custom
name passed via `--mode`), Vite loads these files if present, in this
order — later ones override earlier ones for any key defined in both:

1. `.env`
2. `.env.local`
3. `.env.[mode]`
4. `.env.[mode].local`

All of these are loaded from the project root by default. `.env.local` and
`.env.[mode].local` are intended to be listed in `.gitignore` — they hold
machine-specific or locally-overridden values that shouldn't be committed.

## Example: `.env.qa`

```
# .env.qa — loaded only when running with --mode qa

# Exposed to client code as import.meta.env.VITE_API_BASE_URL
VITE_API_BASE_URL=https://api.qa.example.com

# Exposed to client code as import.meta.env.VITE_FEATURE_FLAGS_URL
VITE_FEATURE_FLAGS_URL=https://flags.qa.example.com

# NOT exposed to client code (no VITE_ prefix) — available only to
# vite.config.ts at config-evaluation time, e.g. for choosing a proxy
# target or a build option based on environment.
INTERNAL_BUILD_LABEL=qa-build
```

Running `vite build --mode qa` (or `vite dev --mode qa`) loads this file
(layered on top of `.env` and `.env.local`) and makes `VITE_API_BASE_URL`
and `VITE_FEATURE_FLAGS_URL` available in client code as
`import.meta.env.VITE_API_BASE_URL` / `import.meta.env.VITE_FEATURE_FLAGS_URL`.
`INTERNAL_BUILD_LABEL` is available inside `vite.config.ts` (via
`loadEnv` or the config function's `mode`/`env` handling) but never reaches
the browser bundle.

## Example: `vite-env.d.ts`

Place this at the `src/` root (or project root) so TypeScript knows the
shape of custom env variables:

```ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_FEATURE_FLAGS_URL: string;
  // add every custom VITE_* variable the project defines
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
```

Without this, `import.meta.env.VITE_API_BASE_URL` still works at runtime
(Vite performs the substitution regardless of TypeScript types), but the
editor and type-checker won't catch a typo'd variable name or know its
type — this file is what closes that gap.
