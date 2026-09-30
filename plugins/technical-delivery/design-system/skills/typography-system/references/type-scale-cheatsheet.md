# Typography cheat sheet

One page, no prose. For the reasoning behind any of it, see `SKILL.md`.

## Scale

```
10px  text-micro           Very small metadata
11px  text-meta            Secondary metadata
12px  text-caption         Captions, helper text, badges, tooltips
13px  text-label           Small labels, form labels, secondary table text
14px  text-body            *** STANDARD UI TEXT — the default ***
15px  text-body-md         Inputs, emphasized body
16px  text-body-lg         Long-form body text
18px  text-card-title      Card titles, section subtitles
20px  text-section-title   Section headings
24px  text-heading         Page headings
28px  text-page-title      Major page heading, KPI values
32px  text-display-sm      Login / hero heading
36px  text-display         Large marketing heading
40px  text-display-lg      Major login / landing display
48px  text-display-xl      Large hero, when genuinely required
```

## Weights

```
400  Regular    body, table cells, most content
500  Medium     labels, sidebar nav, subtle emphasis
600  Semibold   buttons, headings, card titles, KPI values
700  Bold       rare — genuine display/hero text only
```

## Element → size lookup

```
Page title             28px          Form label            13px
Page subtitle          14px          Helper / validation   12px
Section title          20px          Table header          12–13px
Card title             18px          Table body            14px
Standard body          14px (16 long-form)
Sidebar nav            14px          Badge                 12px
Sidebar section label  12px          Tooltip               12px
Button text            14px / 600    Login heading         32px
Input text             14px          Login description     16px
                                     KPI value             28–32px
```

## Families

```
Sans   Inter             → ui-sans-serif, system-ui, sans-serif
       everything: nav, forms, tables, buttons, labels, dashboard content

Mono   Geist Mono        → Source Code Pro, ui-monospace, monospace
       IDs, codes, technical values, debug output, aligned numeric columns

Serif  Instrument Serif  → Source Serif 4, Georgia, serif
       branding / display ONLY — never dashboard content
```

## The one rule

Pick a name from the scale. Never write a raw px value, an arbitrary-value
escape hatch, or an inline font-size in a component.

---
_Last reviewed: 2026-08-11_
