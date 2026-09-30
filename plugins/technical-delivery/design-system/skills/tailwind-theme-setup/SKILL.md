---
name: tailwind-theme-setup
description: >
  Writes the application's real theme file — an app.css whose @theme block
  turns the design tokens, type scale, and breakpoints into actual Tailwind
  utility classes, with light/dark variants and font loading. The concrete
  Tailwind adapter for this plugin's three framework-neutral skills. Use when
  the user says things like "set up Tailwind", "write app.css", "configure the
  theme", "add dark mode", "where do our design tokens live", or after the
  neutral design skills have been applied on a new project.
---

# Tailwind Theme Setup

This is the adapter: the only skill in this plugin that names a CSS library. A
sibling `design-tokens`, `typography-system`, and `responsive-breakpoints` skill
decide *what* the values are; this skill decides *where they live* and turns
them into utility classes a component can actually type.

One sentence of the model this depends on: every visual value is defined once,
centrally, and consumed by name — so this skill's real output is not a
stylesheet but a **single edit point** for the app's entire appearance.

## 1. Detect the Tailwind version first

The two versions configure themselves in completely different places, and
writing the wrong one produces a file that is silently ignored:

- **v4** — CSS-first. Everything lives in `app.css` inside `@theme`. No
  `tailwind.config.ts` is needed. **This is the default and the rest of this
  skill assumes it.**
- **v3** — JS config. Tokens live in `tailwind.config.ts` under `theme.extend`.
  See `references/tailwind-v3.md`, which carries the same tokens in that shape.

Check `package.json` for the `tailwindcss` version. If Tailwind isn't installed
at all, install it before continuing — for a Vite project that's `tailwindcss`
plus `@tailwindcss/vite`, with the plugin added to `vite.config.ts`.

## 2. Write `app.css`

Copy `assets/app.css`. It is the complete, working theme — not a fragment —
and is organized in three parts:

1. **Theme-dependent variables** in `:root` and `.dark`. Plain CSS variables,
   because they change per theme.
2. **`@theme inline`**, mapping those variables onto Tailwind's namespaces so
   they generate real utilities.
3. **`@layer base`**, holding the handful of global element defaults.

Then import it once, at the application's entry point — `main.tsx` for a Vite
app. Once, at the top level; never per-component.

### Why the `:root` + `@theme inline` split

This is the part that's easy to get wrong. `@theme` values are **static** —
declaring `--color-surface: white` there bakes `white` into every generated
utility, and no amount of `.dark` overriding will change it.

`@theme inline` instead emits utilities that reference `var(--surface)`, so
redefining `--surface` under `.dark` swaps every one of them at runtime. Any
token that differs between light and dark must go through this two-step. Tokens
that don't vary — the type scale, radii, breakpoints — can be declared directly
in `@theme`.

## 3. What each namespace generates

`@theme` namespaces are not arbitrary names; each one feeds a specific family
of utilities:

| Declared | Generates |
|---|---|
| `--color-surface` | `bg-surface`, `text-surface`, `border-surface` |
| `--text-body` (+ `--text-body--line-height`) | `text-body`, with its line-height attached |
| `--font-sans` | `font-sans` |
| `--radius-lg` | `rounded-lg` |
| `--shadow-card` | `shadow-card` |
| `--breakpoint-desktop` | the `desktop:` variant |

A token that doesn't sit in the right namespace generates nothing at all and
fails silently — no error, just a class that does nothing. If a new utility
isn't working, this is the first thing to check.

## 4. Semantic names sit alongside the defaults, not instead of them

Tailwind's built-in `text-sm`, `md:`, `shadow-lg` and so on remain available.
They are **not** cleared, even though the tokens are meant to replace them.

The reason is concrete: vendored shadcn/ui components — the ones a sibling
`frontend` plugin's `react-component-library` skill copies into
`shared/components/ui/` — use `sm:` and `text-sm` internally. Clearing those
namespaces (`--breakpoint-*: initial`) would break every one of them, in ways
that don't surface until a specific viewport.

So the rule is enforced by convention rather than by deletion:

- **Application code uses the semantic names.** `text-body`, not `text-sm`.
  `desktop:`, not `xl:`.
- **Vendored `shared/components/ui/` files keep whatever they shipped with.**
  Don't rewrite them to semantic names; they get replaced wholesale on upgrade.

## 5. Reconciling with `shadcn init`

`npx shadcn@latest init` writes its own colour variables and base colour into
the CSS file, which will overwrite or duplicate the theme written here. Order
and ownership matter:

- **Run `shadcn init` first, then apply this theme** on a project where both
  are wanted — that way this file is authoritative and its tokens win.
- If shadcn was initialized afterward and has clobbered things, keep this
  file's token block and re-point shadcn's names (`--card`, `--popover`,
  `--accent`, `--destructive`) at the tokens here rather than keeping its
  `slate` defaults. `--destructive` maps to `--danger`; `--card` to `--surface`.
- Never maintain two parallel colour systems. One set of values, one file.

## 6. Verify it actually works

The failure mode is a theme that looks correct in the file and does nothing in
the browser. Check for real, not by reading — but **ask before starting a dev
server or a build**. A sibling `architecture-foundations` plugin's
`working-agreement` skill covers why verification is batched and asked for; the
rule stands on its own here if that plugin isn't installed.

1. Render an element with `text-page-title` and confirm it computes to **28px**
   in devtools — not that the class is present, that the size is right.
2. Toggle `.dark` on `<html>` and confirm backgrounds and text swap. If they
   don't, the token is in `@theme` where it should be in `:root` + `@theme
   inline` (§2).
3. Tab through a form and confirm a visible focus ring on every control.
4. Resize to 767px and 768px and confirm the `tablet:` variant switches.
5. Confirm all three font families load — mono in particular, since it's easy
   to miss a missing webfont when the fallback is also monospace.

## 7. Rules to enforce everywhere

- **One theme file.** No second source of tokens, no component-level `:root`
  overrides, no parallel shadcn palette.
- **No arbitrary values in components** — not `text-[13px]`, not `p-[13px]`,
  not `bg-[#2563eb]`. If a value is needed often enough to type, it belongs in
  the theme.
- **Every token that varies by theme goes through `:root` + `@theme inline`.**
  Static-only tokens in bare `@theme` are a dark-mode bug waiting to happen.
- **Changing a brand colour means editing `:root` and `.dark`** — if it means
  editing a component, the system has already been bypassed somewhere.
- Keep the semantic breakpoint aliases in step with a sibling `e2e-testing`
  plugin's device matrix; they describe the same boundaries.

---
_Last reviewed: 2026-08-11_
