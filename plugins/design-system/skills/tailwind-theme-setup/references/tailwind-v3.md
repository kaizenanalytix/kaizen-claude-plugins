# Tailwind v3 equivalent

Use this only when `package.json` pins `tailwindcss` to a 3.x version. On v4,
use `assets/app.css` instead — the two are alternatives, never both.

The tokens are identical; only the declaration site moves. In v3, values live
in `tailwind.config.ts` under `theme.extend`, and the theme-dependent ones are
still CSS variables in a stylesheet so `.dark` can swap them.

## 1. The stylesheet — `src/index.css`

Same `:root` / `.dark` variable blocks as `assets/app.css` §1, but with the v3
directives at the top and HSL channel triples instead of full colour values.
The triple-without-a-function format is what lets Tailwind append an opacity
modifier (`bg-primary/50`):

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 0 0% 9%;
    --surface: 0 0% 100%;
    --surface-foreground: 0 0% 9%;
    --muted: 0 0% 96%;
    --muted-foreground: 0 0% 45%;
    --border: 0 0% 90%;
    --primary: 244 75% 51%;
    --primary-foreground: 0 0% 98%;
    --success: 152 60% 36%;
    --danger: 0 72% 51%;
    --warning: 38 92% 50%;
    --info: 199 89% 48%;
    --ring: 244 75% 51%;
    --radius: 6px;
  }

  .dark {
    --background: 0 0% 9%;
    --foreground: 0 0% 98%;
    --surface: 0 0% 15%;
    /* ...remaining dark values, mirroring assets/app.css §1 */
  }

  body {
    @apply bg-background text-foreground font-sans text-body;
  }

  :focus-visible {
    outline: 2px solid hsl(var(--ring));
    outline-offset: 2px;
  }
}
```

## 2. `tailwind.config.ts`

```ts
import type { Config } from 'tailwindcss'

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        background: 'hsl(var(--background) / <alpha-value>)',
        foreground: 'hsl(var(--foreground) / <alpha-value>)',
        surface: {
          DEFAULT: 'hsl(var(--surface) / <alpha-value>)',
          foreground: 'hsl(var(--surface-foreground) / <alpha-value>)',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted) / <alpha-value>)',
          foreground: 'hsl(var(--muted-foreground) / <alpha-value>)',
        },
        border: 'hsl(var(--border) / <alpha-value>)',
        ring: 'hsl(var(--ring) / <alpha-value>)',
        primary: {
          DEFAULT: 'hsl(var(--primary) / <alpha-value>)',
          foreground: 'hsl(var(--primary-foreground) / <alpha-value>)',
        },
        success: 'hsl(var(--success) / <alpha-value>)',
        danger: 'hsl(var(--danger) / <alpha-value>)',
        warning: 'hsl(var(--warning) / <alpha-value>)',
        info: 'hsl(var(--info) / <alpha-value>)',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['Geist Mono', 'Source Code Pro', 'ui-monospace', 'monospace'],
        serif: ['Instrument Serif', 'Source Serif 4', 'Georgia', 'serif'],
      },
      // [size, lineHeight] — the pair is what keeps vertical rhythm consistent
      fontSize: {
        micro: ['10px', '14px'],
        meta: ['11px', '16px'],
        caption: ['12px', '16px'],
        label: ['13px', '18px'],
        body: ['14px', '20px'],
        'body-md': ['15px', '22px'],
        'body-lg': ['16px', '24px'],
        'card-title': ['18px', '24px'],
        'section-title': ['20px', '28px'],
        heading: ['24px', '32px'],
        'page-title': ['28px', '36px'],
        'display-sm': ['32px', '40px'],
        display: ['36px', '44px'],
        'display-lg': ['40px', '48px'],
        'display-xl': ['48px', '56px'],
      },
      borderRadius: {
        sm: 'calc(var(--radius) - 2px)',
        md: 'var(--radius)',
        lg: 'calc(var(--radius) + 2px)',
        xl: 'calc(var(--radius) + 6px)',
      },
      boxShadow: {
        raise: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
        card: '0 1px 3px 0 rgb(0 0 0 / 0.08), 0 1px 2px -1px rgb(0 0 0 / 0.06)',
        dropdown: '0 4px 12px -2px rgb(0 0 0 / 0.12), 0 2px 4px -2px rgb(0 0 0 / 0.06)',
        modal: '0 16px 40px -8px rgb(0 0 0 / 0.18), 0 4px 12px -4px rgb(0 0 0 / 0.08)',
      },
      screens: {
        tablet: '768px',
        laptop: '1024px',
        desktop: '1280px',
        wide: '1536px',
      },
    },
  },
} satisfies Config
```

## Differences that actually bite

- **`extend`, not a bare `theme`.** Replacing `theme` wholesale deletes every
  default — including the `sm:`/`md:` variants vendored shadcn components rely
  on. Always extend.
- **`<alpha-value>` is required** for opacity modifiers to work. Without it,
  `bg-primary/50` silently produces no opacity.
- **`darkMode: 'class'`** is the v3 equivalent of v4's `@custom-variant dark`.
  Omitting it makes `.dark` inert.
- **The `content` globs matter.** v3 has no automatic content detection, so a
  path missing from `content` means those files' classes are stripped from the
  production build — and only from the production build, which is why it's
  usually found after deploy.

## Prefer upgrading

If the project is new, use v4 and `assets/app.css` instead. This file exists
for repos already on v3, not as an equally-good option.

---
_Last reviewed: 2026-08-11_
