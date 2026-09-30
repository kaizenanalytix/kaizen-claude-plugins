---
name: api-sequence-diagram
description: >
  Use this skill when an Architect, Tech Lead, or Backend engineer wants an API flow SEQUENCE
  diagram for an engagement — the ordered request/response interactions between the caller, the
  API surface, internal services, data stores, auth, and external systems for one API flow.
  Trigger on: "api sequence diagram", "sequence diagram", "api flow diagram", "request flow",
  "call flow", "draw the api sequence", "interaction diagram", "how the api calls flow",
  "sequence of calls for a flow". Reads the API specification / integration / technical design
  documents (or a flow the user describes), and produces a UML-style sequence diagram as an
  editable draw.io (.drawio) file saved to a `diagrams/` folder.
---

# api-sequence-diagram Skill

Produce a clean, editable **UML sequence diagram** of an API flow as a **draw.io (`.drawio`)
file**. One diagram per meaningful API flow (e.g. "Create Order", "Authenticate & Issue Token",
"Generate Report"), showing the participants as lifelines and the ordered messages between them —
requests, responses, auth, validation, error/alternate paths, and loops.

You author the `.drawio` XML directly (see `references/drawio-sequence.md` for the exact node and
edge patterns). No external renderer is required — the file opens in draw.io / diagrams.net.

> **Guardrails:** Before writing any file, show the proposed path and get the user's confirmation.
> Never overwrite an existing file — if the target name already exists, save a new version (append
> " v2", " v3", …). Keep any figures from the source documents verbatim; do not invent endpoints,
> status codes, or auth mechanisms that aren't in the sources — mark unknowns `[TO CONFIRM]`.

---

## Step 0 — Locate the working folder

Find the connected/working **project folder**. If none is connected, ask the user to connect or
point to it. Diagrams are written to a `diagrams/` subfolder under it (create it if missing).

## Step 1 — Gather the API interactions

Search the project folder for the documents that describe the API behaviour, and read whatever
exists (ask the user to point at the file(s) if nothing is found):

| Source | What to pull |
|---|---|
| API / Interface Specification | endpoints, verbs, request/response payloads, status codes, auth |
| Integration Design | external system calls, protocols, retries, error handling |
| Technical Design (Back-end / Overview) | services/modules, internal call chain, data stores |
| Business Requirements | the functional flow the API serves |
| Anything the user describes in chat | the flow to diagram, in their own words |

If the sources don't fully specify a step, keep going and mark the gap `[TO CONFIRM]` on the
message label — never invent an endpoint, payload, or status code.

## Step 2 — Identify participants and the message sequence

For each flow, work out:

1. **Participants (lifelines), left → right in call order** — typically: the caller/actor (user,
   client app, or upstream system) · the API surface (gateway / API / controller) · the
   auth service (if any) · the internal service(s) / business logic · the data store(s) · any
   external API. One lifeline per distinct participant; don't split one service into many.
2. **The ordered messages** top → bottom:
   - **Synchronous call** — solid arrow with a filled head, labelled `verb /path` or
     `operation(args)` (e.g. `POST /orders`, `validateToken(jwt)`).
   - **Return / response** — dashed arrow with an open head, labelled with what comes back
     (e.g. `201 Created {orderId}`, `200 OK`, `rows[]`).
   - **Self-call** — a message a participant sends to itself (e.g. `validate payload`).
   - **Async / fire-and-forget** — dashed arrow (e.g. publish to a queue); label it as async.
3. **Structured fragments** where they exist — an **alt** frame for success vs. error branches, a
   **loop** frame for retries/pagination, an **opt** frame for optional steps. Represent these as
   labelled frames (see the reference).
4. **Auth first** — if the flow authenticates, show the token/credential check before the business
   messages.

## Step 3 — Confirm the flow list

List the flow(s) you'll diagram and the participants for each, and confirm with the user before
drawing (one diagram per flow):

```
I'll produce these API sequence diagrams:
  1. <Flow name> — participants: Client → API → Auth → OrderService → PostgreSQL
  2. <Flow name> — participants: …
Reply "go", or tell me which flows to add/drop.
```

## Step 4 — Author the draw.io sequence diagram

Read `references/drawio-sequence.md` and build the `.drawio` XML directly, following those
patterns. Conventions:

- **Lifelines** across the top, evenly spaced; the caller on the left, the deepest dependency
  (data store / external API) on the right. Each lifeline has a header box + a dashed lifeline
  running down the page.
- **Activation bars** (thin rectangles on the lifeline) span the time a participant is handling a
  call — optional but preferred for readability.
- **Every message is labelled.** Solid+filled = synchronous call; dashed+open = return.
- **Time flows top → bottom**; messages never go backwards up the page.
- **Kaizen styling** — lifeline headers in Kaizen blue `#002F6C` on light `#E7EEF6`; black message
  arrows; a titled frame at the top with the flow name; keep it legible (label font ≥ 11).
- **Frames** (`alt` / `loop` / `opt`) drawn as a labelled rectangle enclosing the messages they
  govern, with the guard condition in `[brackets]`.

Produce one diagram (one `.drawio` file) per flow, or lay several flows on separate pages of one
`.drawio` if the user prefers a single file.

## Step 5 — Self-review

Before saving, check the diagram against this checklist and fix anything that fails:

- [ ] Every participant that appears in a message has its own lifeline.
- [ ] Every message (call and return) carries a label; no bare arrows.
- [ ] Calls are solid/filled; returns are dashed/open; async is dashed and marked.
- [ ] The sequence reads strictly top → bottom; no upward messages.
- [ ] Auth/validation appears before the business steps it protects.
- [ ] Error / alternate / loop behaviour is shown as a labelled frame where the sources call for it.
- [ ] Nothing overlaps or is clipped; lifelines are long enough for all messages.
- [ ] `[TO CONFIRM]` marks every gap the sources didn't specify.

## Step 6 — Present & save

Show a short summary (flows, participants per flow, message count, any `[TO CONFIRM]` items) and
the proposed path(s), e.g. `diagrams/<Flow name> - API Sequence.drawio`. On confirmation, write the
file(s) (versioning instead of overwriting) and share them with the user.

```
✅ API sequence diagram(s) generated in "diagrams/":
   • <Flow name> - API Sequence.drawio  (participants: N, messages: N)

Items to confirm:
  • [list any [TO CONFIRM] labels]
```

---

## Error handling

| Situation | Action |
|---|---|
| No API/integration/design docs found | Ask the user to describe the flow, or point at the API spec |
| A step's endpoint/payload/status is unspecified | Draw it and label the gap `[TO CONFIRM]` — never invent it |
| Many flows in scope | Confirm the list in Step 3; produce one diagram per flow |
| Flow has complex branching | Use `alt` / `opt` / `loop` frames rather than crossing arrows |
| No project folder connected | Ask the user to connect or point to it |

_Last reviewed: 2026-08-27_
