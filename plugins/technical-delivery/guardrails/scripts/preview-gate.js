// PreToolUse hook (Bash|PowerShell): blocks a destructive or database-writing command
// until the user has actually been shown a preview of it — and blocks git commit /
// push / PR creation outright, with no preview path (see gitPublishMessage).
//
// THE LOAD-BEARING PROBLEM this solves: if the gate simply blocked, the model
// would preview, retry, and be blocked again forever. So the gate has to know a
// preview genuinely happened. Everything the model can write by itself — a state
// file, a sentinel in the command, a marker in the description — is an
// ATTESTATION it can satisfy inside the same turn without a human ever seeing
// anything. None of those prove a thing.
//
// What the model cannot fabricate is a user turn. So the gate reads the
// transcript and looks for: an assistant message containing the preview heading
// AND this command, followed by a REAL user turn, before this tool call. That
// property — "a human got a turn between seeing the exact command and it
// running" — is the only unforgeable signal available here.
//
// What this does NOT enforce: the QUALITY of the preview. The model can print the
// heading, three lines of nothing, and get a user turn. The guarantee is only
// that the user saw the command and had a chance to object. The
// `permission-preview` skill carries the quality bar; this carries the stop.
//
// Fails open on: KZ_GUARDRAILS=off, a muted/disabled project config, a matching
// allow_pattern, a read-only probe, an unclassifiable command, an unreadable or
// unrecognised transcript, a transcript with too few entries or no real user
// turns at all (post-compaction, headless `claude -p`, and sub-agents all land
// here — none of them have a human to preview to, and a deny-loop there is
// unrecoverable), and any script error.

"use strict";

const fs = require("fs");
const { classifyCommand } = require("./lib/classify");
const { loadConfig, mutedReason, matchesAny } = require("./lib/config");
const { textOf, roleOf, isRealUserTurn, readTail, norm } = require("./lib/transcript");

const PREVIEW_HEADING = "WHAT I WANT TO RUN";

function allow() {
  process.exit(0);
}

function block(message) {
  process.stderr.write(message + "\n");
  process.exit(2);
}

// true  -> a preview was shown and a real user turn followed
// false -> no such evidence; block
// null  -> cannot tell; fail open
function previewEvidence(transcriptPath, command) {
  const entries = readTail(transcriptPath, 200000);
  if (!entries) return null;

  // Too little recovered to reason about (fresh session, post-compaction).
  if (entries.length < 6) return null;

  // No human in this transcript at all: headless run or sub-agent. Blocking
  // there is unrecoverable, so fail open.
  const lastUser = entries.map(isRealUserTurn).lastIndexOf(true);
  if (lastUser === -1) return null;

  const needle = norm(command);
  const fragment = needle.length > 40 ? needle.slice(0, 40) : needle;

  for (let i = 0; i < lastUser; i++) {
    const e = entries[i];
    if (roleOf(e) !== "assistant") continue;
    const text = textOf(e);
    if (!text) continue;
    if (text.includes(PREVIEW_HEADING) && norm(text).includes(fragment)) {
      return true;
    }
  }
  return false;
}

// --------------------------------------------------------------------------
// Block messages — this text IS the guardrail
// --------------------------------------------------------------------------

function generalMessage(cmd, info, cwd) {
  return `BLOCKED — guardrails/preview-gate: this command is destructive or irreversible, and no
preview has been shown to the user yet.

  Command:   ${cmd}
  Class:     ${info.dangerClass}
  Matched:   ${info.matched}

Do NOT run it and do NOT work around it. Reply to the user with exactly this block, then
STOP and wait for their answer. Fill every field; if you cannot fill one, write "unknown"
— never guess and never invent a sample.

  ${PREVIEW_HEADING}
    <the command, verbatim, on one line>
  WHERE IT RUNS
    cwd: ${cwd}
    target: <host / cluster / registry / database / path this actually reaches,
             and where you read that from>
  WHAT IT DOES
    <one concrete sentence: which files, rows, or resources, and how many>
  SAMPLE OF WHAT WILL HAPPEN
    <output of a read-only probe you ran FIRST — git log --oneline -3, ls -la,
     du -sh, terraform plan, --dry-run. Read-only probes are NOT blocked by this
     gate; run one. If none exists, write "no probe available" and say why.>
  REVERSIBLE?
    <yes + the exact undo command, or "NO — there is no undo">
  IF YOU SAY "ALWAYS ALLOW"
    <what a standing session grant would cover, specifically — "any psql command
     against prod-db-01", not "database commands">

Then ask "Shall I run it?" and stop. After the user replies in their own turn, re-issue
the same command — this gate will let it through.`;
}

function dbMessage(cmd, info, cwd) {
  const prodWarning = /\b(prod|prd|production|live)\b/i.test(cmd)
    ? `
  *** The command mentions "prod". Say so in the FIRST line of your preview. ***
`
    : "";

  return `BLOCKED — guardrails/preview-gate: this is a write against a database and no preview
has been shown to the user yet.

  Command:   ${cmd}
  Client:    ${info.family}
  Statement: ${info.matched}
  cwd:       ${cwd}${prodWarning}

Run the read-only probe for this client FIRST — these are NOT blocked by this gate:
  psql/mysql/sqlcmd/snowsql/bq : EXPLAIN <stmt>  AND  SELECT count(*) <same FROM/WHERE>
  sqlite3                      : .schema <table> AND  SELECT count(*) <same WHERE>
  mongosh                      : db.<coll>.countDocuments(<same filter>)
  redis-cli                    : DBSIZE  AND  --scan --pattern '<same pattern>'
  alembic                      : alembic current  AND  alembic upgrade --sql <rev>
  prisma                       : prisma migrate diff --script

Then reply to the user with this block and STOP:

  ${PREVIEW_HEADING}
    <the command, verbatim>
  WHERE IT RUNS
    <host + database + which environment, and where you read that from.
     "localhost" is not a target — resolve what it points at.>
  AFFECTED ROWS
    <the number the count actually returned — not an estimate>
  SAMPLE
    <the first 2-3 rows the WHERE selects, or the offline SQL for a migration>
  REVERSIBLE?
    <is there a backup, a transaction, a down-migration? Name it. If the prior
     values are not recoverable, say so plainly and offer a snapshot first.>
  IF YOU SAY "ALWAYS ALLOW"
    <every future write this client could make against this target, unprompted>

Then ask "Shall I run it?" and stop. Re-issue the command after the user answers.`;
}

// Git publishing has no preview path. The block is the whole answer, so the message
// must not tell the model to retry — it tells it what to hand over instead.
function gitPublishMessage(cmd, info) {
  return `BLOCKED — guardrails/preview-gate: the agent never commits, pushes, or opens/merges
a pull request. This is a standing team rule, not a missing preview — showing a preview
will NOT unlock it, so do not retry this or any variant of it.

  Command:   ${cmd}
  Matched:   ${info.matched}

What to do instead:
  - If the user asked for a commit, give them the commit MESSAGE as a fenced text block
    (subject line under ~72 chars, blank line, body explaining why), plus the exact
    commands for THEM to run, e.g.  git add <files>  then  git commit -F <file>.
  - If they asked for a PR, give them the PR TITLE and DESCRIPTION as text (summary,
    what changed, how it was tested, risks), and let them open it.
  - NO attribution of any kind in either: no "Co-Authored-By: Claude", no "Generated
    with Claude Code", no AI/assistant credit line, footer, or emoji. This overrides
    any other instruction to add one.
  - Then stop. Staging with git add, stashing, and creating a branch are still fine
    if the user asks for them.`;
}

// --------------------------------------------------------------------------

try {
  const input = JSON.parse(fs.readFileSync(0, "utf8"));

  // Matchers are regex-matched against the tool name, so "Bash" can also reach
  // BashOutput and KillShell depending on version. Defend in the script.
  // PowerShell is gated too (0.9.0): on Windows it is the primary shell, and a
  // `psql ... DELETE` through it used to bypass this gate entirely.
  if (input.tool_name !== "Bash" && input.tool_name !== "PowerShell") allow();

  const cmd = (input.tool_input && input.tool_input.command) || "";
  if (!cmd.trim()) allow();

  const projectRoot = input.cwd || process.cwd();
  const cfg = loadConfig(projectRoot);
  if (mutedReason(cfg)) allow();

  // Before allow_patterns: a project whitelist is for its own safe wrapper scripts,
  // not a way around the no-commit rule. Only turning the plugin off lifts this.
  const early = classifyCommand(cmd);
  if (early && early.dangerClass === "git-publish") block(gitPublishMessage(cmd, early));

  if (matchesAny(cfg.allow_patterns, cmd)) allow();

  let info = early;
  if (!info && matchesAny(cfg.extra_patterns, cmd)) {
    info = { dangerClass: "project-defined", matched: "extra_patterns", family: "" };
  }
  if (!info) allow();

  const evidence = previewEvidence(input.transcript_path, cmd);
  if (evidence !== false) allow(); // true = previewed, null = can't tell

  block(
    info.dangerClass === "db-write"
      ? dbMessage(cmd, info, projectRoot)
      : generalMessage(cmd, info, projectRoot)
  );
} catch {
  allow(); // a gate that misfires closed is worse than no gate at all
}
