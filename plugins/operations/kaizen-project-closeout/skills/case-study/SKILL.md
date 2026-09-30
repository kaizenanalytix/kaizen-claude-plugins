---
name: case-study
description: >
  Use this skill when the EL or PM wants to create the Kaizen Case Study (D32, Mandatory)
  for a Kaizen PDP engagement.
  Trigger on: "create case study", "generate case study", "Kaizen case study",
  "D32 case study", "write the case study", "engagement case study",
  "project case study", "make the case study".
  This skill reads the full engagement record across all phases, generates a branded
  Case Study presentation (.pptx), and saves it to "6. Deploy".
---

# case-study Skill

Generate the Kaizen Case Study (D32, Mandatory) from the full engagement record. This is a
reusable, client-approved summary of the project for Kaizen's portfolio. Output: a branded
.pptx saved to `6. Deploy`.

Dependencies: read_phase_docs (shared MCP tool), write_deliverable (shared MCP tool),
kaizen-pptx-template skill (for PPTX rendering).

> **Guardrails:** This skill follows the shared guardrails (G1–G5) defined in the `guardrails`
> skill of shared-foundation-plugin. See that skill for version-not-overwrite, confirmation
> gates, verbatim financial data, deterministic finance, and approval gate rules.

---

## Step 0 — Locate the Project Root

Find the folder containing `6. Deploy/`.

If no workspace folder is connected, use `mcp__cowork__request_cowork_directory` to request one.
Extract the `PROJECT_ID`.

---

## Step 1 — Gather Full Engagement Record

Read key documents across all phases:

```bash
for phase in "0. Sales Alignment" "1. Sales Handoff & Transition" "2. Plan" "3. Analyze" "4. Design" "5. Develop" "6. Deploy"; do
  echo "=== $phase ==="
  find "<PROJECT_ROOT>/$phase/" -type f 2>/dev/null | sort
done
```

Prioritise these sources:

| Source | Purpose |
|---|---|
| SOW (D10) | Project scope and objectives |
| KT Brief | Client context, solution approach |
| Technical Design (D21) | Architecture and technology |
| Project Close Out (D31) | Key findings and results (incorporates the insights summary) |
| Project Sign-Off (D30) | Deliverables and acceptance status |
| Proposal (D7) | Original business case and value proposition |

### Ask the EL for additional context:
- Client-approved name for the case study (or permission to use client name)
- Quantifiable results or impact metrics (only include client-approved figures)
- Client testimonial or quote (if available)
- Permission level: public / Kaizen-internal only / anonymised

---

## Step 2 — Synthesise Case Study Content

### 2.1 Client & Challenge
- Client industry and size (anonymise if required)
- Business challenge or problem statement
- Why the client engaged Kaizen
- Key constraints or complexities

### 2.2 Solution
- Solution approach (2–3 paragraphs)
- Technologies and tools used
- Architecture highlights (reference D4/D21)
- Key innovations or unique aspects of the approach
- Team composition and engagement model

### 2.3 Results & Impact
- Key outcomes and deliverables
- Quantifiable results (only include client-approved metrics per G3)
- Business value delivered
- Client feedback or testimonial (if provided)

Per G4 (Deterministic Finance): do NOT compute ROI, cost savings, or revenue impact.
Only include metrics that are:
1. Directly from the solution output (e.g. "model achieved 95% accuracy")
2. Explicitly approved by the client for external use
3. Copied verbatim — never estimated or projected

### 2.4 Kaizen Differentiators
- What made Kaizen's approach unique
- Methodologies applied (PDP, Agile, specific frameworks)
- How challenges were overcome
- Lessons learned (for internal version only)

---

## Step 3 — Map Content to Slides

| Slide | Title | Content | Recommended Layout |
|---|---|---|---|
| 1 | Title Slide | "Case Study: [Client/Project Name]", Kaizen branding | `0_Title Slide` (slideLayout1) |
| 2 | The Challenge | Client context, business problem, why Kaizen | `6_Title, Subtitle, and Content` (slideLayout14) |
| 3 | Our Approach | Solution methodology, engagement model | `6_Title, Subtitle, and Content` (slideLayout14) |
| 4 | Solution Architecture | Architecture diagram (from D4), tech stack | `3_Title Only + Blank Space` (slideLayout8) |
| 5 | Key Results | Quantifiable outcomes, impact metrics | `3_Title Only + Blank Space` (slideLayout8) |
| 6 | Client Testimonial | Quote from client (if available) | `6_Title, Subtitle, and Content, Grey` (slideLayout15) |
| 7 | Kaizen Differentiators | What made this engagement successful | `6_Title, Subtitle, and Content` (slideLayout14) |

Adjust slide count based on content richness. A typical case study is 5–8 slides.

---

## Step 4 — Build the Deck

Invoke the kaizen-pptx-template skill and follow its PPTX build workflow.

---

## Step 5 — Save the Output

Present the proposed file to the user (per guardrail G2):
```
Proposed file:
  <PROJECT_ROOT>/6. Deploy/<PROJECT_ID> - Case Study.pptx

⚠ This may be shared externally. Confirm with the EL:
  - Client name usage approved? (or anonymise?)
  - All metrics client-approved for external use?
  - Permission level: public / internal / anonymised?

Reply "save" to write this file, or "revise" to make changes.
```

Per G5: this document may be shared externally — require explicit EL approval.

Check for existing versions (per guardrail G1).

After saving, present the file using `mcp__cowork__present_files`.

---

## Step 6 — Summary in Chat

```
✅ Case Study generated: 6. Deploy/<PROJECT_ID> - Case Study.pptx

Case study summary:
  • Client: [name or "Anonymised"]
  • Industry: [industry]
  • Key result: [headline metric or outcome]
  • Permission level: [public / internal / anonymised]
  • Slides: N

⚠ EL must confirm client approval before any external distribution.

Suggested next: Route to EL for review. Say "project closeout" to produce D31 and
archive all deliverables.
```

---

## Error Handling

| Situation | Action |
|---|---|
| No Project Close Out (D31) found | Ask EL for key results verbally |
| Client name usage not confirmed | Default to anonymised; use "[Client]" placeholder |
| No testimonial available | Omit testimonial slide |
| Results metrics not client-approved | Insert `[PENDING CLIENT APPROVAL]` placeholder |
| kaizen-pptx-template skill not available | Fall back to generic pptx skill |
| Project root ambiguous | Ask user to confirm path |

---

_Last reviewed: 2026-07-07_
