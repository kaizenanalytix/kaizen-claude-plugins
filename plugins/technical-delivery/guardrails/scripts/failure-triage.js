// PostToolUse hook (Bash): when a test/build/lint run fails, injects the triage
// contract before the model can react to it — quote the real output, label the
// explanation as a hypothesis, ask before changing code, and stop after two
// attempts on the same command.
//
// DETECTION IS CONJUNCTIVE, and that is what makes this shippable. Claude Code's
// Bash tool_response does not reliably expose an exit code, and NON-EMPTY STDERR
// IS NOT FAILURE — git, npm, pip, and pytest all write to stderr on success. A
// naive "stderr is non-empty -> triage" hook would fire constantly and train the
// model to ignore it, which is strictly worse than not shipping it at all. So
// both must hold: the command is a recognised runner, AND the output carries a
// real failure signature.
//
// Output uses exit 0 + hookSpecificOutput.additionalContext rather than exit 2 +
// stderr. A failing test is not a hook error and should not be framed as one, and
// an older Claude Code that doesn't know the JSON shape ignores it and exits 0 —
// degrading to a silent no-op instead of misbehaving.

"use strict";

const fs = require("fs");
const crypto = require("crypto");
const { isTestRunner } = require("./lib/classify");
const { loadConfig, mutedReason, readState, writeState } = require("./lib/config");

const STATE_FILE = "attempts.json";
const DAY_MS = 24 * 60 * 60 * 1000;

const FAILURE_SIGNATURE =
  /(\b\d+\s+failed\b|\bFAILED\b|\bFAIL\b|Tests?\s+failed|AssertionError|error\s+TS\d+|BUILD\s+FAILURE|BUILD\s+FAILED|npm\s+ERR!|Traceback\s+\(most\s+recent\s+call\s+last\)|\bexit\s+code\s+[1-9]|✗|✘|\b\d+\s+error(s)?\b|error\[E\d+\]|FAILURES!)/;

function quiet() {
  process.exit(0);
}

function inject(text) {
  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: "PostToolUse",
        additionalContext: text,
      },
    })
  );
  process.exit(0);
}

// tool_response is a string on some versions and {stdout, stderr, ...} on others.
function outputOf(resp) {
  if (typeof resp === "string") return resp;
  if (resp && typeof resp === "object") {
    return [resp.stdout, resp.stderr, resp.output, resp.error]
      .filter((s) => typeof s === "string")
      .join("\n");
  }
  return "";
}

function bumpAttempts(projectRoot, sessionId, cmd) {
  const key = `${sessionId}:${crypto.createHash("sha256").update(cmd.replace(/\s+/g, " ").trim()).digest("hex").slice(0, 16)}`;
  const now = Date.now();
  const state = readState(projectRoot, STATE_FILE);

  // prune anything older than a day so this file never grows without bound
  for (const k of Object.keys(state)) {
    if (!state[k] || typeof state[k].ts !== "number" || now - state[k].ts > DAY_MS) {
      delete state[k];
    }
  }

  const n = ((state[key] && state[key].n) || 0) + 1;
  state[key] = { n, ts: now };
  writeState(projectRoot, STATE_FILE, state);
  return n;
}

function message(cmd, n) {
  const head = cmd.length > 60 ? cmd.slice(0, 60) + "…" : cmd;

  const base = `guardrails/failure-triage: \`${head}\` failed (attempt ${n} this session).

Before you change ANY code:

1. QUOTE THE ACTUAL OUTPUT. Paste the real failing lines — the assertion, the stack
   frame, the type error — verbatim. Do not paraphrase, do not summarise the error away.
2. LABEL YOUR EXPLANATION AS A HYPOTHESIS, not a finding. Write "I think X is the cause",
   and list the other candidates you considered. Do not assume the code is what is wrong:
   the test, the fixture, the environment, or your own earlier edit in this session are
   equally likely, and the last one is the most often overlooked.
3. STATE THE PROPOSED CHANGE and what it would prove if it works.
4. ASK: "This is the output, and I'm assuming <hypothesis> — shall I go ahead and make
   that change?" Then STOP and wait.

Do not silently fix and re-run. Do not loosen an assertion, add a wait, skip the test,
or widen a type to make this pass.`;

  if (n < 3) return base;

  return (
    base +
    `

*** THIS IS ATTEMPT ${n} ON THE SAME COMMAND. Stop trying variations. Report all
attempts side by side — what you changed each time and what the output was each
time — say plainly what you have now RULED OUT, say that you do not know the
cause, and ask the user how to proceed. Do not run this command again until they
answer. ***`
  );
}

try {
  const input = JSON.parse(fs.readFileSync(0, "utf8"));
  if (input.tool_name !== "Bash" && input.tool_name !== "PowerShell") quiet();

  const cmd = (input.tool_input && input.tool_input.command) || "";
  if (!cmd.trim()) quiet();

  const projectRoot = input.cwd || process.cwd();
  if (mutedReason(loadConfig(projectRoot))) quiet();

  // Both conditions must hold — see the header comment.
  if (!isTestRunner(cmd)) quiet();
  const out = outputOf(input.tool_response);
  if (!out || !FAILURE_SIGNATURE.test(out)) quiet();

  inject(message(cmd, bumpAttempts(projectRoot, input.session_id || "session", cmd)));
} catch {
  quiet();
}
