// UserPromptSubmit hook: makes every non-trivial request open with a scoped work
// list instead of going straight to doing.
//
// WHY THIS IS A HOOK AND NOT A RULE IN A SKILL. A skill loads only when its
// description matches what the user said — which is exactly the reliability problem
// this is meant to fix. "Whatever the user asks, first say what you'd work on" can
// never be triggered by matching, because it has to apply to requests that match
// nothing. UserPromptSubmit is the only event that fires on every message
// regardless of content.
//
// COST DISCIPLINE. This text is paid on EVERY non-trivial prompt, so it defers
// everything it can to the SessionStart contract, which is paid once. If it grows
// much past ~200 tokens, move the growth there.
//
// IT IS A GATE, NOT A PREAMBLE. The block is presented and then the turn STOPS.
// An earlier version said "then proceed if it's clear" — which made it a report,
// not a gate, since "it seemed clear to me" is precisely the state in which a
// misread premise gets built on. A plan costs one message; rebuilding a feature
// built on the wrong premise costs the feature.
//
// It also deliberately does NOT fire on short/trivial prompts. A scope block on
// "what does D3 mean" is noise, and noise is how a standing instruction gets
// trained out of usefulness — the user starts skipping past it, and then it is not
// there for the request that needed it.
//
// Output: exit 0 with hookSpecificOutput.additionalContext. An older Claude Code
// ignores the unknown shape and exits 0, so this degrades to a silent no-op.

"use strict";

const fs = require("fs");

function quiet() {
  process.exit(0);
}

// Any of these means the user is asking for something to be BUILT, however short
// the prompt. "add a route" is eleven characters and still needs a go-ahead, so the
// length shortcut below must never swallow one of these.
const IMPLEMENTATION_VERB =
  /\b(build|implement|add|create|write|make|refactor|migrate|fix|set ?up|deploy|delete|drop|remove|rename|update|change|wire|scaffold|generate|install|configure|convert|port|extract|split|merge)\b/i;

// Phrasings that ASK TO BE TOLD something. These alone do not decide it — a recall
// opener can still front a real deliverable ("give me an artifact of...") — so both
// guards below must also disagree before it counts as trivial.
const RECALL =
  /^(give me|list|show|tell me|what (is|are|does|do|was|were)|what's|which|who|when|where|why|how (many|much|does|do|did)|can you (list|show|tell|explain|describe)|explain|describe|remind me|summari[sz]e)\b/i;

// Guard 1 — a THING THAT GETS PRODUCED. "give me an artifact" is recall phrasing
// wrapped around a real deliverable. Deliberately excludes words this system talks
// ABOUT rather than makes (hook, plugin, skill, rule), or "how many hooks are
// there" would read as a build request.
const DELIVERABLE =
  /\b(artifact|document|doc|page|report|deck|slide|diagram|spec|plan|file|files|script|mockup|wireframe|dashboard|chart|readme)\b/i;

// Guard 2 — a verb used as an ACTION rather than sitting inside a noun phrase.
// IMPLEMENTATION_VERB alone cannot tell "explain how the WRITE GATE works" from
// "write the tests": both contain "write". A preposition in front of it, or a
// gerund ending, is the signal that something is meant to be DONE.
const ACTION_PHRASE =
  /\b(?:to|by|then|and|also|please)\s+(?:add|creat|build|writ|mak|fix|updat|chang|remov|renam|implement|generat|install|refactor|migrat|scaffold|wir|deploy)\w*|\b(?:add|creat|build|writ|mak|fix|updat|chang|remov|renam|implement|generat|install|refactor|migrat|scaffold|wir|deploy)ing\b/i;

// Prompts that plainly don't need a plan. Kept deliberately narrow — when in doubt
// the block is cheap and the missing plan is not.
function isTrivial(prompt) {
  const p = prompt.trim();

  // Very short asks: a lookup, an acknowledgement, a one-word follow-up. All three
  // signals have to agree it is not work — the verb list alone misses "give me an
  // artifact" (52 chars, no verb, definitely a deliverable) and "show me by adding
  // a route" (46 chars, "adding" is not \badd\b).
  if (
    p.length < 60 &&
    !IMPLEMENTATION_VERB.test(p) &&
    !DELIVERABLE.test(p) &&
    !ACTION_PHRASE.test(p)
  ) {
    return true;
  }

  // Asking to be TOLD something is not asking for something to be BUILT. "give me
  // the list", "show me the rules", "what are the guardrails" produce an answer, not
  // a deliverable — and a scope block on those is the noise that trains people to
  // skip the block entirely. Guarded by the implementation-verb check so "list the
  // files you'd create" still gates.
  if (RECALL.test(p) && !DELIVERABLE.test(p) && !ACTION_PHRASE.test(p) && p.length < 180) {
    return true;
  }

  // Pure acknowledgements and continuations.
  if (/^(yes|no|yep|nope|ok|okay|sure|thanks|ty|go ahead|do it|proceed|continue|stop|wait|nvm|never ?mind)\b/i.test(p)) {
    return true;
  }


  return false;
}

// A request that sweeps across many files gets one extra line, because that is the
// case where a wrong pattern is cheapest to catch and most expensive to miss — the
// difference between one wrong file and fifty. Appended only when it applies, so the
// ordinary prompt pays nothing for it.
const BULK_SHAPED =
  /\b(all|every|each|everywhere|across|bulk|batch|throughout|whole (?:repo|codebase|project)|entire)\b/i;

const BULK_NOTE = `

This looks like it sweeps across many files. Stage it (O9): apply the change to
ONE file first, show the real diff, and confirm the pattern before the rest —
then proceed in visible batches grouped by something meaningful (by module, by
kind of change), not arbitrary chunks. Writing a script does not exempt this;
a script enlarges the blast radius, it does not shrink the review.`;

const TEXT = `guardrails/scope-first: do NOT start building. Reply with this block, then STOP.

  WHAT I UNDERSTAND   one line, restating the ask in your own words
  WHAT I'D BUILD      the concrete items, in order
  NOT DOING           what you're deliberately leaving out
  UNPINNED            every detail the work depends on that they haven't
                      specified and the repo's docs don't answer — name the
                      default you'd take, but do NOT take it yet
  SKILLS              which skill/plugin applies, if more than one could

Then ask whether to go, and wait for their answer. This is a gate, not a
preamble: writing the block and implementing in the same turn defeats it.
"It seemed clear" is exactly when a misread premise gets built on — the plan
costs one message, the rebuild costs the feature.

Already approved in this conversation, or told to just do it? That IS the
go-ahead. Build the whole thing without re-asking — re-litigating approved
work is its own failure.`;

try {
  const input = JSON.parse(fs.readFileSync(0, "utf8"));
  const prompt = input.prompt || (input.user_prompt ?? "");
  if (typeof prompt !== "string" || !prompt.trim()) quiet();
  if (isTrivial(prompt)) quiet();

  // Respect the same escape hatches as every other hook in this plugin.
  const { loadConfig, mutedReason } = require("./lib/config");
  if (mutedReason(loadConfig(input.cwd || process.cwd()))) quiet();

  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: "UserPromptSubmit",
        additionalContext: BULK_SHAPED.test(prompt) ? TEXT + BULK_NOTE : TEXT,
      },
    })
  );
  process.exit(0);
} catch {
  quiet();
}
