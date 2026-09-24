const fs = require("fs");
const path = require("path");
const os = require("os");
const { execSync } = require("child_process");

const projectRoot = process.cwd();
const projectName = path.basename(projectRoot);
const cachePath = path.join(os.homedir(), ".claude", "kaizen", projectName, "codebase-map.json");

function git(args) {
  return execSync(`git ${args}`, { cwd: projectRoot, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
}

function isGitRepo() {
  try {
    return git("rev-parse --is-inside-work-tree") === "true";
  } catch {
    return false;
  }
}

// Distinguishes "this repo has no commits yet" from "that SHA is gone from history".
// `git rev-parse HEAD` fails in both cases, but they need opposite advice.
function headSha() {
  try {
    return git("rev-parse HEAD");
  } catch {
    return null;
  }
}

function dirtyFileCount() {
  try {
    return git("status --porcelain").split("\n").filter(Boolean).length;
  } catch {
    return 0;
  }
}

if (!fs.existsSync(cachePath)) {
  // Only nudge where a map could actually be built and would actually help:
  // it needs git (the checkpoint is a commit SHA — without one there is nothing
  // to invalidate against), and it needs to look like a real project, since this
  // hook fires on every session including in scratch and non-code directories.
  const looksLikeAProject = ["package.json", "pyproject.toml", "requirements.txt"].some((f) =>
    fs.existsSync(path.join(projectRoot, f))
  );
  if (looksLikeAProject && isGitRepo()) {
    console.log(
      `No cached codebase map exists for "${projectName}" yet. The codebase-map-sync skill can ` +
        `build one at ${cachePath} — it describes each source file once so later sessions can jump ` +
        `straight to the right file instead of re-scanning the repo. Worth doing before any task ` +
        `that needs to explore this codebase; it asks permission first. Skip it if this project ` +
        `already has a hand-maintained skill or CLAUDE.md serving as its structural index. Note: ` +
        `a sibling architecture-foundations plugin's PreToolUse gate may also block edits to an ` +
        `existing, non-trivial codebase for a discipline with no .kaizen/adoption.json entry yet — ` +
        `running existing-codebase-adoption satisfies that gate and triggers this skill together.`
    );
  }
  process.exit(0);
}

let cache;
try {
  cache = JSON.parse(fs.readFileSync(cachePath, "utf8"));
} catch {
  process.exit(0);
}

const disciplines = Object.keys(cache.disciplines || {});
const fileCount = disciplines.reduce((sum, d) => {
  const tree = cache.disciplines[d].tree || {};
  return sum + Object.values(tree).reduce((n, folder) => n + Object.keys(folder.files || {}).length, 0);
}, 0);

let stalenessNote = "";
const lastSha = cache.last_scanned_sha;
const head = headSha();

if (head === null) {
  stalenessNote =
    " NOTE: this repo has no commits yet (no HEAD), so the cache's checkpoint can't be verified — " +
    "make the initial commit, then run codebase-map-sync to seed a checkpointed map.";
} else if (lastSha && lastSha !== head) {
  try {
    git(`merge-base --is-ancestor ${lastSha} HEAD`);
    const changed = git(`diff --name-only ${lastSha} HEAD`).split("\n").filter(Boolean);
    if (changed.length > 0) {
      stalenessNote = ` STALE: ${changed.length} file(s) changed since that scan (run codebase-map-sync to refresh before trusting affected entries).`;
    }
  } catch {
    stalenessNote =
      " STALE: last_scanned_sha is no longer in this repo's history (rebase/force-push) — run codebase-map-sync to reseed.";
  }
}

// The checkpoint is a commit SHA, but editing a file doesn't move HEAD — so a matching
// SHA alone does NOT mean the cache is current. Without this, a working tree full of
// uncommitted edits reports as freshly scanned.
if (!stalenessNote && head !== null) {
  const dirty = dirtyFileCount();
  if (dirty > 0) {
    stalenessNote =
      ` STALE: the scanned commit matches HEAD, but ${dirty} file(s) have uncommitted changes — ` +
      `entries for those files may not reflect what's on disk.`;
  }
}

console.log(
  `A cached codebase map for "${projectName}" exists at ${cachePath} ` +
    `(last scanned at commit ${cache.last_scanned_sha}, disciplines: ${disciplines.join(", ")}, ` +
    `${fileCount} files described).${stalenessNote} For a specific file/feature, grep inside that ` +
    `JSON file for a keyword instead of reading the whole thing or re-scanning with Glob/Grep — each ` +
    `entry sits on its own line with a description attached.`
);
process.exit(0);
