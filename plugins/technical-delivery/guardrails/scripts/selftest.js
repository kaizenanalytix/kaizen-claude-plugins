// Self-test for the guardrails hooks. Run it after any Claude Code upgrade:
//
//   node guardrails/scripts/selftest.js
//
// This exists because the preview gate's most likely failure is SILENT: it reads
// the transcript JSONL, and if that format changes the gate fails open — turning
// the guardrail off with no error anywhere. Nothing else will surface that. The
// TRANSCRIPT section below is the part that matters after an upgrade; if those
// cases fail, the gate is no longer enforcing anything.
//
// No dependencies, no test runner. Exits 1 on any failure.

"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync } = require("child_process");

const { classifyCommand, isReadOnlyProbe, isTestRunner } = require("./lib/classify");

// Every hook writes per-user state under ~/.claude/kaizen/. Point home at a throwaway
// folder so the test never touches the real one, and child processes inherit it.
const fakeHome = fs.mkdtempSync(path.join(os.tmpdir(), "kz-home-"));
process.env.HOME = fakeHome;
process.env.USERPROFILE = fakeHome;

const GATE = path.join(__dirname, "preview-gate.js");
const TRIAGE = path.join(__dirname, "failure-triage.js");

let pass = 0;
const failures = [];

function check(name, actual, expected) {
  const ok = actual === expected;
  if (ok) pass++;
  else failures.push(`${name}\n      expected: ${expected}\n      actual:   ${actual}`);
}

function section(t) {
  console.log(`\n${t}`);
}

// --------------------------------------------------------------------------
section("CLASSIFIER — must be gated (a preview is required)");
// --------------------------------------------------------------------------
[
  ['psql "$DATABASE_URL" -c "UPDATE orders SET status=\'shipped\' WHERE batch_id=42"', "db-write"],
  ['psql -c "DELETE FROM orders"', "db-write"],
  ["mysql -e 'TRUNCATE TABLE sessions'", "db-write"],
  ["alembic upgrade head", "db-write"],
  ["prisma migrate deploy", "db-write"],
  ["redis-cli FLUSHALL", "db-write"],
  ["psql <<'SQL'\nDROP TABLE users;\nSQL", "db-write"],            // heredoc, pass 2
  ["npm test && psql -c 'DROP TABLE x'", "db-write"],              // && chain
  ["DATABASE_URL=x sudo psql -c 'DELETE FROM t'", "db-write"],     // env prefix + sudo
  ["rm -rf ./uploads", "destructive-fs"],
  ["rm -rf /var/data", "destructive-fs"],
  ["git push --force origin main", "git-publish"],
  // Git publishing — the agent never commits, pushes, or opens a PR (0.9.0)
  ["git commit -m 'fix login'", "git-publish"],
  ["git add . && git commit -m \"$(cat <<'EOF'\nfix\nEOF\n)\"", "git-publish"], // cat must not make it a probe
  ["git log -1 && git push origin feature/x", "git-publish"],                  // probe riding along
  ["git push", "git-publish"],
  ["git push --force-with-lease origin main", "git-publish"],
  ["git -C ./repo commit --amend --no-edit", "git-publish"],
  ["git -c user.name=x commit -am wip", "git-publish"],
  ["git merge main", "git-publish"],
  ["git rebase origin/main", "git-publish"],
  ["git cherry-pick abc123", "git-publish"],
  ["gh pr create --title x --body y", "git-publish"],
  ["gh pr merge 42 --squash", "git-publish"],
  ["az repos pr create --title x", "git-publish"],
  // PowerShell forms (0.9.0)
  ['& "C:\\Program Files\\PostgreSQL\\16\\bin\\psql.exe" -U postgres -c "DELETE FROM orders"', "db-write"],
  ["psql.exe -c 'TRUNCATE TABLE t'", "db-write"],
  ["Invoke-Sqlcmd -Query 'DROP TABLE t'", "db-write"],
  ["git reset --hard HEAD~3", "destructive-fs"],
  ["git branch -D feature/x", "destructive-fs"],
  ["kubectl delete pod api-7d9", "destructive-infra"],
  ["terraform apply tfplan", "destructive-infra"],
  ["terraform destroy", "destructive-infra"],
  ["docker system prune -af", "destructive-infra"],
  ["npm publish", "destructive-infra"],
  ["make migrate-prod", "opaque-wrapper"],
  ["npm run db:reset", "opaque-wrapper"],
].forEach(([cmd, cls]) => {
  const r = classifyCommand(cmd);
  check(`gate: ${cmd.split("\n")[0].slice(0, 52)}`, r && r.dangerClass, cls);
});

// --------------------------------------------------------------------------
section("CLASSIFIER — must NOT be gated (false positives are the real risk)");
// --------------------------------------------------------------------------
[
  // Probes. If ANY of these gate, the model cannot build the preview it is
  // ordered to build, and the block loop becomes unbreakable.
  'psql -c "SELECT count(*) FROM orders WHERE batch_id=42"',
  'psql -c "EXPLAIN UPDATE orders SET status=1"',
  "alembic current",
  "alembic upgrade --sql head",
  "prisma migrate diff --script",
  "terraform plan -out=tfplan",
  "kubectl get pods",
  "npm publish --dry-run",
  "git log --oneline -3",
  "git status --porcelain",
  'sqlite3 app.db ".schema orders"',
  "redis-cli DBSIZE",
  // Carve-outs
  "rm -rf node_modules",
  "rm -rf node_modules dist .venv coverage",
  "kubectl --context minikube delete pod x",
  // Git that is NOT publishing — must stay usable
  "git add src/app.ts",
  "git stash push -m wip",           // "push" is stash's subcommand, not git's
  "git checkout -b feature/x",
  "git log --grep=commit",
  "git show HEAD:push.md",
  "gh pr view 42",
  "git diff --stat",
  // Ordinary work
  "ls -la",
  "npm install",
  "pytest tests/orders",
  'grep "DELETE FROM" audit.sql',            // verb in a string, not a db client
  'echo "dropping support for node 16"',
  "cat src/orders/update_handler.py",        // "update" inside a filename
].forEach((cmd) => {
  check(`allow: ${cmd.slice(0, 52)}`, classifyCommand(cmd), null);
});

// --------------------------------------------------------------------------
section("CLASSIFIER — probe and runner detection");
// --------------------------------------------------------------------------
check("probe: SELECT count", isReadOnlyProbe("psql -c 'SELECT count(*) FROM t'"), true);
check("probe: not when a write rides along",
  isReadOnlyProbe("psql -c 'SELECT 1' && psql -c 'DROP TABLE t'"), false);
check("runner: pytest", isTestRunner("pytest -q"), true);
check("runner: npm run build", isTestRunner("npm run build"), true);
check("runner: plain ls", isTestRunner("ls -la"), false);

// --------------------------------------------------------------------------
section("TRANSCRIPT — the part that breaks silently after an upgrade");
// --------------------------------------------------------------------------

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "kz-guardrails-"));
const CMD = "psql -c \"DELETE FROM orders WHERE batch_id=42\"";

function jsonl(entries) {
  const p = path.join(tmp, `t${Math.random().toString(36).slice(2)}.jsonl`);
  fs.writeFileSync(p, entries.map((e) => JSON.stringify(e)).join("\n") + "\n", "utf8");
  return p;
}

const filler = (n) =>
  Array.from({ length: n }, (_, i) => ({
    type: "assistant",
    message: { role: "assistant", content: [{ type: "text", text: `filler ${i}` }] },
  }));

const previewMsg = {
  type: "assistant",
  message: {
    role: "assistant",
    content: [{ type: "text", text: `WHAT I WANT TO RUN\n  ${CMD}\nREVERSIBLE? no` }],
  },
};
const realUser = { type: "user", message: { role: "user", content: "yes go ahead" } };
const toolResultUser = {
  type: "user",
  message: { role: "user", content: [{ type: "tool_result", content: "ok" }] },
};

// runGate returns the hook's exit code: 0 = allowed, 2 = blocked
function runGate(transcriptPath, env, opts) {
  const o = opts || {};
  const payload = JSON.stringify({
    tool_name: o.tool || "Bash",
    tool_input: { command: o.cmd || CMD },
    cwd: tmp,
    transcript_path: transcriptPath,
  });
  try {
    execFileSync("node", [GATE], {
      input: payload,
      stdio: ["pipe", "pipe", "pipe"],
      env: Object.assign({}, process.env, env || {}),
    });
    return 0;
  } catch (e) {
    return e.status;
  }
}

check("no preview at all -> BLOCK",
  runGate(jsonl([...filler(8), realUser])), 2);

check("preview + real user turn -> allow",
  runGate(jsonl([...filler(6), previewMsg, realUser])), 0);

// THE SINGLE MOST IMPORTANT CASE. Tool results are ALSO recorded as type:"user";
// if the gate counts one as the user answering, it silently stops enforcing
// anything. A real user turn sits at the START here so the "no human in this
// transcript at all" fail-open rule cannot mask what is being tested — the only
// thing after the preview is a tool_result, which must NOT count.
check("preview + tool_result (NOT a real user turn) -> BLOCK",
  runGate(jsonl([realUser, ...filler(6), previewMsg, toolResultUser])), 2);

check("legacy entry shape (entry.content, no .message) -> still parses",
  runGate(
    jsonl([
      ...filler(6),
      { type: "assistant", content: [{ type: "text", text: `WHAT I WANT TO RUN\n  ${CMD}` }] },
      { type: "user", content: "ok" },
    ])
  ), 0);

check("too few entries (post-compaction) -> fail open",
  runGate(jsonl([realUser])), 0);

check("no real user turn at all (headless / sub-agent) -> fail open",
  runGate(jsonl(filler(10))), 0);

check("missing transcript -> fail open",
  runGate(path.join(tmp, "does-not-exist.jsonl")), 0);

check("KZ_GUARDRAILS=off -> fail open",
  runGate(jsonl([...filler(8), realUser]), { KZ_GUARDRAILS: "off" }), 0);

// 0.9.0 — harness-injected "user" entries must not count as the user answering.
const metaUser = (text) => ({ type: "user", isMeta: true, message: { role: "user", content: [{ type: "text", text }] } });
check("preview + isMeta entry (image/skill/reminder) -> BLOCK",
  runGate(jsonl([realUser, ...filler(6), previewMsg, metaUser("[Image: source: x.png]")])), 2);
check("preview + <system-reminder>-only entry -> BLOCK",
  runGate(jsonl([realUser, ...filler(6), previewMsg,
    { type: "user", message: { role: "user", content: "<system-reminder>ctx</system-reminder>" } }])), 2);
check("preview + real prompt that STARTS with a reminder -> allow",
  runGate(jsonl([realUser, ...filler(6), previewMsg,
    { type: "user", message: { role: "user", content: [
      { type: "text", text: "<system-reminder>ctx</system-reminder>" },
      { type: "text", text: "yes run it" }] } }])), 0);

// 0.9.0 — PowerShell goes through the same gate.
check("PowerShell tool, db write, no preview -> BLOCK",
  runGate(jsonl([...filler(8), realUser]), null, { tool: "PowerShell" }), 2);
check("PowerShell tool, preview + real user turn -> allow",
  runGate(jsonl([...filler(6), previewMsg, realUser]), null, { tool: "PowerShell" }), 0);

// --------------------------------------------------------------------------
section("GIT PUBLISH — never unlocked by a preview (0.9.0)");
// --------------------------------------------------------------------------

const GITCMD = "git commit -m 'fix login'";
const gitPreview = {
  type: "assistant",
  message: { role: "assistant", content: [{ type: "text", text: `WHAT I WANT TO RUN\n  ${GITCMD}` }] },
};
check("git commit, no transcript at all -> BLOCK (no fail-open)",
  runGate(path.join(tmp, "nope.jsonl"), null, { cmd: GITCMD }), 2);
check("git commit even after preview + user yes -> BLOCK",
  runGate(jsonl([...filler(6), gitPreview, realUser]), null, { cmd: GITCMD }), 2);
check("git push via PowerShell -> BLOCK",
  runGate(jsonl(filler(10)), null, { cmd: "git push origin main", tool: "PowerShell" }), 2);
check("git publish block message forbids attribution", (() => {
  try {
    execFileSync("node", [GATE], {
      input: JSON.stringify({ tool_name: "Bash", tool_input: { command: GITCMD }, cwd: tmp }),
      stdio: ["pipe", "pipe", "pipe"],
    });
    return false;
  } catch (e) {
    const s = String(e.stderr);
    return /Co-Authored-By/.test(s) && /Generated\s+with Claude Code/.test(s) && /will NOT unlock/.test(s);
  }
})(), true);
check("git add is not blocked",
  runGate(jsonl(filler(10)), null, { cmd: "git add src/app.ts" }), 0);

// --------------------------------------------------------------------------
section("AGENT DISPATCH — a work dispatch must declare what done means");
// --------------------------------------------------------------------------

const ADGATE = path.join(__dirname, "agent-dispatch-gate.js");
const longBrief = "Implement the invoices module. ".repeat(20);

function runDispatch(prompt, extra) {
  const ti = Object.assign({ prompt }, extra || {});
  try {
    execFileSync("node", [ADGATE], {
      input: JSON.stringify({ tool_name: "Agent", tool_input: ti, cwd: tmp }),
      stdio: ["pipe", "pipe", "pipe"],
    });
    return 0;
  } catch (e) {
    return e.status;
  }
}

check("substantial dispatch, no criteria -> BLOCK", runDispatch(longBrief), 2);
check("same dispatch with DONE WHEN -> allow",
  runDispatch(longBrief + " DONE WHEN: router mounted at /api/v1/invoices."), 0);
check("ACCEPTANCE CRITERIA also satisfies it",
  runDispatch(longBrief + " ACCEPTANCE CRITERIA: the suite is green."), 0);
// Recon has no meaningful "done when" — demanding one there is pure noise.
check("read-only recon dispatch -> allow",
  runDispatch("Search for every place the auth token is read. ".repeat(15)), 0);
check("Explore agent type -> allow", runDispatch(longBrief, { subagent_type: "Explore" }), 0);
check("short prompt is not a work dispatch -> allow", runDispatch("check the version"), 0);

// --------------------------------------------------------------------------
section("ESCAPE HATCHES — ~/.claude/kaizen/<project-key>/guardrails.json");
// --------------------------------------------------------------------------

const { kaizenDir, projectKey } = require("./lib/project-key");
const userCfgDir = kaizenDir(tmp);
fs.mkdirSync(userCfgDir, { recursive: true });
const noPreview = jsonl([...filler(8), realUser]);

function withConfig(cfg, fn, dir) {
  const d = dir || userCfgDir;
  fs.mkdirSync(d, { recursive: true });
  const p = path.join(d, "guardrails.json");
  fs.writeFileSync(p, JSON.stringify(cfg), "utf8");
  try { return fn(); } finally { fs.unlinkSync(p); }
}

check("config lives under the (fake) home, not the repo",
  userCfgDir.startsWith(fakeHome) && !userCfgDir.startsWith(tmp), true);
check("legacy <repo>/.kaizen/guardrails.json is still honoured",
  withConfig({ enabled: false }, () => runGate(noPreview), path.join(tmp, ".kaizen")), 0);
check("user-level file wins over a legacy repo file",
  (() => {
    const legacy = path.join(tmp, ".kaizen");
    fs.mkdirSync(legacy, { recursive: true });
    fs.writeFileSync(path.join(legacy, "guardrails.json"), JSON.stringify({ enabled: false }), "utf8");
    try {
      return withConfig({ enabled: true }, () => runGate(noPreview));
    } finally { fs.unlinkSync(path.join(legacy, "guardrails.json")); }
  })(), 2);

check("allow_patterns whitelists a wrapper script",
  withConfig({ allow_patterns: ["^psql -c \"DELETE"] }, () => runGate(noPreview)), 0);
check("enabled:false turns it off",
  withConfig({ enabled: false }, () => runGate(noPreview)), 0);
check("muted_until in the future turns it off",
  withConfig({ muted_until: new Date(Date.now() + 3600e3).toISOString() }, () => runGate(noPreview)), 0);
check("muted_until in the past does NOT turn it off",
  withConfig({ muted_until: "2020-01-01T00:00:00Z" }, () => runGate(noPreview)), 2);
check("corrupt config fails open to enforcing",
  (() => {
    const p = path.join(userCfgDir, "guardrails.json");
    fs.writeFileSync(p, "{ not json", "utf8");
    try { return runGate(noPreview); } finally { fs.unlinkSync(p); }
  })(), 2);

// --------------------------------------------------------------------------
section("PROJECT KEY — one per checkout, shared by three plugins");
// --------------------------------------------------------------------------

const keyA = path.join(tmp, "a", "frontend");
const keyB = path.join(tmp, "b", "frontend");
fs.mkdirSync(path.join(keyA, ".git"), { recursive: true });
fs.mkdirSync(path.join(keyB, "src"), { recursive: true });
fs.mkdirSync(path.join(keyB, ".git"), { recursive: true });
check("two checkouts with the same folder name get different keys",
  projectKey(keyA) !== projectKey(keyB), true);
check("key keeps the folder name readable", /^frontend-[0-9a-f]{6}$/.test(projectKey(keyA)), true);
check("a subfolder resolves to its repo's key",
  projectKey(path.join(keyB, "src")) === projectKey(keyB), true);

// Each plugin carries its own copy so it can be installed alone. If they drift,
// the three plugins silently look in different folders for the same project.
const TD = path.resolve(__dirname, "..", "..");
["architecture-foundations", "codebase-map"].forEach((p) => {
  const sib = path.join(TD, p, "scripts", "lib", "project-key.js");
  if (!fs.existsSync(sib)) return; // installed standalone — nothing to compare
  check(`project-key.js identical in ${p}`,
    fs.readFileSync(sib, "utf8") === fs.readFileSync(path.join(__dirname, "lib", "project-key.js"), "utf8"),
    true);
});

// --------------------------------------------------------------------------
section("POSTTOOLUSE — failure triage fires only on a real runner failure");
// --------------------------------------------------------------------------

function runTriage(command, response) {
  const out = execFileSync("node", [TRIAGE], {
    input: JSON.stringify({
      tool_name: "Bash",
      tool_input: { command },
      tool_response: response,
      cwd: tmp,
      session_id: "selftest",
    }),
    encoding: "utf8",
  });
  return out.trim();
}

check("pytest failure -> injects", runTriage("pytest -q", "2 failed, 5 passed").length > 0, true);
check("pytest success -> silent", runTriage("pytest -q", "7 passed"), "");
check("non-runner with scary output -> silent",
  runTriage("cat log.txt", "AssertionError everywhere"), "");
check("git stderr on success -> silent",
  runTriage("git push", "Everything up-to-date"), "");
check("injects the additionalContext shape", (() => {
  try {
    const o = JSON.parse(runTriage("npm run build", "error TS2345: bad"));
    return o.hookSpecificOutput.hookEventName === "PostToolUse" &&
      typeof o.hookSpecificOutput.additionalContext === "string";
  } catch { return false; }
})(), true);

// --------------------------------------------------------------------------
section("WRITE GATE — implementation needs an agreed scope, once per piece of work");
// --------------------------------------------------------------------------

const WGATE = path.join(__dirname, "write-gate.js");
const SCOPE_MSG = {
  type: "assistant",
  message: {
    role: "assistant",
    content: [{ type: "text", text: "WHAT I UNDERSTAND / WHAT I'D BUILD / UNPINNED: paging?" }],
  },
};
const says = (s) => ({ type: "user", message: { role: "user", content: s } });
const asst = (s) => ({ type: "assistant", message: { role: "assistant", content: [{ type: "text", text: s }] } });

// Default target is a MIGRATION — since 0.9.0 only database work is hard-gated, so
// the strict-path cases below must exercise a database file to mean anything.
function runWrite(entries, file, content) {
  const payload = JSON.stringify({
    tool_name: "Write",
    tool_input: {
      file_path: path.join(tmp, ...(file || "migrations/0002_invoices.py").split("/")),
      content: content || "",
    },
    cwd: tmp,
    transcript_path: jsonl(entries),
  });
  try {
    execFileSync("node", [WGATE], { input: payload, stdio: ["pipe", "pipe", "pipe"] });
    return 0;
  } catch (e) {
    return e.status;
  }
}

// The case that matters most: one user turn, model starts writing immediately.
check("asked, nothing agreed -> BLOCK",
  runWrite([...filler(6), says("add invoices"), asst("sure, doing it now")]), 2);
check("scope shown and user replied -> allow",
  runWrite([...filler(6), says("add invoices"), SCOPE_MSG, says("go")]), 0);
// One stop per piece of WORK, not per file — no new user turn, window hasn't moved.
check("second file of approved work -> allow",
  runWrite([...filler(6), says("add invoices"), SCOPE_MSG, says("go"), asst("wrote file 1")]), 0);
// New request slides the window past the old approval.
check("new unscoped request after approved work -> BLOCK",
  runWrite([...filler(6), says("add invoices"), SCOPE_MSG, says("go"), asst("done"), says("now add payments")]), 2);
check("a tool_result is not the user approving -> BLOCK",
  runWrite([...filler(6), says("add invoices"), SCOPE_MSG, toolResultUser]), 2);
check("no user turns at all (headless / sub-agent) -> fail open",
  runWrite([...filler(10)]), 0);

// 0.9.0 — ordinary code is not hard-gated. This is the fix for "it blocks even
// normal code": an unscoped edit to an ordinary file goes straight through.
const unscoped = [...filler(6), says("add invoices"), asst("sure, doing it now")];
check("ordinary .ts file, nothing agreed -> allow", runWrite(unscoped, "src/x.ts", "export const x = 1;"), 0);
check("ordinary .tsx component -> allow",
  runWrite(unscoped, "src/modules/orders/components/OrderTable.tsx", "<Column title='Qty' />"), 0);
check("pydantic schemas/ is not database -> allow",
  runWrite(unscoped, "app/modules/orders/schemas/order.py", "class Order(BaseModel): ..."), 0);
check("markdown that mentions DROP TABLE -> allow",
  runWrite(unscoped, "docs/runbook.md", "never run DROP TABLE users in prod"), 0);

// Database work IS gated — by path…
[
  "alembic/versions/0003_add_col.py",
  "db/migrate/20260930_add_index.rb",
  "src/db/client.ts",
  "prisma/schema.prisma",
  "sql/report.sql",
  "app/orders/models.py",
  "db/flyway/V2__add_col.sql",
].forEach((f) => check(`db path gated: ${f}`, runWrite(unscoped, f, "x"), 2));

// …and by content, wherever the file lives.
[
  ["src/orders/repo.ts", "await db.query('DELETE FROM orders WHERE id = $1', [id])"],
  ["app/infra/tables.py", "id = mapped_column(Integer, primary_key=True)"],
  ["app/core/engine.py", "engine = create_async_engine(settings.url)"],
  ["src/config.ts", "const url = 'postgresql://app:pw@db:5432/app'"],
  [".env", "DATABASE_URL=postgres://localhost/app"],
].forEach(([f, c]) => check(`db content gated: ${f}`, runWrite(unscoped, f, c), 2));

// THE BUG this release fixes. Approved DB work, then the harness injects an image
// read / skill load / reminder as a type:"user" entry. That used to slide the window
// and block the next file of already-approved work.
check("approved db work + isMeta entry mid-task -> still allow",
  runWrite([...filler(6), says("add invoices table"), SCOPE_MSG, says("go"),
    asst("wrote 0001"), metaUser("Base directory for this skill: x")]), 0);
check("approved db work + <system-reminder> entry -> still allow",
  runWrite([...filler(6), says("add invoices table"), SCOPE_MSG, says("go"),
    asst("wrote 0001"), says("<system-reminder>file changed</system-reminder>")]), 0);

// --------------------------------------------------------------------------
section("USERPROMPTSUBMIT — scope block fires on work, stays quiet on trivia");
// --------------------------------------------------------------------------

const SCOPE = path.join(__dirname, "scope-first.js");

function runScope(prompt, env) {
  return execFileSync("node", [SCOPE], {
    input: JSON.stringify({ prompt, cwd: tmp }),
    encoding: "utf8",
    env: Object.assign({}, process.env, env || {}),
  }).trim();
}

// Implementation gates regardless of how short the prompt is — "add a route" is
// eleven characters and still needs a go-ahead. These are the cases the old
// length-based shortcut used to swallow.
[
  "add an invoices module to the backend",
  "refactor the orders service to use the repository pattern",
  "can you set up CI/CD for this project",
  "implement the checkout flow end to end",
  "add a route",
  "fix the login bug",
  "install axios",
  "update the theme",
  "refactor this",
  "can you make the header sticky",
].forEach((p) => check(`gates: ${p.slice(0, 44)}`, runScope(p).length > 0, true));

// Noise is how a standing instruction gets trained out of usefulness — the user
// starts skipping it, and then it isn't there for the request that needed it.
[
  "yes please",
  "ok",
  "go ahead",
  "what does D3 mean",
  "what is the test pyramid",
  "why did that fail",
  "thanks",
].forEach((p) => check(`quiet: ${p.slice(0, 44)}`, runScope(p), ""));

// Recall is not work. These regressed twice: once because a stray control byte made
// the RECALL regex match nothing, once because the length shortcut fired before the
// deliverable guard was consulted.
[
  "give me list of guardrails that we gave",
  "show me the rules",
  "what are the guardrails",
  "explain how the write gate works",
  "which skill handles routing",
  "how many hooks are there",
  "tell me why that failed",
  "summarize what we changed today",
].forEach((p) => check(`recall quiet: ${p.slice(0, 38)}`, runScope(p), ""));

// Recall PHRASING around a real deliverable, or around an action, is still work.
[
  "give me an artifact of each guardrail with an example",
  "list the files you would create for the invoices module",
  "show me by adding a route to the orders module",
  "explain the auth flow and then add a login page",
].forEach((p) => check(`recall+work gates: ${p.slice(0, 34)}`, runScope(p).length > 0, true));

// No control bytes anywhere in the hook sources. A stray 0x08 from a mangled escape
// silently disabled the RECALL regex once already, and nothing else would catch it.
["scope-first.js", "write-gate.js", "preview-gate.js", "agent-dispatch-gate.js",
 "guardrail-contract.js", "failure-triage.js"].forEach((f) => {
  const src = fs.readFileSync(path.join(__dirname, f), "utf8");
  const bad = [...src].some((c) => c.charCodeAt(0) < 9 || (c.charCodeAt(0) > 13 && c.charCodeAt(0) < 32));
  check(`no control bytes in ${f}`, bad, false);
});

check("scope-first respects KZ_GUARDRAILS=off",
  runScope("add an invoices module to the backend", { KZ_GUARDRAILS: "off" }), "");
check("scope-first emits the UserPromptSubmit shape", (() => {
  try {
    const o = JSON.parse(runScope("build the invoices module end to end"));
    return o.hookSpecificOutput.hookEventName === "UserPromptSubmit" &&
      /WHAT I'D BUILD/.test(o.hookSpecificOutput.additionalContext);
  } catch { return false; }
})(), true);

// It has to be a GATE, not a preamble. If this text ever stops telling the model to
// stop and wait, the rule silently degrades into "narrate, then do it anyway" —
// which is what it replaced.
check("scope-first tells the model to STOP, not to proceed", (() => {
  const c = JSON.parse(runScope("add an invoices module")).hookSpecificOutput.additionalContext;
  return /do NOT start building/.test(c) &&
    /wait for their answer/.test(c) &&
    /UNPINNED/.test(c) &&
    !/then proceed if/i.test(c);
})(), true);

// Cost guard: this text is paid on EVERY prompt. If it grows, move the growth to
// the SessionStart contract, which is paid once.
// O9: a sweep across many files gets the staging note; a single-target change does not.
[
  "rename useAuth to useSession everywhere",
  "add a header to every skill file",
  "update all the components",
  "refactor this across the whole codebase",
].forEach((p) =>
  check(`bulk note: ${p.slice(0, 40)}`, /Stage it \(O9\)/.test(runScope(p)), true));

[
  "add a route to the orders module",
  "fix the login bug",
  "implement the checkout flow end to end",
].forEach((p) =>
  check(`no bulk note: ${p.slice(0, 40)}`, /Stage it \(O9\)/.test(runScope(p)), false));

check("scope-first stays under ~300 tokens",
  runScope("build the invoices module end to end").length < 1300, true);

// --------------------------------------------------------------------------
try { fs.rmSync(tmp, { recursive: true, force: true }); } catch {}
try { fs.rmSync(fakeHome, { recursive: true, force: true }); } catch {}

console.log(`\n${"=".repeat(60)}`);
if (failures.length) {
  console.log(`FAILED — ${pass} passed, ${failures.length} failed\n`);
  failures.forEach((f, i) => console.log(`  ${i + 1}. ${f}\n`));
  console.log("If only the TRANSCRIPT cases failed, the preview gate is no longer");
  console.log("enforcing anything — the JSONL format has probably changed. Fix");
  console.log("textOf/roleOf/isRealUserTurn in preview-gate.js.");
  process.exit(1);
}
console.log(`OK — all ${pass} checks passed.`);
