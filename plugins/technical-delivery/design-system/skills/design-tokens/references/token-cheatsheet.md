# Design token cheat sheet

One page, no prose. For the reasoning behind any of it, see `SKILL.md`.

## Color — semantic roles

```
background            page base surface
foreground            default text on background
surface               cards, panels, popovers
surface-foreground    text on surface
muted                 table stripes, disabled fields
muted-foreground      captions, helper text, placeholders
border                dividers, input outlines, table rules
ring                  focus ring
```

## Color — status roles

```
primary      primary action, brand emphasis
secondary    secondary action, lower-emphasis UI
success      completed, healthy, approved
danger       destructive, error, failure
warning      needs attention, degraded, pending
info         neutral informational callout
```

Each status role needs: a base, a readable foreground, and a subtle variant for
filled backgrounds (alert bodies, badges).

## Spacing — 4px scale

```
0   2   4   8   12   16   20   24   32   40   48   64   80   96
            ^^^^^^^^^^^^^^^^^^^^^  most enterprise UI lives here
```

## Radius

```
radius-sm     4px     badges, tags, small inline controls
radius-md     6px     *** DEFAULT — buttons, inputs, selects ***
radius-lg     8px     cards, panels, popovers
radius-xl    12px     modals, large containers
radius-full  9999px   pills, avatars, circular icon buttons
```

## Shadows — by elevation

```
shadow-raise      table rows, hovered list items
shadow-card       resting cards and panels
shadow-dropdown   menus, popovers, comboboxes
shadow-modal      dialogs, drawers — top layer
```

Shadow weight must agree with `z-index` order. Dark themes convey elevation
with a lighter surface, not a heavier shadow.

## Interaction states — all four, every interactive element

```
hover      shift toward the surface's contrast direction; pointer only
focus      visible ring via the `ring` token — NON-NEGOTIABLE
active     brief pressed treatment, distinct from hover
disabled   reduced emphasis + non-interactive cursor, still legible
```

`outline: none` without a replacement ring is an accessibility failure.
Prefer `:focus-visible` so the ring shows for keyboard, not mouse clicks.

## Contrast targets (WCAG AA)

```
4.5:1   body text
3:1     large text, UI boundaries, icons
```

Verify in **both** light and dark. Never let colour be the only signal — pair
status colour with an icon or label.

## The one rule

No hex codes, no off-scale spacing, no hand-written `box-shadow`, no arbitrary
radius in a component. Tokens live in the theme file and nowhere else.

---
_Last reviewed: 2026-08-11_
