---
name: technical-design
description: >
  Use when an Architect or Tech Lead wants detailed Technical Design documentation for an
  engagement. Produces a SET of standalone design docs (not one file), auto-detected from the
  requirements: Technical Design Overview plus back-end, security, and infrastructure & deployment
  (always), and front-end, API, integration, processing/algorithm (when applicable). Interviews the
  architect on deciding factors (tech stack, architecture, hosting, auth) first. Trigger on:
  "draft/create/generate technical design", "TDD", "technical design document", "generate design
  documents", "front-end design", "back-end design", "API spec", "security design", "infrastructure
  design", "design documentation". Reads requirements/context from the project folder and writes one
  .docx per document to a `design/` folder. Does NOT produce the data model (use `data-model`),
  data-flow diagrams (use `dataflow-diagrams`), or the solution overview diagram (use `e2e-diagrams`)
  — it references them instead.
---

# technical-design Skill

Generate the **detailed Technical Design documentation set** for an engagement from the
Business Requirements and other requirements/technical inputs. Rather than a single monolithic
document, this skill produces **multiple standalone `.docx` design documents**, each with its own
version history, review cycle, and owner — auto-detected from the project's requirements. All
outputs save to a `design/` subfolder under the working project folder.

**Guardrails:** Before writing any file, show the proposed output paths and get confirmation.
Never overwrite an existing file — version instead (" v2", " v3", …). Keep financial figures
verbatim.

---

## Ownership boundary — what this skill does and does NOT produce

This skill owns the **written detailed-design documents**. Three sibling skills own the rest of
the Design phase; this skill **references** them, it never regenerates their output.

| This skill PRODUCES (written design docs) | Delegated to a sibling skill (do NOT generate here) |
|---|---|
| Technical Design Overview | Business Requirements → `business-requirements` |
| Front-end / UI Design | Data model, ERD, DDL, data dictionary, source-to-target → `data-model` |
| Back-end / Application Design | Data-flow & E2E process diagrams (DFDs) → `dataflow-diagrams` |
| API / Interface Specification | Business-facing solution overview diagram → `e2e-diagrams` |
| Integration Design | |
| Processing / Algorithm / ML Design | |
| Security Design | |
| Infrastructure & Deployment Design | |

When the requirements clearly imply a delegated artifact (a schema, a data flow, an architecture
picture), **flag it and point the user at the right skill** in the Step 5 summary — do not build it.

---

## The document set

Every generated document is a separate `.docx`. Each carries a **lightweight traceability table**
(see "Traceability" below) linking it back to the requirement IDs it satisfies.

### Universal set — always generated
| Document | Purpose |
|---|---|
| **Technical Design Overview** | The parent/index doc: architecture summary, technology-stack table (exact versions), component map, cross-cutting concerns, links to every child doc and to the delegated deliverables, and the rolled-up traceability. The doc a reviewer opens first. |
| **Back-end / Application Design** | Services/modules, processing logic, internal data-store interaction, configuration & dependency management, error handling. |
| **Security Design** | AuthN/authZ model, secrets management, data protection (in transit / at rest), vulnerability scanning, compliance notes. |
| **Infrastructure & Deployment Design** | Environment matrix, IaC approach, containers/serverless, CI/CD pipeline, scaling strategy, monitoring & alerting (design-time topology, not a runtime runbook). |

### Conditional set — generated only when auto-detected (see Step 2)
| Document | Generated when the requirements show… |
|---|---|
| **Front-end / UI Design** | UI, screens, dashboard, portal, web/mobile app, UX, wireframes, user-facing interaction |
| **API / Interface Specification** | API, endpoint, REST/GraphQL, webhook, service interface, third-party integration |
| **Integration Design** | multiple external systems, messaging/queues, event streams, external ingestion (offer to fold into the API Spec if thin) |
| **Processing / Algorithm / ML Design** | model, ML, scoring, forecast, optimisation, rules engine, non-trivial batch transformation logic |

Each document's full section skeleton lives in `references/<doc>.md`. Read only the outlines for
the confirmed set in Step 3.

| Document | Outline file |
|---|---|
| Technical Design Overview | `references/technical-design-overview.md` |
| Front-end / UI Design | `references/frontend-design.md` |
| Back-end / Application Design | `references/backend-design.md` |
| API / Interface Specification | `references/api-spec.md` |
| Integration Design | `references/integration-design.md` |
| Processing / Algorithm / ML Design | `references/processing-algorithm-design.md` |
| Security Design | `references/security-design.md` |
| Infrastructure & Deployment Design | `references/infra-deployment-design.md` |
| *Deciding-factor interview (Step 3)* | `references/deciding-factor-questions.md` |

---

## Step 0 — Locate the Project Folder

Locate the working project folder — the folder that holds the requirements and context documents.

If no project folder is connected, ask the user to connect or point to it. If the project folder
is ambiguous, ask the user to confirm the path before proceeding.

---

## Step 1 — Inventory Source Documents

```bash
find "<PROJECT_FOLDER>" -type f | sort
```

Search the project folder recursively for the source documents below. If a needed input can't be
found or is ambiguous, ask the user to point at the file(s).

| Source | Purpose | Precedence |
|---|---|---|
| Business Requirements Document (BRD) | Functional & non-functional requirements, requirement IDs, data & integration needs | **Primary** — the requirement source of truth |
| Any standalone requirements doc / requirements review | Additional or earlier requirements if no BRD exists | Fallback if no BRD |
| Solution overview / E2E diagram | Architecture context and component boundaries | Context |
| Technical checklist | Tech stack, environment, access details | Context |
| SOW | Scope and technology constraints | Context |
| Existing data model | Entities the back-end/API design must align to | Context (do not regenerate) |

Extract text from each source document using an appropriate reader for its file type.

If **no BRD and no requirements document** is found, stop and advise:
> "To draft the design documentation I need the Business Requirements (BRD) or a requirements
> document. Please run 'draft BRD' first, or point me at the requirements file."

If the BRD is present but thin, continue and fill gaps with `[TO CONFIRM]` placeholders.

---

## Step 2 — Auto-detect the Applicable Document Set  *(new — the core of the multi-doc behaviour)*

Read the BRD / requirements and assemble the set of documents to produce.

1. **Start with the universal set** (always in): Technical Design Overview, Back-end / Application
   Design, Security Design, Infrastructure & Deployment Design.
2. **Scan for conditional-document signals.** Detect each conditional doc from BOTH:
   - **Keyword signals** — the trigger words in the conditional table above (UI/screen/dashboard;
     API/endpoint/webhook; queue/event/external system; model/algorithm/scoring/rules…).
   - **Structural cues** — a Front-end presence in the BRD's scope, an integration/interface list,
     a features inventory, NFRs that imply a UI (usability/accessibility) or APIs (integration
     SLAs), data-heavy processing sections.
3. **Detect delegated artifacts** — data model/schema, data flows, architecture diagram — and note
   them for the summary (do NOT add them to the generation set).
4. **Assemble the proposed set with evidence.** For each conditional doc that fired, capture the
   phrase(s) that triggered it.

Then present the proposed set for **one batch confirmation** — the user toggles the
set before anything is generated:

```
Based on the requirements, I'll generate these design documents:

  UNIVERSAL (always)
    1. Technical Design Overview
    2. Back-end / Application Design
    3. Security Design
    4. Infrastructure & Deployment Design

  DETECTED AS APPLICABLE
    5. Front-end / UI Design        ← triggered by: "operations dashboard", "user login screen"
    6. API / Interface Specification ← triggered by: "expose scoring API", "Salesforce integration"

  NOT GENERATED HERE (handled by other skills — run these separately if needed)
    • Data model / schema      → run `data-model`
    • Data-flow diagrams       → run `dataflow-diagrams`
    • Solution overview diagram → run `e2e-diagrams`

Reply "go" to generate all of the above, or tell me which to add/remove
(e.g. "drop the front-end doc", "add processing/algorithm design").
```

Only proceed once the user confirms the set.

---

## Step 3 — Deciding-Factor Interview  *(MANDATORY — always runs before any content is generated)*

Before writing a single document, interview the solution architect on the decisions that determine
what goes into the docs (tech stack, architecture style, hosting, auth, and so on). This step runs
**every time**, even when the source documents look complete — the architect is the source of truth
for these choices. The full question bank is in `references/deciding-factor-questions.md`; read it
and follow its rules.

How to run it:

1. **Select the relevant question blocks.** Block A (global) plus F, G, H (universal docs) always
   apply. Add blocks B/C/D/E only for the conditional documents the architect confirmed in Step 2 —
   don't ask front-end questions if no Front-end Design is being generated.
2. **Pre-fill from the source docs.** For each question, if the technical checklist, SOW, or an
   existing doc already answers it, present that as the **proposed answer with its source** and ask
   the architect to **confirm or override** — don't ask cold when you already know.
3. **Ask in batches** (use `AskUserQuestion` where available). Each question offers sensible options
   with a recommended default and always allows a free-text answer or **"decide later"**.
4. **Never invent a decision.** Any question the architect defers becomes `[TO CONFIRM]` in the
   documents — it is never guessed.
5. **Compile the answers into the Design Decisions Register** (chosen value · source =
   architect/technical checklist/SOW · rationale if given). This register is written into the Overview doc (§6) and
   is the single source of truth every child document draws its technology/approach statements from.

Do not proceed to Step 4 until the interview is complete (every applicable question is answered or
explicitly deferred).

---

## Step 4 — Generate Each Confirmed Document (.docx)

For each document in the confirmed set:

1. **Read its outline** from `references/<doc>.md` — that file owns the section skeleton, the
   per-section guidance, and the formatting notes for that document. Do not inline the structure
   here; the reference files are the single source of truth for document structure.
2. **Populate it** from the requirements + technical context (Step 1) and the **Design Decisions
   Register** (Step 3) — all technology/approach statements come from the architect's answers, not
   from inference.
3. **Inject the traceability table** (see below) as a fixed section near the top of the document.
4. **Apply the shared formatting rules** (below).
5. Enforce **exact technology versions** (never "latest"); unknowns become `[TO CONFIRM]`.

Generate every document as its own `.docx`, named
`<PROJECT_FOLDER>/design/<Document Name>.docx`, e.g.:
- `Technical Design Overview.docx`
- `Back-end Design.docx`
- `API Specification.docx`

### Traceability table (every document)

Each document includes a **Requirements Traceability** section — a lightweight table sourced from
the BRD's requirement IDs (`FR-###`, `NFR-###`):

| Req ID | Requirement (short) | Design element in this doc | Section ref |
|---|---|---|---|
| FR-012 | Users can export the report to PDF | `ExportService.renderPdf()` | §3.2 |
| NFR-004 | p95 response < 500 ms | Async worker + read replica | §4.1 |

The **Technical Design Overview** additionally carries a **rolled-up** traceability matrix listing
every requirement ID across the whole set and which document(s) address it — with any requirement
not covered by any document flagged `[GAP — no design element]`.

### Shared formatting rules
- Table header rows: Kaizen navy `#0A2342`, white text.
- Code snippets: monospace font, light grey background.
- Technology versions: always exact versions, never "latest".
- `[TO CONFIRM]` placeholders (orange highlight) for details requiring team validation.
- Every document carries a Document Control block: Version History (Version | Date | Author |
  Changes) and Reviewers (Name | Role | Review Date).

---

## Step 5 — Present & Save (batch)

Present the whole set at once, then a **single save-all** confirmation. Version checks are still
applied **per file** — if any target name already exists, bump that file's version (" v2", " v3",
…) rather than overwriting; existing single "Technical Design.docx" files are left untouched (this
set coexists with them).

```
Generated design documents (drafts) for the `design/` folder:
  1. Technical Design Overview.docx
  2. Back-end Design.docx
  3. Security Design.docx
  4. Infrastructure & Deployment Design.docx
  5. Front-end Design.docx
  6. API Specification.docx

Reply "save" to write all of these, or "revise <n>" to change one before saving.
```

After saving, share the generated files with the user.

---

## Step 6 — Summary in Chat

```
✅ Design documentation generated in the `design/` folder:
   • Technical Design Overview.docx
   • Back-end Design.docx
   • Security Design.docx
   • Infrastructure & Deployment Design.docx
   • Front-end Design.docx
   • API Specification.docx

Set summary:
  • Documents generated: N (universal: 4, conditional: N)
  • Requirements traced: N of M BRD requirements  (uncovered: [list any GAPs])
  • Tech-stack components pinned: N

Not generated here (run these skills if you need them):
  • Data model / schema      → say "generate data model"       (data-model)
  • Data-flow diagrams       → say "generate data flow diagrams" (dataflow-diagrams)
  • Solution overview diagram → say "create E2E diagram"         (e2e-diagrams)

Items requiring team input:
  • [list any [TO CONFIRM] items across the set]

Suggested next: review each doc with the owning lead (front-end lead → Front-end Design, etc.),
then run `data-model` and `dataflow-diagrams` to complete the Design phase.
```

---

## Error Handling

| Situation | Action |
|---|---|
| No BRD / requirements doc found | Stop; advise user to run `business-requirements` first, or point at the requirements file |
| Requirements thin / vague | Generate with `[TO CONFIRM]` placeholders; list unknowns in the summary |
| Tech stack / deciding factors not in source docs | Ask the architect in the Step 3 interview; if deferred, write `[TO CONFIRM]` — never guess |
| Architect skips the interview | Do not generate; the interview is mandatory. Offer to proceed with all-`[TO CONFIRM]` only on explicit instruction |
| Only universal docs detected (no conditional signals) | Generate the 4 universal docs; note that no UI/API/integration/algorithm signals were found |
| User wants a delegated artifact (schema, DFD, diagram) | Do not build it; point to `data-model` / `dataflow-diagrams` / `e2e-diagrams` |
| A requirement maps to no design element | Flag `[GAP — no design element]` in the Overview's rolled-up traceability |
| Existing single "Technical Design.docx" present | Leave it untouched; generate the set alongside (coexist). Offer a later "split existing TDD into the set" pass if asked |
| A source file is a cloud-only stub | Note it, continue; advise user to download/provide the file |
| Project folder ambiguous | Ask user to confirm path |

---

_Last reviewed: 2026-08-27_
