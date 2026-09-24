---
name: design-tokens
description: >
  Defines the centralized token catalog for everything visual that isn't type
  — color roles, spacing, border radius, shadows, and the four interaction
  states (hover, focus, active, disabled) — so components consume named tokens
  instead of inventing hex codes, pixel paddings, and one-off shadows.
  Framework- and CSS-library-agnostic. Use when the user says things like
  "define our colors", "add a design token", "what border radius should this
  be", "our spacing is inconsistent", "the spacing looks off", "this doesn't
  match the rest of the app", "make it look better", "set up dark mode
  colors", "hover and focus states", "this isn't keyboard accessible", "the
  contrast is too low", or when starting a new project before any component is
  written.
---

# Design Tokens

Every visual value a component uses — color, spacing, radius, shadow, and how
it looks when hovered, focused, pressed, or disabled — comes from a named token
defined in one place. Components consume tokens. Components never invent
values.

This skill names tokens neutrally and says nothing about how they're declared.
A sibling `tailwind-theme-setup` skill in this plugin turns them into real CSS.
Type is covered separately by a sibling `typography-system` skill; the two are
designed to be applied together.

## 1. What a token actually buys you

A token is not a naming convention for its own sake — it's the difference
between "make the primary colour slightly darker" being a one-line change and
being a two-day audit.

The test for whether a system is real: **can one edit change every instance of
a thing?** If a component hardcodes `#2563eb`, the answer is no, and the fact
that it *looks* consistent today is irrelevant — it's consistent by coincidence,
and it will drift the first time someone eyeballs a colour from a screenshot.

That's why the rule below is absolute rather than aspirational: the moment one
component invents its own value, the system stops being able to make that
promise for that value everywhere.

## 2. Color

Tokens are named by **role**, not by appearance. `primary`, not `blue-600`.
A role survives a rebrand and works in both light and dark; a colour name
doesn't — `text-blue-600` in a dark theme is a bug waiting to happen, and
`bg-white` is simply wrong the moment dark mode ships.

**Semantic roles** — the ones most components actually use:

| Token | Role |
|---|---|
| `background` | The page's base surface |
| `foreground` | Default text on `background` |
| `surface` | Raised surfaces: cards, panels, popovers |
| `surface-foreground` | Text on `surface` |
| `muted` | Recessed backgrounds: table stripes, disabled fields |
| `muted-foreground` | Secondary text — captions, helper text, placeholders |
| `border` | Dividers, input outlines, table rules |
| `ring` | Focus ring — see §6 |

**Status roles** — meaning, not decoration. Each needs a foreground that meets
contrast on its own background, and a subtle variant for filled backgrounds
(alert bodies, badges) where the full-strength colour would be overwhelming:

| Token | Meaning |
|---|---|
| `primary` | Primary action, brand emphasis |
| `secondary` | Secondary action, lower-emphasis UI |
| `success` | Completed, healthy, approved |
| `danger` | Destructive action, error, failure |
| `warning` | Needs attention, degraded, pending |
| `info` | Neutral informational callout |

Rules:

- **Never a raw hex in a component.** A hex code appears in the theme file and
  nowhere else.
- **Never a bare colour-family utility** (`text-blue-600`, `bg-gray-100`) where
  a role exists. Roles are what make dark mode a token swap instead of a rewrite.
- **Every pair is checked for contrast** — body text at 4.5:1, large text and
  UI boundaries at 3:1 (WCAG AA). Check in both themes; a pair that passes in
  light frequently fails in dark.
- **Status colour is never the only signal.** Red-green colour blindness is
  ~8% of men — pair status colour with an icon or text label, always.

## 3. Spacing

One scale, 4px-based, used for padding, margin, and gap alike:

```
0    2    4    8    12    16    20    24    32    40    48    64    80    96
```

Most enterprise UI density lives between 8 and 24. Reach outside that range
deliberately, not by accident.

Never write a spacing value that isn't on the scale. `13px` of padding is the
same category of mistake as a `13px` font size that isn't on the type scale —
it looks fine alone and destroys rhythm in aggregate.

## 4. Radius

Four rungs plus full:

| Token | Value | Use |
|---|---|---|
| `radius-sm` | 4px | Badges, tags, small inline controls |
| `radius-md` | 6px | **Default — buttons, inputs, selects** |
| `radius-lg` | 8px | Cards, panels, popovers |
| `radius-xl` | 12px | Modals, large containers |
| `radius-full` | 9999px | Pills, avatars, circular icon buttons |

Derive these from a single base value so the whole product's roundness can be
tuned with one edit rather than five.

## 5. Shadows

Shadow communicates **elevation** — how far off the page something sits — so
name it by what's raised, not by how blurry it is:

| Token | Elevation |
|---|---|
| `shadow-raise` | Subtle lift: table rows, hovered list items |
| `shadow-card` | Resting cards and panels |
| `shadow-dropdown` | Menus, popovers, comboboxes |
| `shadow-modal` | Dialogs, drawers — the top layer |

None of these is called `shadow-sm`/`shadow-lg`. That's deliberate: those names
already exist in most CSS frameworks, and shadowing a built-in name means a
component can use the framework's version by accident and look almost — but not
quite — right.

Two cautions. Shadows tuned for light mode look muddy on dark surfaces; dark
themes generally need a *lighter surface colour* to convey elevation rather
than a stronger shadow. And elevation must agree with `z-index` — a modal that
sits above a dropdown in stacking order but below it in shadow weight reads as
broken even when nobody can say why.

## 6. Interaction states

Four states, defined once as tokens and applied uniformly. These are part of
the design system, not per-component polish — an app where each button decides
its own hover treatment is exactly as inconsistent as one where each picks its
own font size.

| State | Rule |
|---|---|
| **hover** | A consistent shift toward the surface's contrast direction. Pointer devices only — never make information reachable *only* on hover, since touch has no hover. |
| **focus** | A visible ring using the `ring` token, on **every** interactive element. |
| **active** | A brief pressed treatment, distinct from hover, so a click feels acknowledged. |
| **disabled** | Reduced emphasis plus a non-interactive cursor. Must still be legible — a disabled control the user can't read is a dead end, since they can't tell what they're being denied. |

**Focus states are non-negotiable.** They are how keyboard and screen-reader
users know where they are; removing the outline without replacing it makes an
app unusable without a mouse and is a straightforward accessibility failure.
`outline: none` with no replacement ring is never acceptable — if the default
ring is ugly, replace it with a better one, don't delete it.

Prefer focus treatments that appear for keyboard navigation but not on mouse
click (the `:focus-visible` behaviour) — that's what makes a strong, obvious
ring acceptable to designers who object to seeing it on every click.

## 7. Rules to enforce everywhere

- **Tokens are defined in exactly one place** — the theme file a sibling
  `tailwind-theme-setup` skill writes. A component never defines a token.
- **No raw values in components**: no hex colours, no off-scale spacing, no
  hand-written `box-shadow`, no arbitrary radius.
- **Name by role, never by appearance.** `danger`, not `red`. `surface`, not
  `white`.
- **Every interactive element has all four states.** A control with a hover but
  no focus ring is incomplete, not merely unpolished.
- **Adding a token is a deliberate decision**, made once and centrally. When a
  design calls for a value the catalog lacks, either map it to the nearest
  existing token or add it to the catalog — never satisfy it locally in one
  component.
- Contrast is verified in **both** light and dark themes, not just the one
  being worked on.

The scannable one-page version of every token above is in
`references/token-cheatsheet.md`.

---
_Last reviewed: 2026-08-11_
