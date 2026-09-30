// PreToolUse hook (Agent|Task): blocks a sub-agent dispatch that declares no
// acceptance criteria.
//
// HONEST LIMITATION, STATED UP FRONT. This matches on the SHAPE OF PROSE inside a
// prompt, which is exactly the kind of check that is fragile and that this plugin
// otherwise argues against. It cannot tell a good criterion from a bad one — only
// that the dispatch says "done when" somewhere. A lazy dispatch that writes
// "DONE WHEN: it works" satisfies it. What it genuinely catches is the common
// failure: firing an agent at a vague brief with no definition of done at all, so
// nothing can be verified when it returns (O4) and a plausible summary passes for
// completed work.
//
// It is therefore tuned to be nearly false-positive-free rather than thorough:
//   * short prompts pass untouched — a quick lookup is not a work dispatch
//   * ANY of several criteria markers satisfies it, not a specific heading
//   * everything ambiguous fails open
// A gate that blocks a legitimate dispatch is worse than one that misses a sloppy
// one, because the first makes people disable the plugin.

"use strict";

const fs = require("fs");
const { loadConfig, mutedReason } = require("./lib/config");

// Below this, it isn't a work dispatch — it's a lookup, a question, a one-liner.
const SUBSTANTIAL = 400;

// Any ONE of these means the dispatch declared what "done" means.
const CRITERIA_MARKERS = [
  "DONE WHEN",
  "ACCEPTANCE CRITERIA",
  "SUCCESS CRITERIA",
  "CRITERIA:",
  "MUST SATISFY",
  "COMPLETE WHEN",
  "VERIFY THAT",
  "DEFINITION OF DONE",
];

// Read-only reconnaissance genuinely has no "done when" — the deliverable is
// whatever it finds, and demanding criteria there would be noise.
const RECON_AGENT_TYPES = ["explore", "plan", "general-purpose-readonly"];
const RECON_HINT =
  /\b(search for|find (?:all|every|where)|locate|explore|investigate|look for|report back on|summarise|summarize|read through|survey)\b/i;

function allow() {
  process.exit(0);
}

const MESSAGE = `BLOCKED — guardrails/agent-dispatch-gate: this dispatch declares no acceptance
criteria, so nothing will be able to verify what comes back.

Every dispatch carries four things (O2). The one missing here is the second:

  1 RESOLVED ANSWERS   every decision already made, verbatim — the sub-agent has
                       none of this conversation and cannot ask you (O1)
  2 DONE WHEN          <-- MISSING. State it checkably. "Implements the module"
                       is not checkable; "InvoiceRepository declared in domain/,
                       implemented in infra/, router mounted at /api/v1/invoices"
                       is.
  3 RETURN SHAPE       what the summary must contain — files, decisions, anything
                       it could not do. Say "short summary, not your reasoning."
  4 CONSTRAINTS        what not to touch, what not to create, no user-facing
                       decisions, no new dependencies

Add a DONE WHEN section and re-dispatch. If you cannot say what done looks like,
the subtask is not ready to dispatch — that is the rule working, not the rule
getting in the way.

Also check O10: pass this agent only its predecessors' handover packets — what they
export and what they decided — not the accumulated conversation.`;

try {
  const input = JSON.parse(fs.readFileSync(0, "utf8"));

  const tool = input.tool_name || "";
  if (tool !== "Agent" && tool !== "Task") allow();

  const ti = input.tool_input || {};
  const prompt = typeof ti.prompt === "string" ? ti.prompt : "";
  if (!prompt || prompt.length < SUBSTANTIAL) allow();

  if (mutedReason(loadConfig(input.cwd || process.cwd()))) allow();

  // Read-only recon agents have no meaningful "done when".
  const at = String(ti.subagent_type || ti.agentType || "").toLowerCase();
  if (RECON_AGENT_TYPES.includes(at)) allow();
  if (RECON_HINT.test(prompt.slice(0, 300))) allow();

  const upper = prompt.toUpperCase();
  if (CRITERIA_MARKERS.some((m) => upper.includes(m))) allow();

  process.stderr.write(MESSAGE + "\n");
  process.exit(2);
} catch {
  allow(); // a gate that misfires closed is worse than no gate at all
}
