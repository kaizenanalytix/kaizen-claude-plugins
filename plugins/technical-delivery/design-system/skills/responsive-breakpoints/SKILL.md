---
name: responsive-breakpoints
description: >
  Defines the five responsive tiers — mobile, tablet, laptop, desktop, large
  desktop — for applications whose primary target is enterprise desktop but
  which must remain usable on every other size, and the layout patterns each
  tier needs. Deliberately aligned with the viewports the e2e suite tests, so
  CSS and tests can't disagree about where a layout changes.
  Framework- and CSS-library-agnostic. Use when the user says things like
  "what breakpoints should we support", "make this responsive", "how should
  this look on mobile", "make it work on phones", "it breaks on a small
  screen", "this table doesn't fit", "fix the layout on tablet", "tablet
  layout", or when starting a new project before any component is written.
---

# Responsive Breakpoints

The application's **primary target is enterprise desktop usage** — dense data
tables, multi-panel layouts, keyboard-driven workflows. It must nonetheless
remain genuinely usable at every tier below that, not merely avoid horizontal
scrolling.

Those two statements are in tension, and the tension is the whole point of this
skill: "desktop-primary" is a statement about where design effort goes and
which layout is the reference, **not** a licence to let smaller sizes degrade
into something technically-rendering but unusable.

## 1. The five tiers

| Tier | From | Notes |
|---|---|---|
| **Mobile** | 0 | The base. Single column, everything stacks. |
| **Tablet** | 768px | The in-between size most layouts get wrong. |
| **Laptop** | 1024px | The first tier where a persistent sidebar fits. |
| **Desktop** | 1280px | **The primary design target.** |
| **Large desktop** | 1536px | Cap content width; don't just stretch. |

**Design mobile-first, in the CSS sense.** Base styles are the mobile layout;
each breakpoint is a min-width that adds capability upward. This is a mechanical
choice, not a contradiction of "desktop-primary" — min-width cascades layer
cleanly, max-width overrides fight each other. Desktop remains the tier that
gets the most design attention; it just isn't the tier written first.

## 2. Don't invent custom breakpoint values

These five values are the standard Tailwind `md`/`lg`/`xl`/`2xl` defaults, kept
deliberately. Two independent reasons:

**They already land on the real device sizes.** 768px is exactly an iPad Mini's
portrait width; 1280px is the standard laptop-class desktop viewport. Custom
values like 767px or 1200px sit *beside* real devices rather than on them,
which is how a layout ends up broken on precisely one popular tablet.

**They match what the e2e suite tests.** A sibling `e2e-testing` plugin's
`playwright-project-structure` skill defines its device matrix in
`references/responsive-breakpoints.md`: Pixel 5, iPhone 13, iPad Mini (768),
and 1280×800 desktop. If the CSS breakpoints and the test viewports disagree,
the tests exercise the layout everywhere *except* at the boundary where it
actually changes — which is the only place responsive bugs live. Keep the two
aligned; if one moves, move the other in the same change. (If that plugin isn't
installed, the tier table above stands on its own.)

## 3. What actually changes at each tier

Breakpoints are only worth having where **behaviour** changes. Adjusting a font
size or letting a flex row reflow is not a breakpoint concern — it happens for
free.

| Pattern | Mobile | Tablet | Laptop+ |
|---|---|---|---|
| Navigation | Drawer / hamburger | Drawer or collapsed rail | Persistent sidebar |
| Data table | Card list, or the 3–4 columns that matter | Horizontal scroll with a pinned first column | Full table |
| Form | Single column | Single column | Two columns where fields pair naturally |
| Modal | Full-screen sheet | Centred, constrained | Centred, constrained |
| Filters | Bottom sheet / drawer | Drawer | Inline toolbar |
| Page padding | 16px | 24px | 32px |

**Data tables are the hard case** in enterprise UI, and the one most often
skipped. A twelve-column table cannot shrink to 390px — it has to become a
different presentation. Decide which it is *per table* (card list vs. horizontal
scroll with a pinned identity column); there is no automatic answer, and
shipping a horizontally-scrolling twelve-column table on a phone is the default
failure mode.

## 4. Touch targets

At the mobile and tablet tiers, interactive elements need a **minimum 44×44px
hit area** — a finger is not a cursor. Padding counts toward this; a 16px icon
with 14px of padding around it qualifies.

This applies to touch-capable tablets too, not only phones. It's the most common
thing missed when a desktop-primary layout is adapted downward: the layout
reflows correctly and every control ends up too small to reliably press.

Related, from a sibling `design-tokens` skill in this plugin: **hover cannot be
the only way to reach anything.** Touch devices have no hover state, so a row
action that only appears on hover is invisible and unreachable on every device
below the laptop tier.

## 5. Large desktop: constrain, don't stretch

Above 1536px, the failure mode inverts — there's too much width rather than too
little. Full-width text becomes unreadable (comfortable line length is roughly
60–80 characters), and controls drift so far apart that related things stop
looking related.

Cap the content container and centre it. Full-bleed is for tables and
dashboards that genuinely use the horizontal space, not for forms and prose.

## 6. Rules to enforce everywhere

- **Use the five named tiers.** Never a one-off media query at an invented
  width — that's the layout equivalent of a hardcoded font size.
- **Add a breakpoint only where behaviour changes.** If nothing but spacing
  reflows, no breakpoint is needed.
- **Every tier is verified, not assumed.** At minimum, check the layout at
  390px, 768px, and 1280px before calling a screen done.
- **Decide the data-table strategy explicitly per table**, at build time — not
  by discovering at review time that it scrolls sideways on a phone.
- **44×44px minimum touch targets** at mobile and tablet.
- **Keep these values in step with the e2e device matrix.** They are one
  decision recorded in two places, and they must not drift.

---
_Last reviewed: 2026-08-11_
