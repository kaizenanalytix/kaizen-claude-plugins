---
name: tech-architecture-diagram
description: >
  Use this skill when an Architect or Tech Lead wants a high-level TECHNICAL ARCHITECTURE diagram
  for an engagement — the concrete system decomposed into client, networking, application, and data
  tiers, with the specific technologies in each block (e.g. React, FastAPI, PostgreSQL) shown with
  rich tech-stack iconography. Trigger on: "tech architecture diagram", "technical architecture
  diagram", "system architecture diagram", "architecture diagram of the stack", "draw the
  architecture", "high level architecture", "solution architecture diagram", "tech stack diagram",
  "components and tiers diagram". Reads the technical design documents and the data model, then
  produces a clean, renderable draw.io (.drawio) file with grouped per-tier subgraphs and clear
  directionality, saved to a `diagrams/` folder.
---

# tech-architecture-diagram Skill

Produce a **high-level technical architecture diagram** as an editable **draw.io (`.drawio`)**
file. Act as a **principal system architect**: decompose the system into concrete components across
the **client, networking, application, and data** tiers (add **integration/external** and a
**security/cross-cutting** band when the design calls for them), name the **specific technology** in
each block (React, FastAPI, PostgreSQL, Redis, S3, …), draw it with **rich tech-stack iconography**,
and give it **clear directionality** with each layer in its own **grouped subgraph**.

Unlike the business-facing `e2e-diagrams` solution overview (plain-language, no logos), this diagram
is **technical and stack-explicit** — it is the picture an engineer opens to see what is built with
what, and how the tiers connect.

You author the `.drawio` XML directly (see `references/drawio-architecture.md` for tier layout, the
shape/icon library, and copy-ready style strings). No external renderer is required.

> **Guardrails:** Before writing any file, show the proposed path and get the user's confirmation.
> Never overwrite an existing file — if the target name already exists, save a new version (append
> " v2", " v3", …). Take every technology and component from the design documents / data model or
> the architect's confirmation — never invent a stack. Mark anything unconfirmed `[TO CONFIRM]`.

---

## Step 0 — Locate the working folder

Find the connected/working **project folder**. If none is connected, ask the user to connect or
point to it. The diagram is written to a `diagrams/` subfolder under it (create it if missing).

## Step 1 — Read the design and the data model

Search the project folder and read whatever exists (ask the user to point at the file(s) if nothing
is found):

| Source | What to pull |
|---|---|
| Technical Design Overview | the technology-stack table, component map, cross-cutting concerns |
| Back-end / Application Design | services/modules, runtimes, frameworks, internal APIs |
| Front-end / UI Design | client apps, frameworks, delivery (web/mobile) |
| API / Interface Specification | the API surface, gateway, protocols |
| Integration Design | external systems, messaging/queues, event streams |
| Infrastructure & Deployment Design | hosting/cloud, containers/serverless, CI/CD, networking |
| Security Design | auth, secrets, edge protection (for the cross-cutting band) |
| Data model (ERD / DDL / data dictionary) | the data stores and their engines (PostgreSQL, Snowflake, …) |

If the technical design set doesn't exist yet, offer to run `technical-design` and `data-model`
first, or let the architect describe the stack directly.

## Step 2 — Decompose into tiers and confirm the stack

Assemble the component-to-tier map. Use these tiers (include a tier only if it has real content):

1. **Client / Presentation** — web app, mobile app, portal, BI tool, external caller. Tech: React,
   Angular, Next.js, iOS/Android, Power BI, …
2. **Networking / Edge** — CDN, DNS, load balancer, API gateway, WAF, VPN. Tech: CloudFront, ALB,
   API Gateway, nginx, …
3. **Application / Services** — the business logic: services, workers, jobs, ML/scoring, cache,
   message bus. Tech: FastAPI, Node/Express, Spring Boot, Celery, Kafka, Redis, SageMaker, …
4. **Data / Persistence** — operational + analytical stores, object storage, search, warehouse.
   Tech: PostgreSQL, MongoDB, S3, Snowflake, Elasticsearch, …
5. **Integration / External** (optional) — third-party APIs, SaaS, upstream/downstream systems.
6. **Security & Cross-cutting** (optional band) — auth/identity, secrets, observability, CI/CD.

For each block record the **specific technology** (and a product/version only if the sources give
one). Where the sources are silent on a technology choice, either pull it from the design's
tech-stack table or **ask the architect** (a short batch of questions) — do not guess a stack. Any
choice left open becomes `[TO CONFIRM]` in the block.

Confirm the tier map before drawing:

```
Proposed architecture (tiers → components [tech]):
  Client      : Web App [React], Mobile [React Native]
  Networking  : CDN [CloudFront], API Gateway [AWS API GW]
  Application : Order API [FastAPI], Worker [Celery], Cache [Redis], Auth [Cognito]
  Data        : Operational DB [PostgreSQL], Object store [S3], Warehouse [Snowflake]
  External    : Payments [Stripe]
Reply "go", or adjust any block/technology.
```

## Step 3 — Author the draw.io architecture diagram

Read `references/drawio-architecture.md` and build the `.drawio` XML directly. Requirements:

- **One grouped subgraph per tier** — a titled, colour-coded container (draw.io `group`/container
  cell) holding that tier's component nodes. Order the tiers to match the primary flow.
- **Clear directionality** — a dominant reading direction (top → bottom: Client → Networking →
  Application → Data, or left → right). Connect tiers/components with labelled arrows showing the
  request/data direction (e.g. `HTTPS`, `SQL`, `gRPC`, `events`). Cross-cutting concerns (auth,
  observability) attach to the side as a band, not inline in the main flow.
- **Rich tech iconography** — give each component a real technology icon where a stencil exists
  (cloud-provider resource icons for AWS/Azure/GCP services; the built-in stencils for databases,
  queues, caches, containers, Kubernetes, etc.). For a product with no built-in stencil (React,
  FastAPI, PostgreSQL, …), use a clean labelled node tinted with the product's brand colour and the
  technology name — the reference lists the exact style strings and the brand-colour table. Data
  stores are cylinders. Keep icons consistent in size.
- **Labels** — each block shows the **component role** and the **[technology]** (e.g.
  `Order API\n[FastAPI]`, `Operational DB\n[PostgreSQL]`).
- **Chrome** — a descriptive title top-centre; a single frame around the whole diagram; a small
  legend if you used tier colours or icon conventions worth explaining.

## Step 4 — Self-review

Check the diagram and fix anything that fails:

- [ ] Every tier with content is a titled, grouped container; empty tiers are omitted.
- [ ] Every component names a specific technology (or is marked `[TO CONFIRM]`).
- [ ] Data stores render as cylinders; cloud services use their provider icons; icon sizes are
      consistent.
- [ ] Arrows show a clear, mostly uni-directional flow and are labelled with protocol/data.
- [ ] Cross-cutting concerns sit in a side band, not tangled into the main path.
- [ ] Title + single frame present; nothing overlaps or is clipped; the file is well-formed XML.

## Step 5 — Present & save

Show a summary (tiers, component count, technologies, any `[TO CONFIRM]`) and the proposed path
`diagrams/Technical Architecture.drawio`. On confirmation, write the file (versioning instead of
overwriting) and share it with the user.

```
✅ Technical architecture diagram generated: diagrams/Technical Architecture.drawio
   Tiers: client, networking, application, data[, external, security]
   Components: N   Technologies: React, FastAPI, PostgreSQL, …

To confirm:
  • [list any [TO CONFIRM] blocks]
```

---

## Error handling

| Situation | Action |
|---|---|
| No technical design / data model found | Offer to run `technical-design` + `data-model`, or have the architect describe the stack |
| A block's technology is unspecified | Ask the architect; if deferred, label the block `[TO CONFIRM]` — never guess |
| No stencil for a product (React, FastAPI, …) | Use a brand-colour labelled node per the reference; don't fetch external images |
| Too many components for one page | Group aggressively into tiers; collapse minor components into a labelled sub-box |
| No project folder connected | Ask the user to connect or point to it |

_Last reviewed: 2026-08-27_
