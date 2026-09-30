---
name: dataflow-diagrams
description: >
  Use this skill when the Architect or Tech Lead wants to generate the End-to-End and Data
  Flow Diagrams for an engagement.
  Trigger on: "generate data flow diagrams", "create E2E flow", "data flow diagram",
  "end to end flow", "E2E diagram", "DFD", "generate dataflow",
  "create the flow diagrams".
  This skill reads the technical design documents from the project folder, generates E2E and
  data flow diagrams (.drawio and/or .png), and saves them to a `diagrams/` folder.
---

# dataflow-diagrams Skill

Generate End-to-End Flow and Data Flow Diagrams from the technical design documents.
Output: .drawio files and/or rendered .png files saved to a `diagrams/` subfolder under the
working project folder.

Claude authors valid draw.io `.drawio` XML directly, and can optionally render PNG exports if
a local renderer is available.

**Guardrails:** Before writing any file, show the proposed path and get confirmation. Never
overwrite an existing file — version instead (" v2", " v3", …). Keep any financial figures
verbatim.

---

## Step 0 — Locate the Project Folder

Work inside a single connected/working project folder.

If no project folder is connected, ask the user to connect or point to it. If the project
folder is ambiguous, ask the user to confirm the path before proceeding.

---

## Step 1 — Inventory Source Documents

Search the project folder recursively for the source documents:

```bash
find "<PROJECT_ROOT>" -type f | sort
```

| Source | Purpose |
|---|---|
| Technical design documents | Component architecture, processing logic, APIs, database design, integrations |
| Solution overview | High-level architecture diagram |
| Business requirements document | Functional requirements for data flows |

If a needed input can't be found or is ambiguous, ask the user to point at the file(s).

If no technical design documents are found:
> "To generate data flow diagrams, I need the technical design documents. Please provide the
> technical design, or the processing and integration details."

---

## Step 2 — Identify Flows to Diagram

From the source documents, identify all flows that need diagramming:

### 2.1 End-to-End (E2E) Flows
Full process flows showing how data moves from source to consumption:
- Primary data pipeline (source → ingest → transform → store → serve)
- User interaction flows (request → process → response)
- Batch processing flows (schedule → extract → load → validate → report)
- ML/analytics flows (data → feature eng → train → evaluate → deploy → predict)

### 2.2 Data Flow Diagrams (DFDs)
Detailed data movement at each stage:
- Level 0: Context diagram (system boundary, external entities)
- Level 1: Major processes and data stores
- Level 2: Detailed sub-processes (for complex areas only)

### 2.3 Integration Flows
Per-integration sequence showing:
- Source system → protocol → transformation → target system
- Authentication steps
- Error handling and retry paths

---

## Step 3 — Generate the Diagrams

Claude authors valid draw.io `.drawio` XML directly (editable). Optionally render .png exports
if a local renderer is available.

### E2E Flow Diagram conventions
- **Swim lanes:** one per system or logical boundary (Client Systems, Ingestion, Processing,
  Storage, Consumption)
- **Flow direction:** left-to-right or top-to-bottom (be consistent across diagrams)
- **Shapes:**
  - Rounded rectangle = process / service
  - Cylinder = data store
  - Parallelogram = external system / data source
  - Diamond = decision point
  - Arrow = data flow (label with data type and protocol)
- **Colours:** Use Kaizen brand colours where possible
- **Labels:** Every arrow labelled with data type, format, and frequency
  (e.g. "Customer records, JSON, daily batch")

### Data Flow Diagram conventions
- Follow standard DFD notation (Yourdon & DeMarco or Gane & Sarson)
- **Circle / rounded rect** = process (numbered: 1.0, 1.1, 1.2)
- **Open rectangle** = data store (labelled: DS1, DS2)
- **Rectangle** = external entity
- **Arrow** = data flow (labelled with data name)
- Include data volume and frequency annotations where known

### Rendering output
Claude authors valid draw.io `.drawio` XML directly; optionally render PNG exports if a local
renderer is available, otherwise deliver the `.drawio` files (which open in draw.io). Include
the XML in a code block and write it to file. Also provide a text-based flow description as a
fallback.

---

## Step 4 — Present for Review

Present all diagrams to the user before saving (per guardrail):
```
Generated diagrams:

1. E2E Flow: [brief description of what it shows]
   Components: N | Data flows: N

2. Data Flow Diagram (Level 0): [context diagram description]

3. Data Flow Diagram (Level 1): [detailed flow description]

4. [Additional diagrams as needed]

Proposed files:
  <PROJECT_ROOT>/diagrams/E2E Flow.drawio
  <PROJECT_ROOT>/diagrams/E2E Flow.png
  <PROJECT_ROOT>/diagrams/Data Flow Diagram.drawio
  <PROJECT_ROOT>/diagrams/Data Flow Diagram.png

Reply "save" to write these files, or "revise" to make changes.
```

Check for existing versions and version rather than overwrite (per guardrail).

---

## Step 5 — Save the Output

After user confirmation, save all .drawio and .png files to a `diagrams/` subfolder under the
working project folder (create it if missing).

After saving, share the generated files with the user.

---

## Step 6 — Summary in Chat

```
✅ Data flow diagrams generated:
  • diagrams/E2E Flow.drawio (.png)
  • diagrams/Data Flow Diagram.drawio (.png)

Diagram summary:
  • E2E flows: N
  • DFD levels: N
  • Integration flows: N
  • Total data flows mapped: N

Items requiring validation:
  • [list any flows with [TO CONFIRM] labels]

Suggested next: Review the diagrams with the development team.
```

---

## Error Handling

| Situation | Action |
|---|---|
| No technical design documents found | Ask the user to provide the technical design or processing/integration details |
| No local renderer available | Generate .drawio XML and text descriptions; deliver the .drawio files |
| Processing logic unclear | Generate best-effort diagram with `[TO CONFIRM]` labels |
| A source file is a cloud-only stub | Note it, continue; advise the user |
| Project folder ambiguous | Ask user to confirm path |

---

_Last reviewed: 2026-08-27_
