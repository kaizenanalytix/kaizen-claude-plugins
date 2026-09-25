---
name: typography-system
description: >
  Defines the application's typography as a closed, explicitly-enumerated
  pixel scale with a semantic name for every rung, plus font families,
  weights, and a per-element usage table — so font sizes are chosen from a
  named scale rather than invented per component. Framework- and
  CSS-library-agnostic. Use when the user says things like "set up the
  typography", "what font size should this be", "define the type scale",
  "our text sizes are inconsistent", "the text looks too big/small", "this
  heading doesn't match the others", "which font should we use", "change the
  font", or when starting a new project before any component is written.
---

# Typography System

Typography is standardized across the whole application. Font sizes are
**explicitly defined in pixels** and picked from the scale below by their
semantic name. Developers do not choose font sizes ad hoc — that is the entire
point of this skill, and every rule below follows from it.

This skill names sizes neutrally (`body`, `card-title`, `page-title`). Turning
those names into real utility classes is a sibling `tailwind-theme-setup`
skill's job in this plugin — read this first, then let the adapter write the
file.

## 1. Why a closed scale, and not "use your judgement"

An open-ended choice produces `13px` in one component and `14px` in the next
for the same kind of text, because both are defensible in isolation. Nobody
notices until the app has a dozen near-identical sizes, at which point nothing
can be restyled centrally — changing "body text" means auditing every file.

A closed scale removes the decision. The question stops being *"what size
should this be?"* (a judgement call, answered differently every time) and
becomes *"which of these named things is this?"* (a classification, answered
the same way every time). That is why the scale is enumerated exhaustively
below rather than described as a rough range.

## 2. The scale

Fourteen rungs, in pixels. Every one has a stated purpose — if a new piece of
text doesn't obviously match one, it is almost always the `14px` standard.

| px | Semantic name | Used for |
|---|---|---|
| 10 | `text-micro` | Very small metadata |
| 11 | `text-meta` | Secondary metadata |
| 12 | `text-caption` | Captions, helper text, badges, tooltips |
| 13 | `text-label` | Small labels, secondary table text, form labels |
| 14 | `text-body` | **Standard UI text — the default for most of the app** |
| 15 | `text-body-md` | Inputs, emphasized body text |
| 16 | `text-body-lg` | Default long-form body text |
| 18 | `text-card-title` | Card titles, section subtitles |
| 20 | `text-section-title` | Section headings |
| 24 | `text-heading` | Page headings |
| 28 | `text-page-title` | Major page heading, KPI values |
| 32 | `text-display-sm` | Login / hero heading |
| 36 | `text-display` | Large marketing heading |
| 40 | `text-display-lg` | Major login / landing display heading |
| 48 | `text-display-xl` | Large hero text, when genuinely required |

The full scale plus the usage table below, in a scannable one-page form, is in
`references/type-scale-cheatsheet.md`.

## 3. Where each rung actually goes

The scale says what exists; this says which one to reach for. When a component
type appears here, use the size listed — don't re-derive it.

| Element | Size |
|---|---|
| Page title | 28px |
| Page subtitle / description | 14px |
| Section title | 20px |
| Card title | 18px |
| Standard body | 14px (16px for long-form reading) |
| Sidebar navigation | 14px |
| Sidebar section label | 12px |
| Button text | 14px |
| Input text | 14px |
| Form label | 13px |
| Helper / validation text | 12px |
| Table header | 12–13px |
| Table body | 14px |
| Badge | 12px |
| Tooltip | 12px |
| Login main heading | 32px |
| Login description | 16px |
| Statistics / KPI value | 28–32px |

Worked example — a login form, entirely from the table above: welcome heading
28px, description 14px, form label 13px, input 14px, button 14px/600,
validation message 12px. No value in that screen was chosen; every one was
looked up.

## 4. Weights

Four weights only:

| Weight | Name | Use |
|---|---|---|
| 400 | Regular | Body text, table cells, most content |
| 500 | Medium | Labels, sidebar nav, subtle emphasis |
| 600 | Semibold | Buttons, headings, card titles, KPI values |
| 700 | Bold | Rare — reserve for genuine display/hero text |

Most application UI is 400, 500, and 600. **Avoid excessive 700** — when
everything is bold, the weight stops carrying meaning, and dense enterprise
screens are exactly where that failure is most visible. If a heading needs more
prominence, it usually needs a larger rung on the scale or more surrounding
space, not more weight.

## 5. Font families

Three families, each with a fallback chain and a narrow remit.

**Sans — `Inter`** → `ui-sans-serif`, `system-ui`, `sans-serif`

The default for essentially everything: navigation, forms, tables, buttons,
labels, dashboard content, general UI text.

**Mono — `Geist Mono`** → `Source Code Pro`, `ui-monospace`, `monospace`

For values where fixed-width alignment carries information: IDs, reference
codes, technical values, debug output, and columns of numbers that should line
up digit-for-digit. Not for prose that merely happens to be technical.

**Serif — `Instrument Serif`** → `Source Serif 4`, `Georgia`, `serif`

Intentional branding and display elements only — a marketing hero, a login
splash. **Never** normal dashboard content. If a serif is showing up inside a
data table, that's a misuse to flag.

Every family declares its fallback chain, so the layout stays intact during
webfont load and on any machine where the webfont fails to fetch.

## 6. Rules to enforce everywhere

- **Never write an arbitrary font size in a component.** Not `13px`, not a
  `text-[13px]`-style escape hatch, not an inline style. Use the semantic name.
  If nothing on the scale fits, that's a conversation about the scale, not a
  license to add a fifteenth size locally.
- **Never use a raw generic size name** (`text-sm`, `text-base`) where the
  system defines a semantic one — `text-sm` doesn't say whether it's a caption,
  a label, or a table header, so it can't be restyled by meaning later.
- **The scale is defined in exactly one place** — the theme file a sibling
  `tailwind-theme-setup` skill writes. A component never redefines a rung.
- **Serif never appears in dashboard content**; mono only where fixed-width
  actually matters.
- When a review turns up a size that isn't on the scale, map it to the nearest
  rung rather than widening the scale to accommodate it — the scale grows only
  by deliberate decision, never by accident.

---
_Last reviewed: 2026-08-11_
