# E2E Diagramming Standards (template edition)

The single source of truth for how a Kaizen E2E Solution Overview looks. **Everything here is taken
from the four E2E templates** (`01` master, `02` stencils, `03` palette/typography, `04` blocks).
Do **not** import the `solution-overview` skill's icon vocabulary (AWS/cloud/brand logos) or its JSON
renderer — this diagram is business-facing and shape-based.

---

## 1 · Colour format (Kaizen blue)

| Role | Hex |
|---|---|
| Kaizen blue — frame, band header, phase & group headers, accents | `#002F6C` |
| Light tint — phase-card / group fills | `#E7EEF6` |
| Band / group body | `#F5F8FB` |
| Supporting group header | `#8A94A0` |
| Supporting group body | `#F7F8FA` |
| Ink (text) | `#1A2B3C` |
| Muted (captions/roles) | `#5A6B7B` |
| Container border | `#C2C2C2` |
| Separator / hairline | `#C7CFD8` |
| **Arrows (all)** | `#000000` |
| Actor pill — peach (fill/stroke/icon) | `#FBE9DF` / `#E8B49A` / `#E07B54` |
| Actor pill — blue (fill/stroke/icon) | `#E7EEF6` / `#AEC3DA` / `#5B7FA6` |
| Format badge (MP4 / CSV / …) | `#002F6C` |

Phases are unified in Kaizen blue and told apart by **number + name + position** — never by giving
each phase a different hue.

## 2 · Typography (pt)

Title 28 · Subtitle 16 · Band header 14 (white) · Phase / group title 13 · Actor name 12 ·
Box / cylinder label 12–13 · Box detail 10 · Arrow labels 10–11 · Legend / footer title 12 ·
Footer body 10 · Caption 9. Two weights only: regular + bold. Sentence case.

## 3 · Shape vocabulary (icons) — from template 02 only

| Shape | draw.io style tell | Means |
|---|---|---|
| **Cylinder** | `shape=cylinder3` | Data store (DB, file, dataset) — light-blue fill `#E7EEF6` / `#002F6C` |
| **Rounded box** | `rounded=1` | Process / service (an action, component, job) — white / `#002F6C` |
| **Square container** | `rounded=0` + blue header bar | Group / layer (holds nodes) — SQUARE, numbered |
| **Diamond** | `rhombus` | Decision-point (quality gate / branch) |
| **Dashed box** | `rounded=0;dashed=1` | External system / API (outside the boundary) |
| **Person** | `shape=actor` | Actor / consumer |
| **Gray box** | `#F1F3F5` / `#5A6B7B` | Archive / rejected (neutral — never red) |
| **Rounded pastel card** | phase accent bar + chip | Phase card (strip) |
| **Rounded pill** | actor colours + person | Actor header pill |
| **Circle + number** | ellipse | Number chip (phase / group) |

No vendor/cloud/AWS/brand logos anywhere. The recognisable product name goes in `[brackets]` inside
a normal shape (e.g. `Model training\n[SageMaker]`).

## 4 · Flow notation — from templates 02 / 03

- **Solid black arrow** = data flow. Every arrow is labelled (protocol / operation / data).
- **Dashed black arrow** = async / optional / feedback.
- **No connector-dot (A/B) notation.** Represent every link — including feedback — as a labelled
  black arrow. Feedback loops are **optional**: include one only when a real loop exists.
- Orthogonal routing; one dominant reading direction (left → right, top → bottom inside a group).

## 5 · Layout (Approach 3, from template 01)

Top → bottom on one 1280×720 slide: **header** (Kaizen logo top-left · title centre · client logo
top-right) → **phase strip** (4 numbered blue cards = the business story) → **main automated band**
(navy/blue header, actor pills, then square groups left→right) → **footer** (Legend 1/4 · Data
Sources 1/2 · External APIs 1/4). Each phase card binds to a same-numbered group; extra groups are
neutral-gray "supporting". A feedback arrow is optional.

---

## 6 · Best Practices (BP-1…BP-10) — adapted to this template

Same intent as the Kaizen Diagramming Best Practices, with
two house adaptations (BP-4, BP-5) for the template's shape-based, arrow-only language.

- **BP-1 Balanced layout** — grid-aligned, evenly spaced, no crowding or big empty gaps; fits 1280×720.
- **BP-2 Uni-directional flow** — reads left→right; no backward-crossing solid arrows. A feedback
  loop, if present, is a single clean **dashed black arrow**, clearly labelled.
- **BP-3 Logical grouping** — nodes sit inside titled, square group containers; use a "supporting"
  group for architecture that isn't a phase beat.
- **BP-4 (adapted) No spaghetti** — keep arrows few and legible; **connector-dot notation is not
  used** — every link is a labelled black arrow. If a node would need many arrows, re-group instead.
- **BP-5 (adapted) Shape-based icons** — data stores = cylinders; processes, decisions, externals,
  actors each visually distinct per §3. **No technical/vendor logos** — product names live in
  `[brackets]`.
- **BP-6 Named arrows** — every arrow carries a label. Unlabeled arrows fail.
- **BP-7 Title & logos** — descriptive title top-centre, Kaizen logo top-left, client logo top-right.
- **BP-8 Encompassing border** — one frame around the whole slide (Kaizen blue).
- **BP-9 Legibility & beauty** — the type scale in §2, consistent sizes across peer elements, nothing
  clipped/overlapping; polished.
- **BP-10 Business-readable labels** — plain-language names of what a component does; flag deep
  jargon (model architectures, instance types, hyperparameters, versions, DDL) and rewrite (e.g.
  "GNN (GAT-3-layer-4-head) [SageMaker ml.g5.xlarge]" → "Anomaly Detection Model [SageMaker]").

### Self-review verdict format
```
VERDICT: PASS or FAIL
SCORE: n/10 (BP-1..BP-10)
REQUIRED CHANGES: numbered problem + fix, referencing component/location. "None" if PASS.
NICE-TO-HAVE: optional polish.
```
When self-reviewing, judge BP-4/BP-5 by the house rules: labelled black arrows instead of connector
dots, and shape-based icons (no logos).
