# Annotated `server.proxy` config

```ts
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  return {
    // ...plugins, resolve, etc. — see vite-config-basics

    server: {
      proxy: {
        // Any request starting with '/api' gets forwarded to the target.
        // e.g. fetch('/api/products') -> `${VITE_API_PROXY_TARGET}/api/products`
        '/api': {
          // Read the backend's local URL from an env variable rather than
          // hardcoding it — see vite-env-variables for the .env convention.
          // Note: values consumed only inside vite.config.ts don't need
          // the VITE_ prefix, but using it here keeps the same variable
          // usable from client code too, if ever needed.
          target: env.VITE_API_PROXY_TARGET ?? 'http://localhost:8000',

          // changeOrigin: rewrites the Host header on the forwarded
          // request to match the target, instead of leaving it as the
          // Vite dev server's own host. Needed whenever the target
          // backend checks/validates the Host header (many frameworks'
          // dev servers do, as a basic anti-DNS-rebinding measure).
          changeOrigin: true,

          // rewrite: strips or rewrites the path before forwarding, when
          // the backend doesn't itself expect the '/api' prefix. Only
          // needed if the backend's real routes don't include that
          // prefix — if they do (e.g. backend routes are already
          // '/api/products'), omit rewrite entirely.
          // rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
  };
});
```

## `changeOrigin` — when it's needed

Needed whenever the target server validates the incoming `Host` header
against its own expected host (common in dev servers and some frameworks'
security defaults). Without it, the proxied request arrives with the Vite
dev server's `Host` header (e.g. `localhost:5173`) instead of the target's
(e.g. `localhost:8000`), which some backends reject. Safe to leave on by
default for local development.

## `rewrite` — when it's needed

Needed only when the prefix used to match requests on the frontend side
(`/api`) is not actually part of the backend's real route paths. For
example, if the frontend calls `/api/products` but the backend's actual
route is just `/products` (no `/api` prefix), add:

```ts
rewrite: (path) => path.replace(/^\/api/, ''),
```

If the backend's routes already include the same prefix used to match
(e.g. backend really does serve `/api/products`), omit `rewrite` — forward
the path unchanged.
