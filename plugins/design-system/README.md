# design-system

Tier 1 plugin: the visual foundation an application is built on, defined once
before the first component exists. Three of its four skills are framework- and
CSS-library-agnostic — they'd apply equally to a React, Vue, or plain-HTML app —
and the fourth is a thin Tailwind adapter that turns them into a real file.
Depends on nothing.

## Overview

This plugin exists because of a specific, recurring failure: nothing tells a
developer what font size to use, so they pick one. Then the next developer picks
a slightly different one. Six months later the app has `text-[13px]`,
`text-[14px]`, and `text-sm` all meaning "normal text", four blues, three card
shadows, and no way to restyle anything centrally.

The fix is not a style guide nobody reads — it's making the scale the *only*
thing available. Every value a component can use is named and enumerated here;
anything not on the scale is a bug, not a judgement call.

Ordering matters as much as content: these skills run **before** any component
is written (a sibling `architecture-foundations` plugin's `project-kickoff`
skill sequences that). Retrofitting tokens into an app that already has 200
components is a migration; applying them to an empty skeleton is free.

## Layout

```
skills/
├── typography-system/       # ─┐
├── design-tokens/           #  ├─ framework- AND css-library-neutral
├── responsive-breakpoints/  # ─┘
└── tailwind-theme-setup/    # ── adapter: the only skill naming a CSS library
```

Skills are grouped by name prefix, not by folder. Every skill sits directly at
`skills/<name>/SKILL.md` — one level deeper still auto-triggers off its
`description` but loses the `/design-system:<skill>` invocation form. If a second
adapter is ever added (vanilla CSS custom properties, CSS modules, styled
components), give it its own top-level skill name rather than nesting it under a
folder.

## Components

| Skill | Purpose |
|---|---|
| `typography-system` | The pixel type scale (10→48px) with a semantic name per rung, the per-element usage table (page title, form label, table header, KPI value...), the four font weights, and the three font families with fallback chains. The hard rule: sizes are picked from the scale by name, never written as arbitrary values. |
| `design-tokens` | The token catalog for everything that isn't type: color roles, spacing, radius, shadows, and the four interaction states (hover/focus/active/disabled). Focus states are treated as non-optional, since they're a keyboard-accessibility requirement rather than a decorative nicety. |
| `responsive-breakpoints` | Five tiers — mobile, tablet, laptop, desktop, large desktop — for applications whose primary target is enterprise desktop but which must remain usable everywhere else. Deliberately aligned with a sibling `e2e-testing` plugin's test viewports so the CSS and the tests can't disagree about where a layout changes. |
| `tailwind-theme-setup` | The adapter. Writes `app.css` — `@import "tailwindcss"` plus an `@theme` block turning every token above into a real utility class, light/dark variants, and font loading. Ships a copy-paste `assets/app.css`; `references/tailwind-v3.md` gives the equivalent `tailwind.config.ts` shape for projects still on v3. |

## Setup

None for the three neutral skills — they're pure conventions.

`tailwind-theme-setup` needs Tailwind installed. On a project created via a
sibling `architecture-foundations` plugin's `project-kickoff` skill, that already
happened. On an existing project, the skill detects whether Tailwind v4 or v3 is
installed and writes the matching config shape.

## Usage

- "Set up the design system" / "what font sizes should we use" / "define the type scale" → `typography-system`
- "Define our colors/spacing/shadows" / "add a design token" / "what's our border radius" → `design-tokens`
- "What breakpoints should we support" / "make this responsive" / "mobile and tablet layouts" → `responsive-breakpoints`
- "Set up Tailwind" / "write app.css" / "configure the theme" / "add dark mode" → `tailwind-theme-setup`
- "Start a new project" → a sibling `architecture-foundations` plugin's `project-kickoff` skill, which applies all four of these in order before anything else is scaffolded
