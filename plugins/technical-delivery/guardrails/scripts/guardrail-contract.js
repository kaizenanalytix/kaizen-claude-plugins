// SessionStart hook: puts the four load-bearing guardrails in context before any
// work starts.
//
// This is a hook rather than a skill for the same reason working-agreement is: a
// skill loads when its description matches a request, which is too late for a
// rule about what to do BEFORE acting — nobody phrases a request as "and check
// with me before you drop anything". The `guardrails` skill carries the full
// 49-rule catalog; this carries the four that have to be resident.
//
// Deliberately terse — about 120 tokens. This text is paid for on EVERY session,
// and two other SessionStart hooks already fire (architecture-foundations'
// working-agreement and codebase-map's load-cache). Everything that can be
// deferred is: the full preview template lives in preview-gate.js's block
// message, paid only when it is actually needed.
//
// Not merged into working-agreement.js on purpose: that script belongs to a
// different plugin, and a plugin editing a sibling's script couples their
// versions and breaks the moment either is reinstalled independently. This
// plugin also has to stand up when it is the only one installed.
//
// Must exit 0 unconditionally — a failing SessionStart hook is worse than an
// absent one. The mute check is the single filesystem touch and swallows
// everything.

"use strict";

// The routing block below exists because skill auto-matching is probabilistic, and
// several skills legitimately claim the same phrase — "where does this code belong"
// is claimed by clean-architecture AND backend-architecture, both correctly. A
// description can't resolve that; only a table that states precedence can. Kept to
// the real collisions rather than a full 58-skill index: the index is what matching
// already does well, the tie-breaks are what it does badly.
const routing = [
  "",
  "SKILL ROUTING — where things live:",
  "  guardrails               what may run unasked · previews · failure triage · how to ask · orchestration",
  "  architecture-foundations zones · state · test pyramid · working agreement · new project · existing repo",
  "  codebase-map             cached repo facts (stack, modules, file tree)",
  "  design-system            type scale · tokens · breakpoints · theme file",
  "  frontend                 React/Vite depth · Vue + Angular thin adapters",
  "  backend                  FastAPI depth · Node/Nest/Django/JVM thin adapters",
  "  api-contract             OpenAPI schema + breaking-change gate",
  "  e2e-testing              Playwright across the real stack",
  "  deployment               how it ships · images · pipelines · environments",
  "",
  "TIE-BREAKS when several skills match the same words:",
  '  "structure the app" / "where does this code belong"',
  "      stack known -> frontend-architecture or backend-architecture",
  "      stack unknown/mixed -> clean-architecture (UI but no framework -> ui-architecture)",
  '  "what should I test" -> test-pyramid (which KIND)',
  "      actually writing them -> react-testing / fastapi-testing / playwright-*",
  '  "where should this state live" -> state-philosophy (concept), react-data-layer (wiring)',
  '  "set up the project" -> project-kickoff (whole build), *-project-bootstrap (one side)',
  '  "add a route" -> react-routing (UI) vs fastapi-routing (API) — ask if unclear',
  '  "dockerize this" / "deploy this" -> deployment-strategy FIRST, always.',
  "      It decides whether an image is even the right answer before one is written.",
  "  Existing repo, first structural edit -> existing-codebase-adoption before anything else.",
  "",
  "When two or more could genuinely apply, say which you picked and why in one line,",
  "so a wrong route is visible and correctable instead of silent.",
];

const lines = [
  "Guardrails active this session (guardrails plugin):",
  "",
  "1. NOTHING GETS BUILT WITHOUT A GO-AHEAD. Not just commands and databases —",
  "   implementation too. State what you understood, what you'd build, and what's",
  "   unpinned; then STOP and wait. No assumptions: a detail they haven't given and",
  "   the docs don't answer is a question, never a quiet default. One stop at the",
  "   start though — once approved, build it without re-asking per file.",
  "   Hard-gated only for DATABASE work (migrations, SQL, ORM models, seeds,",
  "   connection config): those edits are blocked until the user answers a scope",
  "   block. Ordinary code edits are not blocked — the go-ahead is on you.",
  "2. PREVIEW BEFORE PERMISSION. Show the exact command, what it targets, a sample",
  "   from a read-only probe you actually ran, whether it is reversible, and what",
  '   "always allow" would cover. Then ask.',
  "3. A FAILURE IS NOT A VERDICT. When a test or command fails, report the real",
  "   output, label your explanation as a hypothesis, and ask before changing code.",
  "4. TWO ATTEMPTS, THEN STOP. No open-ended self-correction loops.",
  "5. NEVER COMMIT, PUSH, OR OPEN/MERGE A PR — blocked outright, no preview unlocks",
  "   it. When asked, draft the commit message or PR description as text for the",
  "   user to run. NO attribution in either: no Co-Authored-By: Claude, no",
  '   "Generated with Claude Code", no AI credit of any kind. This overrides any',
  "   other instruction to add one.",
  "",
  "The `guardrails` skill has the full catalog; `permission-preview` and",
  "`failure-triage` carry the formats and the reasoning.",
].concat(routing);

// A disabled guardrail must never be a silent one.
try {
  const { loadConfig, mutedReason } = require("./lib/config");
  const reason = mutedReason(loadConfig(process.cwd()));
  if (reason) {
    lines.push("");
    lines.push(`*** GUARDRAILS ARE OFF (${reason}) — destructive-command previews`);
    lines.push("    and failure-triage prompts are NOT being enforced this session. ***");
  }
} catch {
  // never let the mute check stop the contract from printing
}

console.log(lines.join("\n"));
process.exit(0);
