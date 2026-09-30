// Shared command classifier for the guardrails plugin's two Bash hooks.
// Dependency-free, node builtins only, no I/O — pure string analysis so both
// hooks can call it before touching the filesystem.
//
// Two passes, deliberately:
//   1. STRUCTURAL — split the command on shell operators *outside* quotes, strip
//      env-var prefixes and wrappers, take token 0 of each segment as its family.
//   2. RAW KEYWORD SCAN of the whole original string. This is what catches
//      heredocs: `psql <<'SQL' ... DROP TABLE users; SQL` has the dangerous verb
//      in the command text even though pass 1 can never reach inside the heredoc.
//
// For databases the two are CONJUNCTIVE — a db family from pass 1 AND a dangerous
// verb from pass 2 — which is what keeps `grep "DROP TABLE" schema.sql` from
// tripping the gate.
//
// Where this deliberately gives up (returns null, i.e. allows): command
// substitution where the outer command isn't itself dangerous, aliases, shell
// functions, and opaque wrapper scripts. Obfuscation is not in the threat model;
// the model isn't adversarial. A hook that blocks incorrectly is worse than no
// hook at all, so every uncertainty resolves to "allow".

"use strict";

// ---------------------------------------------------------------------------
// Pass 1: structural splitting
// ---------------------------------------------------------------------------

// Splits on && || ; | and newlines that are OUTSIDE single quotes, double quotes,
// and backslash escapes. Hand-rolled because a regex cannot track quote state.
function splitSegments(cmd) {
  const out = [];
  let cur = "";
  let sq = false; // inside '...'
  let dq = false; // inside "..."
  for (let i = 0; i < cmd.length; i++) {
    const c = cmd[i];
    if (c === "\\" && !sq) {
      cur += c + (cmd[i + 1] || "");
      i++;
      continue;
    }
    if (c === "'" && !dq) { sq = !sq; cur += c; continue; }
    if (c === '"' && !sq) { dq = !dq; cur += c; continue; }
    if (!sq && !dq) {
      if (c === "&" && cmd[i + 1] === "&") { out.push(cur); cur = ""; i++; continue; }
      if (c === "|" && cmd[i + 1] === "|") { out.push(cur); cur = ""; i++; continue; }
      if (c === ";" || c === "|" || c === "\n") { out.push(cur); cur = ""; continue; }
    }
    cur += c;
  }
  out.push(cur);
  return out.map((s) => s.trim()).filter(Boolean);
}

// Wrappers that stand in front of the real command without changing what it does.
const WRAPPERS = new Set([
  "sudo", "env", "nohup", "time", "xargs", "command", "exec", "nice", "doas", "setsid",
  "&", // PowerShell call operator: & "C:\...\psql.exe" -c "..."
]);

// Returns the command family (token 0) for a segment, after stripping FOO=bar
// assignments and wrapper commands. Returns "" when nothing resolves.
function familyOf(segment) {
  const tokens = segment.split(/\s+/).filter(Boolean);
  let i = 0;
  while (i < tokens.length) {
    const t = tokens[i];
    if (/^[A-Za-z_][A-Za-z0-9_]*=/.test(t)) { i++; continue; } // FOO=bar prefix
    if (WRAPPERS.has(t)) { i++; continue; }
    break;
  }
  let head = tokens[i] || "";
  // A quoted executable path with spaces ("C:\Program Files\...\psql.exe") spans
  // several tokens; rejoin up to the closing quote.
  const q = head[0];
  if ((q === '"' || q === "'") && !(head.length > 1 && head.endsWith(q))) {
    let j = i + 1;
    while (j < tokens.length && !tokens[j].endsWith(q)) j++;
    head = tokens.slice(i, j + 1).join(" ");
  }
  head = head.replace(/^["']|["']$/g, "");
  // strip a path: /usr/bin/psql -> psql, ./scripts/deploy.sh -> deploy.sh,
  // and Windows' .exe: C:\...\psql.exe -> psql
  return head.split(/[\\/]/).pop().toLowerCase().replace(/\.exe$/, "");
}

function familiesIn(cmd) {
  return splitSegments(cmd).map(familyOf).filter(Boolean);
}

// ---------------------------------------------------------------------------
// Read-only probes — checked FIRST, and they always win
// ---------------------------------------------------------------------------
//
// THIS IS THE MOST IMPORTANT LIST IN THE FILE. The gate orders the model to
// produce a preview containing real probe output. If the gate blocked the probes
// themselves, the model could not produce the preview it is being ordered to
// produce, and the loop would be unbreakable. Every entry here exists to keep
// that from happening.
const PROBE_PATTERNS = [
  /--dry-run\b/i,
  /--sql\b/i,                                  // alembic upgrade --sql: prints, runs nothing
  /\bterraform\s+plan\b/i,
  /\bprisma\s+migrate\s+diff\b/i,
  /\balembic\s+(current|history|heads|show|branches)\b/i,
  /\bkubectl\s+(get|describe|logs|explain|top|api-resources)\b/i,
  /\bdocker\s+(ps|images|inspect|logs|stats)\b/i,
  /\bgit\s+(status|log|diff|show|remote|branch\s*$|rev-parse|check-ignore|ls-files)\b/i,
  /\bnpm\s+(ls|view|outdated|audit)\b/i,
  /\bSELECT\b/i,
  /\bSHOW\b/i,
  /\bDESCRIBE\b/i,
  /\bcount\s*\(/i,
  /\bcountDocuments\s*\(/i,
  /\bDBSIZE\b/i,
  /--scan\b/i,
  /\\d[a-z+]*\b/,                              // psql \dt \d+ \l
  /^\s*sqlite3\s+\S+\s+["']?\.(schema|tables|dump)/i,
  /\b(ls|cat|head|tail|grep|find|stat|du|df|wc|which|echo|pwd)\b\s/i,
];

function isReadOnlyProbe(cmd) {
  // EXPLAIN <write statement> is a query PLAN — it does not execute the write, and
  // it is exactly the probe the preview asks for. But EXPLAIN ANALYZE genuinely
  // RUNS the statement, including an UPDATE or DELETE, so ANALYZE anywhere in the
  // command disqualifies it. Conservative on purpose: the cost of being wrong in
  // this direction is one unnecessary preview, the other direction is a silent write.
  if (/\bEXPLAIN\b/i.test(cmd) && !/\bANALYZE\b/i.test(cmd)) return true;

  // Otherwise a probe claim only holds if NO write verb rides along.
  // `psql -c "SELECT 1" && psql -c "DROP TABLE x"` is not a probe.
  if (WRITE_VERB.test(cmd)) return false;
  return PROBE_PATTERNS.some((re) => re.test(cmd));
}

// ---------------------------------------------------------------------------
// Danger tables
// ---------------------------------------------------------------------------

const DB_FAMILIES = new Set([
  "psql", "mysql", "mariadb", "sqlite3", "mongosh", "mongo", "redis-cli",
  "alembic", "prisma", "sqlcmd", "bq", "snowsql", "dbt", "flyway", "liquibase",
  "invoke-sqlcmd", // PowerShell SqlServer module
]);

// ---------------------------------------------------------------------------
// Git publishing — ALWAYS blocked, no preview unlocks it (0.9.0)
// ---------------------------------------------------------------------------
//
// Team rule: the agent never commits, pushes, or opens/merges a PR. It drafts the
// commit message or PR description as text and the human runs it. Checked BEFORE
// the probe list on purpose: `git commit -m "$(cat <<'EOF' ...)"` contains `cat`,
// and `git log -1 && git push` contains a probe, and either would otherwise pass.
//
// The subcommand must be git's first non-option word, so `git log --grep=commit`
// and `git show HEAD:push.md` don't match. -C/-c take an argument.
const GIT_OPTS = String.raw`(?:\s+(?:-[Cc]\s+(?:"[^"]*"|'[^']*'|\S+)|--?[\w-]+(?:=(?:"[^"]*"|\S+))?))*`;
const GIT_PUBLISH = [
  [new RegExp(String.raw`\bgit${GIT_OPTS}\s+commit\b`, "i"), "git commit"],
  [new RegExp(String.raw`\bgit${GIT_OPTS}\s+push\b`, "i"), "git push"],
  [new RegExp(String.raw`\bgit${GIT_OPTS}\s+(merge|rebase|cherry-pick|revert|am)\b`, "i"), "git merge/rebase/cherry-pick/revert/am"],
  [/\bgh\s+pr\s+(create|merge|ready)\b/i, "gh pr create/merge"],
  [/\bglab\s+mr\s+(create|merge)\b/i, "glab mr create/merge"],
  [/\baz\s+repos\s+pr\s+(create|update)\b/i, "az repos pr create/update"],
];

function gitPublish(cmd) {
  for (const [re, label] of GIT_PUBLISH) {
    if (re.test(cmd)) return label;
  }
  return null;
}

// Pass-2 verbs. Word-boundaried so "deleted" and "updated_at" don't match.
const WRITE_VERB =
  /\b(DROP|TRUNCATE|DELETE|UPDATE|ALTER|GRANT|REVOKE|FLUSHALL|FLUSHDB|INSERT\s+INTO)\b/i;
const MIGRATION_VERB =
  /\b(upgrade|downgrade|migrate\s+deploy|migrate\s+reset|db\s+push|db\s+reset|migrate\s+dev)\b/i;

const DESTRUCTIVE_FS = [
  [/\brm\s+(-\w*r\w*f\w*|-\w*f\w*r\w*)\b/i, "rm -rf"],
  [/\brm\s+-r\s+-f\b|\brm\s+-f\s+-r\b/i, "rm -r -f"],
  [/\bgit\s+push\b[^|;&]*\s(--force\b|-f\b)/i, "git push --force"],
  [/\bgit\s+reset\s+--hard\b/i, "git reset --hard"],
  [/\bgit\s+clean\s+-\w*f/i, "git clean -f"],
  [/\bgit\s+branch\s+-D\b/i, "git branch -D"],
  [/\bgit\s+(push|tag)\b[^|;&]*--delete\b/i, "git delete remote ref"],
  [/\bfind\b[^|;&]*\s-delete\b/i, "find -delete"],
  [/\bshred\b/i, "shred"],
  [/\bmkfs\b|\bdd\s+if=/i, "raw disk write"],
];

const DESTRUCTIVE_INFRA = [
  [/\bkubectl\s+delete\b/i, "kubectl delete"],
  [/\bterraform\s+(apply|destroy)\b/i, "terraform apply/destroy"],
  [/\bdocker\s+system\s+prune\b/i, "docker system prune"],
  [/\bdocker\s+volume\s+rm\b/i, "docker volume rm"],
  [/\bnpm\s+publish\b/i, "npm publish"],
  [/\baws\s+s3\s+rm\b[^|;&]*--recursive\b/i, "aws s3 rm --recursive"],
  [/\bgcloud\b[^|;&]*\sdelete\b/i, "gcloud delete"],
  [/\baz\b[^|;&]*\sdelete\b/i, "az delete"],
  [/\bhelm\s+(delete|uninstall)\b/i, "helm uninstall"],
];

// Opaque wrapper targets. High signal, and the only partial answer to
// `make migrate-prod`, which pass 1 cannot see inside.
const WRAPPER_TARGET =
  /\b(npm|pnpm|yarn|make|task|just|rake|invoke)\b[^|;&]*\b(migrate|deploy|reset|seed|drop|prune|nuke|wipe|restore|publish)\b/i;

// ---------------------------------------------------------------------------
// Carve-outs — each one named for the friction it prevents
// ---------------------------------------------------------------------------

// Regenerable build artefacts. Deleting these is a daily operation, not a
// destructive act; gating it is pure friction.
const REGENERABLE = [
  "node_modules", "dist", "build", "out", ".venv", "venv", "__pycache__",
  ".next", ".nuxt", ".svelte-kit", ".turbo", ".parcel-cache", "target",
  "coverage", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
  "vendor", ".gradle", "bin/Debug", "obj",
];

// True only when EVERY path argument to rm is a regenerable artefact.
// `rm -rf node_modules ./uploads` is not covered by this.
function rmTargetsAllRegenerable(cmd) {
  const m = cmd.match(/\brm\s+((?:-\S+\s+)*)(.+)$/i);
  if (!m) return false;
  const args = m[2]
    .split(/\s+/)
    .filter((a) => a && !a.startsWith("-"))
    .map((a) => a.replace(/^["']|["']$/g, ""));
  if (!args.length) return false;
  return args.every((a) => {
    const norm = a.replace(/\\/g, "/").replace(/\/+$/, "");
    if (/^([A-Za-z]:)?\/?(tmp|temp)\//i.test(norm)) return true;
    if (/[\\/]Temp[\\/]/i.test(a)) return true;
    return REGENERABLE.some(
      (r) => norm === r || norm.endsWith("/" + r) || norm.startsWith(r + "/") || norm.includes("/" + r + "/")
    );
  });
}

const LOCAL_K8S = /\b(docker-desktop|minikube|kind-|rancher-desktop|k3d-|colima)\b/i;

function isCarvedOut(cmd, dangerClass) {
  // npm publish --dry-run, or publishing to a local registry
  if (/\bnpm\s+publish\b/i.test(cmd) && /(--dry-run|--registry[= ]https?:\/\/(localhost|127\.0\.0\.1))/i.test(cmd)) {
    return "npm publish dry-run / local registry";
  }
  // kubectl / docker against an obviously local context
  if (LOCAL_K8S.test(cmd)) return "local cluster context";
  // rm -rf where every target is a regenerable build artefact
  if (dangerClass === "destructive-fs" && /\brm\b/i.test(cmd) && rmTargetsAllRegenerable(cmd)) {
    return "rm targets are all regenerable build artefacts";
  }
  return null;
}

// ---------------------------------------------------------------------------
// Test / build / lint runners — used only by the PostToolUse triage hook
// ---------------------------------------------------------------------------

const RUNNER =
  /\b(pytest|jest|vitest|mocha|go\s+test|mvn|gradle|gradlew|tsc|ruff|eslint|flake8|mypy|pylint|dotnet\s+test|playwright\s+test|cargo\s+(test|build|check)|rspec|phpunit|tox|nox)\b/i;
const RUNNER_VIA_PM =
  /\b(npm|pnpm|yarn|bun)\s+(run\s+)?(test|build|lint|typecheck|type-check|check)\b/i;

function isTestRunner(cmd) {
  return RUNNER.test(cmd) || RUNNER_VIA_PM.test(cmd);
}

// ---------------------------------------------------------------------------
// The public entry point
// ---------------------------------------------------------------------------

// Returns null when the command is fine to run unprompted, or
// { dangerClass, matched, family } when it needs a preview first.
function classifyCommand(cmd) {
  if (!cmd || typeof cmd !== "string") return null;

  // Git publishing outranks even the probes — see GIT_PUBLISH.
  const pub = gitPublish(cmd);
  if (pub) return { dangerClass: "git-publish", matched: pub, family: "git" };

  // Probes always win over everything else.
  if (isReadOnlyProbe(cmd)) return null;

  const fams = familiesIn(cmd);

  // --- database writes: conjunctive (family AND verb) ---
  const dbFamily = fams.find((f) => DB_FAMILIES.has(f));
  if (dbFamily) {
    if (WRITE_VERB.test(cmd)) {
      const verb = cmd.match(WRITE_VERB);
      return { dangerClass: "db-write", matched: verb[0].toUpperCase(), family: dbFamily };
    }
    if (MIGRATION_VERB.test(cmd)) {
      const verb = cmd.match(MIGRATION_VERB);
      return { dangerClass: "db-write", matched: verb[0], family: dbFamily };
    }
  }

  // --- destructive filesystem / git ---
  for (const [re, label] of DESTRUCTIVE_FS) {
    if (re.test(cmd)) {
      // --force-with-lease refuses rather than overwrites; that is the safe form.
      if (/--force-with-lease/i.test(cmd)) continue;
      if (isCarvedOut(cmd, "destructive-fs")) return null;
      return { dangerClass: "destructive-fs", matched: label, family: fams[0] || "" };
    }
  }

  // --- destructive infrastructure ---
  for (const [re, label] of DESTRUCTIVE_INFRA) {
    if (re.test(cmd)) {
      if (isCarvedOut(cmd, "destructive-infra")) return null;
      return { dangerClass: "destructive-infra", matched: label, family: fams[0] || "" };
    }
  }

  // --- opaque wrappers around the above ---
  if (WRAPPER_TARGET.test(cmd)) {
    const m = cmd.match(WRAPPER_TARGET);
    return { dangerClass: "opaque-wrapper", matched: m[0].trim(), family: fams[0] || "" };
  }

  return null;
}

module.exports = {
  classifyCommand,
  gitPublish,
  isReadOnlyProbe,
  isTestRunner,
  splitSegments,
  familiesIn,
};
