// Shared escape-hatch and state handling for the guardrails plugin's hooks.
//
// Three tiers of override, none of which requires editing this plugin or
// reinstalling the marketplace:
//
//   1. KZ_GUARDRAILS=off            per-machine / CI. Required for headless
//                                   `claude -p` runs, where a deny-loop is
//                                   unrecoverable because no human can answer.
//   2. ~/.claude/kaizen/<project-key>/guardrails.json
//                                   per-user, per-checkout (see project-key.js),
//                                   never inside the repo. A legacy
//                                   <repo>/.kaizen/guardrails.json is still read
//                                   when the user-level file doesn't exist:
//                                     enabled        false turns everything off
//                                     muted_until    ISO timestamp, temporary
//                                     allow_patterns regexes that always pass
//                                                    (how a team whitelists its
//                                                    own safe wrapper scripts —
//                                                    the one real answer to the
//                                                    `make migrate` blind spot)
//                                     extra_patterns regexes that always gate
//   3. The native permission dialog, which is the user's per-command override
//      and is better at that job than anything this plugin could add.
//
// Deliberately NOT offered: a per-command override token the model can emit.
// It would be indistinguishable from the model bypassing its own gate.
//
// Everything here fails open. A config file that is missing, unreadable, or
// malformed must never turn into a block.

"use strict";

const fs = require("fs");
const path = require("path");
const { kaizenDir, findFile } = require("./project-key");

function isDisabledByEnv() {
  const v = (process.env.KZ_GUARDRAILS || "").trim().toLowerCase();
  return v === "off" || v === "0" || v === "false" || v === "disabled";
}

function loadConfig(projectRoot) {
  const empty = { enabled: true, muted_until: null, allow_patterns: [], extra_patterns: [], source: null };
  try {
    const p = findFile(projectRoot, "guardrails.json");
    if (!p) return empty;
    const cfg = JSON.parse(fs.readFileSync(p, "utf8"));
    return {
      source: p,
      enabled: cfg.enabled !== false,
      muted_until: typeof cfg.muted_until === "string" ? cfg.muted_until : null,
      allow_patterns: Array.isArray(cfg.allow_patterns) ? cfg.allow_patterns : [],
      extra_patterns: Array.isArray(cfg.extra_patterns) ? cfg.extra_patterns : [],
    };
  } catch {
    return empty; // corrupt config is not this hook's problem to fix
  }
}

// Returns a reason string when the guardrails are currently off, else null.
function mutedReason(cfg) {
  if (isDisabledByEnv()) return "KZ_GUARDRAILS=off";
  if (!cfg.enabled) return `${cfg.source || "guardrails.json"} has enabled:false`;
  if (cfg.muted_until) {
    const until = Date.parse(cfg.muted_until);
    if (!Number.isNaN(until) && Date.now() < until) {
      return `muted until ${cfg.muted_until}`;
    }
  }
  return null;
}

function matchesAny(patterns, cmd) {
  for (const p of patterns) {
    try {
      if (new RegExp(p).test(cmd)) return p;
    } catch {
      // a malformed user regex is ignored, never fatal
    }
  }
  return null;
}

// Per-machine state, following the codebase-map precedent of keeping cache-ish
// state outside the repo. Used for the retry counter only, where a wrong count
// changes one sentence of wording and nothing else.
function stateDir(projectRoot) {
  return path.join(kaizenDir(projectRoot), "guardrails");
}

function readState(projectRoot, file) {
  try {
    const p = path.join(stateDir(projectRoot), file);
    if (!fs.existsSync(p)) return {};
    return JSON.parse(fs.readFileSync(p, "utf8")) || {};
  } catch {
    return {};
  }
}

function writeState(projectRoot, file, data) {
  try {
    const dir = stateDir(projectRoot);
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, file), JSON.stringify(data), "utf8");
  } catch {
    // never let a state write failure affect the exit path
  }
}

module.exports = {
  isDisabledByEnv,
  loadConfig,
  mutedReason,
  matchesAny,
  readState,
  writeState,
  stateDir,
};
