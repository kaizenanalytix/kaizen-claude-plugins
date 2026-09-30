// PreToolUse hook (Edit|Write|NotebookEdit): blocks the FIRST write of a new piece
// of DATABASE work until a scope block has been shown and the user has answered it.
//
// SCOPE (0.9.0). This used to gate every edit in the repo, and in practice it blocked
// ordinary code partway through approved work (see the isMeta fix in
// lib/transcript.js). Ordinary code is now left to the advisory scope-first prompt.
// The hard stop is kept only where a wrong edit reaches data: migrations, SQL, ORM
// models, seeds, and connection config — found by PATH (isDbPath) or by CONTENT
// (DB_CONTENT) for repository code that writes raw SQL. Everything else passes.
//
// WHY THIS EXISTS. The scope block was delivered by a UserPromptSubmit hook, and
// UserPromptSubmit is ADVISORY — it injects context, it cannot stop a turn. So
// "do NOT start building" was a request the model could read and then ignore, which
// is exactly what "it's not following it" means in practice. Only PreToolUse can
// actually block. This is the same relationship preview-gate.js has to Bash: the
// prose says what to do, the gate makes it non-optional.
//
// THE RULE, precisely: a scope block must appear BEFORE THE LAST REAL USER TURN,
// and after the one before it.
//
//   user: "add invoices"          <- previous user turn (window opens)
//   assistant: [scope block]      <- must appear in here
//   user: "go"                    <- last user turn (window closes)
//   -> writes allowed
//
// With only ONE user turn in the tail the window opens at the start of it, so
// "user asks -> model starts writing" blocks. That is the single most important
// case and an earlier draft got it wrong by treating one user turn as
// too-little-history and failing open — which meant the first request of any
// session was never gated.
//
// That shape is what makes it one stop per piece of WORK rather than one per file:
//
//   * Once approved, the model writes ten files with no new user turn in between,
//     so the window never moves and every write passes. No re-asking per file.
//   * When the user then says "now add payments", that becomes the new last user
//     turn, the window slides, and there is no scope block inside it — so the next
//     write blocks until the new work is scoped. New work, new go-ahead.
//
// FAILS OPEN on: no real user turns at all (headless `claude -p`, sub-agents —
// there is nobody to scope TO, and a deny-loop there is unrecoverable), a tail too
// short to reason about (post-compaction), an unreadable or unrecognised
// transcript, a file outside the project root, this plugin's own scratch paths, a
// muted config, and any script error. A gate that misfires closed would brick every
// edit in the repo.

"use strict";

const fs = require("fs");
const path = require("path");
const { textOf, roleOf, readTail, userTurnIndices } = require("./lib/transcript");
const { loadConfig, mutedReason, matchesAny } = require("./lib/config");

// Any one of these in an assistant message counts as having scoped the work. Kept
// as a set of markers rather than one exact heading so a reasonable paraphrase
// still satisfies the gate — the point is that the user saw a plan and answered,
// not that a specific string was typed.
const SCOPE_MARKERS = [
  "WHAT I'D BUILD",
  "WHAT I WOULD BUILD",
  "WHAT I UNDERSTAND",
  "WHAT I'D WORK ON",
  "UNPINNED",
  "SCOPE BLOCK",
  // The C9 short form. A one-property, single-file, already-diagnosed change gets a
  // one-line ask rather than the five-field block — but it is still a STOP, and the
  // gate has to recognise it or the short form is unusable: the user approves the
  // one-liner and the edit gets blocked anyway, forcing the long form back.
  // Deliberately shared with V4's hypothesis report, which is the same shape —
  // "here is the change I would make", followed by the user's turn.
  "PROPOSED CHANGE",
];

// Files that ARE database work by where they live. Matched against the path with
// forward slashes, case-insensitive. Deliberately not "schemas/" — in the FastAPI
// layout that is Pydantic request/response models, not tables.
const DB_PATH = [
  /\/(migrations?|alembic|flyway|liquibase|seeds?|seeders|fixtures\/sql)\//i,
  /\/db\/(migrate|seeds?)\//i,
  /\/(db|database)\//i,
  /\/prisma\//i,
  /\.(sql|prisma)$/i,
  /\/V\d+(_\d+)*__[^/]+$/,                   // Flyway V1__init.*
  /(^|\/)(alembic\.ini|schema\.rb|knexfile\.[jt]s|ormconfig\.[jt]s(on)?|dbt_project\.ya?ml|drizzle\.config\.[jt]s)$/i,
  /(^|\/)models\.py$/i,                      // Django / SQLAlchemy convention
  /\/dbt\/models\//i,
];

// Content that makes ANY file database work: raw write/DDL SQL, ORM table
// declarations, engine/session setup, and connection strings. Checked on the text
// being written or replaced. Not applied to prose (.md/.txt/.rst) — docs that talk
// about DROP TABLE are not database work, and this plugin's own skills are full of it.
const DB_CONTENT = [
  /\b(CREATE|ALTER|DROP)\s+(TABLE|INDEX|SCHEMA|DATABASE|VIEW|SEQUENCE|TRIGGER|FUNCTION)\b/i,
  /\bTRUNCATE\s+(TABLE\s+)?[\w."]+/i,
  /\bDELETE\s+FROM\s+[\w."]+/i,
  /\bINSERT\s+INTO\s+[\w."]+/i,
  /\bUPDATE\s+[\w."]+\s+SET\b/i,
  /\bmodels\.Model\b|\bmigrations\.(Migration|RunSQL|AddField|RemoveField|AlterField|CreateModel|DeleteModel)\b/,
  /\b(declarative_base|DeclarativeBase|mapped_column|create_engine|create_async_engine|sessionmaker|async_sessionmaker)\b/,
  /\bColumn\(\s*(Integer|String|Text|Boolean|DateTime|Date|Numeric|Float|ForeignKey|BigInteger|JSONB?|UUID|Enum)\b/,
  /\bop\.(add_column|drop_column|create_table|drop_table|alter_column|execute|create_index|drop_index)\b/,
  /@(Entity|Table)\b|\bsequelize\.define\b|\bmongoose\.(model|Schema)\b|\$executeRaw|\$queryRaw/,
  /\b(DATABASE_URL|SQLALCHEMY_DATABASE_URI|DB_(HOST|PASSWORD|USER|NAME|URL|PORT))\b/,
  /\b(postgres(ql)?|mysql|mariadb|mongodb(\+srv)?|redis|mssql|sqlserver)(\+\w+)?:\/\//i,
];

const PROSE = /\.(md|mdx|txt|rst|adoc)$/i;

function isDbPath(file) {
  const p = "/" + String(file).replace(/\\/g, "/");
  return DB_PATH.some((re) => re.test(p));
}

function writtenText(ti) {
  return [ti.content, ti.new_string, ti.old_string, ti.new_source]
    .filter((s) => typeof s === "string")
    .join("\n");
}

function dbReason(file, ti) {
  if (isDbPath(file)) return "database path";
  if (PROSE.test(file)) return null;
  const text = writtenText(ti);
  const hit = DB_CONTENT.find((re) => re.test(text));
  return hit ? "database content" : null;
}

function allow() {
  process.exit(0);
}

function block(message) {
  process.stderr.write(message + "\n");
  process.exit(2);
}

function hasScopeBeforeLastUserTurn(entries) {
  const users = userTurnIndices(entries);

  // Nobody in this transcript at all: headless `claude -p` or a sub-agent. There is
  // no one to scope TO, and a deny-loop there is unrecoverable, so fail open.
  if (users.length === 0) return null;

  const last = users[users.length - 1];

  // Window to search: from the PREVIOUS user turn to the last one. With only one
  // user turn, the window opens at the start of the tail — which is the case that
  // matters most, because "user asks, model immediately starts writing" has exactly
  // one user turn, and treating that as too-little-history to judge would mean the
  // first request of every session could never be gated at all.
  const prev = users.length >= 2 ? users[users.length - 2] : -1;

  for (let i = prev + 1; i < last; i++) {
    const e = entries[i];
    if (roleOf(e) !== "assistant") continue;
    const text = (textOf(e) || "").toUpperCase();
    if (SCOPE_MARKERS.some((m) => text.includes(m))) return true;
  }
  return false;
}

const MESSAGE = `BLOCKED — guardrails/write-gate: this edit touches the DATABASE (migration, SQL,
ORM model, seed, or connection config) and no scope block has been shown for it since
the user's previous turn, so it has not been agreed yet. Ordinary code edits are not
gated; database work is, strictly.

Do NOT write this file, and do NOT work around the gate. Reply to the user with this
block, then STOP and wait for their answer:

  WHAT I UNDERSTAND
    <one line, the ask in your own words>
  WHAT I'D BUILD
    <the concrete items, in order — and if this repeats across more than about
     five files, say you'll pilot ONE first and confirm the pattern (O9)>
  NOT DOING
    <what you're deliberately leaving out>
  UNPINNED
    <every detail this depends on that they haven't specified and the repo's docs
     don't answer. Name the default you'd take. Do NOT take it yet.>
  SKILLS
    <which skill/plugin applies, if more than one could>

Then ask whether to go, and wait. After they reply in their own turn, retry the
edit — this gate will let it through, and every following file in the same approved
work goes through without asking again.

If they already approved this work and you are still seeing this, you have gone past
what was agreed: say what changed and re-confirm rather than widening it silently.`;

try {
  const input = JSON.parse(fs.readFileSync(0, "utf8"));

  const t = input.tool_name;
  if (t !== "Edit" && t !== "Write" && t !== "NotebookEdit") allow();

  const ti = input.tool_input || {};
  const file = ti.file_path || ti.notebook_path;
  if (!file) allow();

  // Build output, VCS internals, and this plugin's own state are not "implementation".
  if (/[\\/](node_modules|dist|build|\.git|\.kaizen|coverage|__pycache__|\.venv)[\\/]/.test(file)) allow();

  const projectRoot = input.cwd || process.cwd();

  // A file outside the project isn't this project's work — same fix the adoption
  // gate needed after it blocked a scratchpad under the OS temp directory.
  const absRoot = path.resolve(projectRoot);
  const absFile = path.resolve(path.isAbsolute(file) ? file : path.join(absRoot, file));
  const rel = path.relative(absRoot, absFile);
  if (!rel || rel.startsWith("..") || path.isAbsolute(rel)) allow();

  const cfg = loadConfig(projectRoot);
  if (mutedReason(cfg)) allow();
  if (matchesAny(cfg.allow_patterns, file)) allow();

  // Only database work is hard-gated. Everything else is ordinary code. Tested on
  // the PROJECT-RELATIVE path, so a repo that lives under D:\database\ isn't all DB.
  if (!dbReason(rel, ti)) allow();

  const entries = readTail(input.transcript_path, 200000);
  if (!entries || entries.length < 6) allow();

  const scoped = hasScopeBeforeLastUserTurn(entries);
  if (scoped !== false) allow(); // true = agreed, null = can't tell

  block(MESSAGE);
} catch {
  allow(); // a gate that misfires closed is worse than no gate at all
}
