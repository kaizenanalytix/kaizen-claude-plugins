---
name: kaizen-pptx-template
description: "Create PowerPoint presentations using the Kaizen Analytix branded template. Use this skill whenever the user asks to create a deck, presentation, slides, or pptx — the output MUST use the bundled Kaizen 2026 template. This skill takes priority over the generic pptx skill for all presentation creation requests. Trigger on any mention of: 'deck', 'slides', 'presentation', 'pptx', 'pitch deck', 'make a deck about', 'create a presentation on', or any request that would result in a .pptx file being created. Even casual requests like 'put together some slides on X' or 'I need a deck for a meeting about Y' should use this skill. The ONLY exception is if the user explicitly asks to edit someone else's existing .pptx file that is NOT the Kaizen template — in that case, use the generic pptx editing skill instead."
---

# Kaizen PPTX Template Skill

Every presentation you create uses the Kaizen Analytix 2026 branded template bundled at `assets/kaizen-2026-template.pptx` (relative to this skill's directory). Never create slides from scratch with pptxgenjs — always use the template-based editing workflow from the pptx skill.

## Step 1: Read the pptx editing guide

Before doing anything, read the pptx skill's editing workflow:
```
view /mnt/skills/public/pptx/editing.md
```

Then read the main pptx SKILL.md for QA and conversion instructions:
```
view /mnt/skills/public/pptx/SKILL.md
```

These contain the scripts and workflow you'll use. This skill adds Kaizen-specific guidance on top of that foundation.

## Step 2: Copy the template

Copy the template from this skill's assets to your working directory:
```bash
cp <this-skill-dir>/assets/kaizen-2026-template.pptx /home/claude/kaizen-template.pptx
```

## Step 3: Analyze the template

```bash
python /mnt/skills/public/pptx/scripts/thumbnail.py /home/claude/kaizen-template.pptx
extract-text /home/claude/kaizen-template.pptx
```

Then unpack it:
```bash
python /mnt/skills/public/pptx/scripts/office/unpack.py /home/claude/kaizen-template.pptx unpacked/
```

## Step 4: Understand the Kaizen template structure

The template has 11 example slides and 53 slide layouts. Here is the complete layout catalog — use this to plan which layouts to use for each piece of content.

### Template Branding (DO NOT MODIFY)
- **Theme**: "Kaizen PPT Theme 2026"
- **Font**: Aptos (both headings and body) — never override this
- **Color scheme** (Custom 8):
  - Dark 1: `#2E2E2E` (near-black text)
  - Light 1: `#FFFFFF` (white)
  - Light 2: `#F2F2F2` (light grey backgrounds)
  - Accent 1: `#002A45` (Kaizen prussian blue — primary brand color)
  - Accent 2: `#FFD358` (gold)
  - Accent 3: `#00A9E0` (light blue)
  - Accent 4: `#B1B3B3` (silver)
  - Accent 5: `#63666A` (dark grey)
  - Accent 6: `#797979` (medium grey)
- **Logo**: Kaizen "K" logo appears in layouts automatically — do not add or remove it
- **Footer**: "© 2026 Kaizen Analytix LLC | All Rights Reserved. CONFIDENTIAL & PROPRIETARY" — present in content layouts, inherited from layout

### Layout Catalog

Each layout has a white or grey variant. Grey variants have a light grey (`#F2F2F2`) background. Alternate between white and grey to add visual rhythm.

#### Title / Opening Slides
| Layout File | Name | Use For |
|---|---|---|
| slideLayout1.xml | 0_Title Slide | Opening slide — full cityscape background, logo top-right, navy diagonal header. Has: center title, subtitle, date/text field |
| slideLayout2.xml | 0_Title Slide 2 | Alternate opener — logo top-left, right-side photo. Has: center title, picture placeholder, subtitle, text field |
| slideLayout3.xml | 0_Client Title Slide | Client-facing opener — navy diagonal, right photo, logo bottom-left. Has: picture placeholders, subtitle, center title, text field |
| slideLayout31.xml | 1_GOLD - Title Slide | Gold-accent title slide variant |
| slideLayout32.xml | 1_GOLD - Client Title Slide | Gold-accent client title variant |

#### Section Dividers
| Layout File | Name | Use For |
|---|---|---|
| slideLayout4.xml | 0_Section Title Slide | Section breaks — full cityscape background, white content card with logo |
| slideLayout33.xml | 1_GOLD - Section Title Slide | Gold-accent section divider |

#### Agenda
| Layout File | Name | Use For |
|---|---|---|
| slideLayout5.xml | 1_Agenda | Agenda slide — left-side photo, title + two text areas on right |

#### Content Slides — Title + Subtitle + Blank
| Layout File | Name | Use For |
|---|---|---|
| slideLayout6.xml | 2_Title, Subtitle, and Blank Space | White bg, top header bar with logo. Title + subtitle at top, open space below for flexible content |
| slideLayout7.xml | 2_Title, Subtitle, and Blank Space, Grey | Grey variant of above |

#### Content Slides — Title Only + Blank
| Layout File | Name | Use For |
|---|---|---|
| slideLayout8.xml | 3_Title Only + Blank Space | White bg, title only, large blank area. Good for diagrams, charts, images |
| slideLayout9.xml | 3_Title Only + Blank Space, Grey | Grey variant |

#### Content Slides — With Client Logo
| Layout File | Name | Use For |
|---|---|---|
| slideLayout10.xml | 4_CLIENT LOGO_Title, Subtitle, and Blank Space | White, includes client logo placeholder |
| slideLayout11.xml | 4_CLIENT LOGO_Title, Subtitle, and Blank Space, Grey | Grey variant |
| slideLayout12.xml | 5_CLIENT LOGO_Title and Blank Space | White, client logo, title only |
| slideLayout13.xml | 5_CLIENT LOGO_Title and Blank Space, Grey | Grey variant |

#### Content Slides — Title + Subtitle + Content
| Layout File | Name | Use For |
|---|---|---|
| slideLayout14.xml | 6_Title, Subtitle, and Content | Pre-structured content area with text placeholder |
| slideLayout15.xml | 6_Title, Subtitle, and Content, Grey | Grey variant |

#### Content Slides — Title + Text Box
| Layout File | Name | Use For |
|---|---|---|
| slideLayout16.xml | 7_Title Only + Text Box | Title + single text body area |
| slideLayout17.xml | 7_Title Only + Text Box, Grey | Grey variant |

#### Content Slides — No Border Variants
| Layout File | Name | Use For |
|---|---|---|
| slideLayout18.xml | 8_Title, Subtitle, and Blank Space - NO BORDER | Clean, no header border line |
| slideLayout19.xml | 8_Title, Subtitle, and Blank Space, Grey - NO BORDER | Grey, no border |
| slideLayout20.xml | 9_Title Only + Blank Space - NO BORDER | Title only, no border |
| slideLayout21.xml | 9_Title Only + Blank Space, Grey - NO BORDER | Grey, title only, no border |

#### Multi-Column Content
| Layout File | Name | Use For |
|---|---|---|
| slideLayout22.xml | 10_Title Only and Two Content | Two-column layout, title only |
| slideLayout23.xml | 10_Title Only and Two Content, Grey | Grey variant |
| slideLayout24.xml | 11_Title, Subtitle, and Two Content | Two-column with subtitle |
| slideLayout25.xml | 11_Title, Subtitle, and Two Content, Grey | Grey variant |
| slideLayout26.xml | 12_Title and Three Content | Three-column layout |
| slideLayout27.xml | 12_Title and Three Content, Grey | Grey variant |
| slideLayout28.xml | 13_Title, Subtitle, and Three Content | Three-column with subtitle |
| slideLayout29.xml | 13_Title, Subtitle, and Three Content, Grey | Grey variant |

#### Split Layouts
| Layout File | Name | Use For |
|---|---|---|
| slideLayout30.xml | 14_2/3rd Split - Title, Subtitle, Two Content | 2/3 + 1/3 split with subtitle |
| slideLayout42.xml | 4_2/3rd Split - Two Content | 2/3 + 1/3 split, no subtitle |
| slideLayout51.xml | 25_2/3rd Split + Blank | 2/3 split, blank content area |
| slideLayout52.xml | 26_GOLD - 2/3rd Split + Blank | Gold variant of split |

#### Gold-Accent Content Layouts
| Layout File | Name | Use For |
|---|---|---|
| slideLayout34-41.xml | Gold variants | Same structure as standard content layouts but with gold accent elements instead of navy |

#### Special Purpose
| Layout File | Name | Use For |
|---|---|---|
| slideLayout43.xml | 16_Photo + Blank | Photo on one side, blank on other |
| slideLayout44.xml | 17_Case Study | Structured case study layout |
| slideLayout45.xml | 18_Case Study Blank | Blank case study layout |
| slideLayout46.xml | 19_Leadership & Team Bio | Single person bio with photo |
| slideLayout47.xml | 20_Two Team Member Bio | Two-person bio layout |
| slideLayout48.xml | 21_Three Team Member Bio | Three-person bio layout |
| slideLayout49.xml | 22_Former Team Bio | Former team member bio |
| slideLayout50.xml | 24_Center Title Only | Centered title, minimal |
| slideLayout53.xml | 27_Blank | Completely blank slide |

## Step 5: Plan the deck

Map the user's content to template layouts. Follow these rules:

1. **Always start with a Title Slide** (slideLayout1, 2, or 3) as slide 1
2. **Use Section Title Slides** (slideLayout4) to break up major sections
3. **Vary layouts** — don't repeat the same layout for consecutive slides. Alternate between:
   - White and grey background variants
   - Title+subtitle and title-only variants
   - Single-column, two-column, and three-column layouts
4. **Match content to layout and format**:
   - Comparisons → two-column (slideLayout22-25)
   - Three parallel items → three-column (slideLayout26-29)
   - Agenda or table of contents → agenda layout (slideLayout5)
   - Team introductions → bio layouts (slideLayout46-49)
   - Case studies → case study layouts (slideLayout44-45)
   - Large visuals or charts → blank-space layouts (slideLayout8-9, 20-21)
   - Dense text → title+content layouts (slideLayout14-17)
   - **Tabular data** (team rosters, pricing/costing, role matrices, feature comparisons with 3+ structured columns) → **OOXML `<a:tbl>` tables**, NOT monospaced text or text-box columns. Place the table inside a blank-space layout (slideLayout8-9) or as a content element in any layout with open space.
5. **End with a closing/thank-you slide** using a title slide variant or section title

### Content-to-format decision rules

When deciding how to render content, follow this priority:

1. **Tabular data** (roles + attributes, pricing, schedules with columns) → OOXML table
2. **Comparison or parallel items** (2–3 things side by side) → multi-column layout
3. **Sequential/phased content** (timelines, processes) → single-column with bold phase headers (accent1, 20pt) and indented bullets below each
4. **Narrative + key points** (solution description, executive summary) → intro paragraph followed by bulleted capabilities
5. **Key metrics / ROI** → large stat callouts (28–36pt bold) alongside supporting bullets

**Never render tabular data as monospaced text in a text box — always use a real table.**

## Step 6: Build the deck

Follow the pptx editing workflow exactly:

1. Unpack the template (already done in Step 3)
2. Delete unwanted example slides from `<p:sldIdLst>` in `ppt/presentation.xml`
3. Use `add_slide.py` to create new slides from the chosen layouts
4. Reorder `<p:sldId>` entries in `<p:sldIdLst>` to match your planned order
5. **Add explicit positions to all placeholders** (see critical rule below)
6. Complete all structural changes before editing content
7. Edit content in each slide XML using the str_replace tool (not sed or Python)
8. Run `clean.py` to remove orphaned files
9. Run `pack.py` to create the final .pptx

### CRITICAL: Add explicit positions to all placeholder shapes

When `add_slide.py` creates a slide from a layout, the slide XML contains empty `<p:spPr/>` for each placeholder. PowerPoint inherits positions from the layout, but **LibreOffice and some renderers DO NOT** — causing all placeholders to stack at (0,0) and overlap each other.

**After creating slides and before editing content**, add explicit `<a:xfrm>` coordinates to every placeholder's `<p:spPr>`. Copy the exact x, y, cx, cy values from the corresponding layout XML.

Example — change this:
```xml
<p:spPr/>
```
To this (copying values from the layout):
```xml
<p:spPr><a:xfrm><a:off x="415290" y="1335805"/><a:ext cx="5181600" cy="4937760"/></a:xfrm></p:spPr>
```

This is **ESPECIALLY critical** for:
- **Multi-column layouts** (slideLayout22–29): columns will overlap without explicit positions
- **Two-content layouts** (slideLayout24–25): left and right panels render on top of each other
- **Any layout with both a subtitle (idx=13) and content (idx=14) placeholder**: the subtitle will overlap the content area

To extract positions from layouts, parse each layout XML and find the `<a:xfrm>` inside each `<p:sp>` that has a `<p:ph>` element. Match by placeholder `idx` value.

### Critical rules for content editing

- **Preserve all `<a:rPr>` formatting** — copy font sizes, bold settings, and color references from existing placeholders when adding text
- **Use scheme colors** — reference theme colors (`<a:schemeClr val="accent1"/>`) not hardcoded hex values, so the brand palette stays consistent
- **Bold all headers** — use `b="1"` on `<a:rPr>` for slide titles, section headers, and inline labels
- **Separate list items** into individual `<a:p>` elements — never concatenate multiple items into one paragraph
- **Use XML entities for smart quotes** — `&#x201C;` and `&#x201D;` for double quotes
- **Don't add decorative elements** — the template's visual design (diagonal lines, logo placement, footer) comes from the layouts. Don't add colored bars, accent lines, or decorative shapes.

### Text color by layout type

- **Title Slides (slideLayout1, 2, 3)**: Use `accent1` (navy) for title text and `accent5` (dark grey) for subtitle/date text. **NEVER use `lt1` (white)** — the cityscape background has light/cloudy areas that make white text invisible.
- **Section Title Slides (slideLayout4)**: Use `dk1` (near-black) for the title and `accent5` for the subtitle — the white content card behind the text needs dark text for contrast.
- **Content Slides (all others)**: Titles inherit from the layout (dark text on the header bar). For body text, use default `dk1`. For inline labels/headers within body content, use `accent1` (navy) with `b="1"`. For milestone or callout labels, use `accent3` (light blue).

### Font sizes (minimums — never go below these)

| Element | Size | Notes |
|---|---|---|
| Slide titles | 2800 (28pt) | Bold, always |
| Section headers within a slide | 1700–2000 (17–20pt) | Bold, navy (`accent1`) |
| Body text / bullet content | 1500–1600 (15–16pt) | Main readable content |
| Subtitles (under header bar) | 1400 (14pt) | `accent5` color |
| Table cell text | 1100–1300 (11–13pt) | Acceptable since tables have structure |
| Footnotes / source citations | 1000 (10pt) | Minimum for any text on the slide |

**Never use 1100–1200pt for main body text outside of tables.** If content doesn't fit at 1500pt, split across two slides rather than shrinking the font.

### Spacing standards

- **Line spacing**: Use `<a:lnSpc><a:spcPts val="2200"/>` to `<a:spcPts val="2600"/>` (22–26pt) for body text. Never rely on default single spacing — it creates cramped, hard-to-read slides.
- **After-paragraph spacing**: Use `<a:spcAft><a:spcPts val="600"/>` to `<a:spcPts val="1000"/>` (6–10pt) between bullet groups to create breathing room.
- **Fill the slide**: Content should use **70–90% of the available area** below the header bar. If content only fills the top third of the slide, increase font sizes, add more spacing between items, or restructure the layout. Empty lower halves look unfinished and unprofessional.

### Table formatting standards

When using OOXML `<a:tbl>` tables:

- **Header row**: Navy fill (`<a:schemeClr val="accent1"/>`), white bold text (`<a:srgbClr val="FFFFFF"/>`), font size 1200–1400
- **Body rows**: Alternate `#F2F2F2` grey and `#FFFFFF` white for row banding
- **Role/label column**: Bold text, navy color (`accent1`)
- **Totals/summary row**: Light navy tint fill (`<a:schemeClr val="accent1"><a:lumMod val="20000"/><a:lumOff val="80000"/></a:schemeClr>`), bold navy text
- **Table style**: Use `<a:tblStyle val="{5940675A-B579-460E-94D1-54222C63F5DA}"/>` for clean default styling
- **Highlight callouts**: Use `accent3` (light blue) to highlight special items (e.g., offshore team members, key differentiators)

## Step 7: QA

Follow the QA process from the pptx SKILL.md exactly:
1. Run `extract-text` to verify all content is present and no placeholder text remains
2. Convert to images and visually inspect for overlaps, overflow, and alignment issues
3. Fix any issues found
4. Re-verify affected slides

Always check for leftover placeholder text:
```bash
extract-text output.pptx | grep -iE "\bx{3,}\b|lorem|ipsum|\bTODO|\[insert|this.*(page|slide).*layout|click to"
```

### Visual QA checklist (in addition to the standard pptx QA)

When inspecting rendered slides, specifically verify:
- [ ] Title slide text is readable against the cityscape background (not white-on-white)
- [ ] Multi-column layouts have columns side by side, not stacked/overlapping
- [ ] All body text is ≥15pt and readable at presentation distance
- [ ] Content fills 70–90% of the slide area (no large empty bottom halves)
- [ ] Tabular data uses real tables, not monospaced text boxes
- [ ] Table header rows have navy background with white text
- [ ] No text overflows the slide bottom edge or the footer bar
