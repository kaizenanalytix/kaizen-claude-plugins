# The team model: a lead, a work graph, and a review loop

How a multi-agent build actually runs — the lead that owns the graph, specialist agents that each
see only their slice, the handover packet that moves between them, and the verify loop that closes
before anything is called done.

---

## The constraint that shapes everything

**Sub-agents cannot talk to each other.** They are spawned, they run, they return to whoever
spawned them. There is no peer channel, no shared scratchpad they can converse through.

So "the team interacts" has exactly one true meaning here: **the lead is the message bus.** Agent A
finishes, hands a packet to the lead, and the lead decides what of that packet Agent B needs. Every
edge in the graph passes through the lead.

That is not a limitation to work around — it is what keeps contexts small. If agents could talk
freely they would accumulate each other's noise, which is the exact failure the split exists to
prevent.

---

## Why the Workflow tool rather than hand-rolled Agent calls

Deterministic control flow. Loops, conditionals, and fan-out belong in a script, not in a model's
judgement about what to dispatch next. Specifically:

| Need | What provides it |
|---|---|
| The handover packet | `schema` on `agent()` — forces structured output, validated at the tool-call layer, so the model retries on mismatch rather than returning prose you have to parse |
| Memoisation (O6) | `resumeFromRunId` — the longest unchanged prefix of `agent()` calls returns cached results instantly; only edited or new calls re-run |
| Parallel implementers that write files | `isolation: 'worktree'` — each agent gets its own git worktree, so two agents writing at once don't corrupt each other |
| Bounded retry (O5) | A plain `for` loop in the script |
| Scaling to the ask | `budget.remaining()` |

**It requires explicit opt-in on every run.** That is a real cost and worth stating plainly: you
cannot make this the silent default, and you shouldn't want to.

---

## The two shapes, and which to use

`pipeline()` is the default. It runs each item through all stages **with no barrier** — item A can
be in review while item B is still being implemented. Wall-clock is the slowest single chain, not
the sum of slowest-per-stage.

`parallel()` is a **barrier** — it waits for everything. It is correct only when the next step
genuinely needs all prior results together.

**A dependency graph is the one place a barrier is genuinely right**, because computing the next
ready-set requires knowing which nodes finished. So: `parallel()` per wave, `pipeline()` for
everything inside a wave that doesn't interlock.

---

## The handover packet

Every node returns the same shape. This is what the lead passes onward — never the whole history.

```js
const HANDOVER = {
  type: 'object',
  properties: {
    node:         { type: 'string' },
    filesWritten: { type: 'array', items: { type: 'string' } },
    exports:      { type: 'array', items: { type: 'string' },
                    description: 'symbols, routes, or types dependents may rely on' },
    decisions:    { type: 'array', items: { type: 'string' },
                    description: 'choices made that a dependent must not contradict' },
    blocked:      { type: 'array', items: { type: 'string' },
                    description: 'anything it could not do, and why' },
  },
  required: ['node', 'filesWritten', 'exports', 'blocked'],
}
```

`exports` and `decisions` are the load-bearing fields. A dependent node needs to know *what it can
import* and *what it must not contradict* — and almost nothing else. Handing it the predecessor's
full reasoning is how contexts quietly grow back to the size the split was meant to avoid.

`blocked` exists so a node can fail honestly instead of inventing a way through. An empty `blocked`
from an agent that clearly hit a wall is worse than a populated one.

---

## The review verdict

Every node is reviewed by a **different agent** than the one that built it. An implementer
summarising its own work is evidence, not proof.

```js
const VERDICT = {
  type: 'object',
  properties: {
    node:          { type: 'string' },
    meetsCriteria: { type: 'boolean' },
    violations:    { type: 'array', items: { type: 'string' } },
    mustFix:       { type: 'array', items: { type: 'string' } },
  },
  required: ['node', 'meetsCriteria', 'violations'],
}
```

The reviewer is given the node's **acceptance criteria and the packet** — not the implementer's
prompt. Give it the prompt and it grades the intent rather than the result.

---

## The whole script

```js
export const meta = {
  name: 'build-feature',
  description: 'Implement a feature across a dependency graph, reviewing every node',
  phases: [
    { title: 'Implement', detail: 'one agent per ready node, isolated worktrees' },
    { title: 'Review',    detail: 'an independent reviewer per node' },
  ],
}

// --- the graph: nodes and what they depend on ---------------------------------
const GRAPH = [
  { id: 'contract', deps: [],
    brief: 'Add Invoice + InvoiceCreate schemas to the OpenAPI contract.',
    criteria: 'openapi.json validates; Invoice has id, amount_cents, status, issued_at; no existing field changed type' },
  { id: 'backend', deps: ['contract'],
    brief: 'Implement modules/invoices/ — domain interface, service, SQLAlchemy repo, router.',
    criteria: 'InvoiceRepository declared in domain/, implemented in infra/; router mounted at /api/v1/invoices; no SQL outside infra/' },
  { id: 'frontend', deps: ['contract'],
    brief: 'Implement modules/invoices/ — RTK Query slice, table page, lazy guarded route.',
    criteria: 'types imported from the generated contract types, never redeclared; server state in the query cache; no filter state in Redux' },
  { id: 'e2e', deps: ['backend', 'frontend'],
    brief: 'One Playwright spec: create an invoice, assert it persisted and renders.',
    criteria: 'asserts the DB row, not just the toast; unique per-test data; no fixed waits' },
]

// --- prompts: each agent sees ONLY its brief and its predecessors' packets -----
function implementPrompt(node, inbound, lastVerdict) {
  return [
    `You are implementing ONE node of a larger build: "${node.id}".`,
    ``,
    `BRIEF`,
    node.brief,
    ``,
    `DONE WHEN`,
    node.criteria,
    ``,
    `WHAT UPSTREAM NODES PRODUCED (this is all you get — do not go looking for more):`,
    inbound.length
      ? inbound.map(p =>
          `  ${p.node}\n    exports:   ${p.exports.join(', ') || '(none)'}\n` +
          `    decisions: ${p.decisions?.join('; ') || '(none)'}`).join('\n')
      : '  (nothing — this node starts the graph)',
    ``,
    lastVerdict
      ? `A previous attempt FAILED review. Fix exactly this and nothing else:\n  ` +
        lastVerdict.mustFix.join('\n  ')
      : '',
    ``,
    `CONSTRAINTS`,
    `- Make no user-facing decisions. Everything you need is above; if it genuinely`,
    `  is not, put it in "blocked" and stop rather than inventing it.`,
    `- Touch only files belonging to this node.`,
    `- Never create .claude/, .claude/settings.json, or CLAUDE.md.`,
    `- Install no dependencies.`,
    `Return the handover packet. Short — files, exports, decisions, blocked. Not your reasoning.`,
  ].join('\n')
}

function reviewPrompt(node, packet) {
  return [
    `Review ONE node against its acceptance criteria. You did not write this code.`,
    ``,
    `NODE      ${node.id}`,
    `DONE WHEN ${node.criteria}`,
    ``,
    `CLAIMED`,
    `  files:   ${packet.filesWritten.join(', ')}`,
    `  exports: ${packet.exports.join(', ')}`,
    `  blocked: ${packet.blocked.join('; ') || '(nothing)'}`,
    ``,
    `READ THE FILES. The packet is a claim, not proof — a well-written summary of`,
    `work that was not done is the failure mode here.`,
    `Set meetsCriteria=false if any criterion is unmet, and put the minimal fix in`,
    `mustFix. Do not fix it yourself.`,
  ].join('\n')
}

// --- one node: implement -> review -> bounded retry ---------------------------
async function buildNode(node, done) {
  const inbound = node.deps.map(d => done[d]).filter(Boolean)
  let verdict = null

  for (let attempt = 1; attempt <= 2; attempt++) {
    const packet = await agent(implementPrompt(node, inbound, verdict), {
      label: `build:${node.id}${attempt > 1 ? ` (retry ${attempt})` : ''}`,
      phase: 'Implement',
      schema: HANDOVER,
      isolation: 'worktree',   // these run concurrently and write files
    })
    if (!packet) return { node, failed: true, why: 'implementer returned nothing' }

    verdict = await agent(reviewPrompt(node, packet), {
      label: `review:${node.id}`,
      phase: 'Review',
      schema: VERDICT,
    })
    if (!verdict) return { node, packet, failed: true, why: 'reviewer returned nothing' }
    if (verdict.meetsCriteria) return { node, packet, verdict, attempts: attempt }

    log(`${node.id}: review failed (attempt ${attempt}) — ${verdict.violations.join('; ')}`)
  }
  return { node, verdict, failed: true, why: 'failed review twice' }
}

// --- the lead: walk the graph wave by wave ------------------------------------
const done = {}
const pending = new Set(GRAPH.map(n => n.id))
const failures = []

while (pending.size) {
  const ready = GRAPH.filter(n => pending.has(n.id) && n.deps.every(d => done[d]))

  if (!ready.length) {
    // Everything left depends on something that failed. Say so; don't spin.
    log(`STOPPED — ${[...pending].join(', ')} cannot start; upstream nodes failed.`)
    break
  }

  log(`wave: ${ready.map(n => n.id).join(', ')}`)
  const results = await parallel(ready.map(n => () => buildNode(n, done)))

  for (const r of results.filter(Boolean)) {
    pending.delete(r.node.id)
    if (r.failed) failures.push(r)
    else done[r.node.id] = r.packet
  }
  // A node that returned null (skipped or died) stays pending and the next
  // iteration finds no progress — caught by the no-ready check above.
}

return {
  completed: Object.keys(done),
  failed: failures.map(f => ({ node: f.node.id, why: f.why, mustFix: f.verdict?.mustFix ?? [] })),
  neverStarted: [...pending],
}
```

---

## What the lead does with the result

**Not** "report success". The lead's job after the graph drains:

1. **Say what completed, what failed, and what never started.** `neverStarted` is the one people
   forget, and it's the most misleading thing to omit — those nodes aren't broken, they were never
   attempted, and silence reads as coverage.
2. **Never fabricate a packet for a node that returned nothing** (O3). A `null` is a failure.
3. **Ask before re-dispatching** (O5). Report what failed and what you'd change in the retry — a
   sharper criterion, a smaller node, more inbound context. "Run it again" is not a change.
4. **Verify the seams the graph didn't.** Each node was reviewed against *its own* criteria;
   nothing checked that backend and frontend agree. That's the lead's own work, or another node.

---

## Sizing

| Ask | Shape |
|---|---|
| One module, clear brief | Don't orchestrate. One agent, or just do it. |
| A feature across 3–5 areas | This graph, ~8–10 agents with review |
| A migration across many files | `pipeline()` over the file list, plus O9's pilot-first rule |
| An audit with unknown extent | Loop-until-dry: keep spawning finders until K rounds return nothing new |

**The overhead is real.** The graph, the schemas, the prompts, the review pass. Don't pay it for
work that fits in one context — a chain of one-agent hops is just a slower single agent.

---

_Last reviewed: 2026-09-18_
