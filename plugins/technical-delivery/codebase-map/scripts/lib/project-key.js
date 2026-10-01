// Per-project, per-user state location shared by the Kaizen technical-delivery plugins:
//
//   ~/.claude/kaizen/<project-key>/
//     codebase-map.json   codebase-map
//     adoption.json       architecture-foundations (existing-codebase-adoption)
//     guardrails.json     guardrails (escape hatches), plus guardrails/ state
//
// WHY USER-LEVEL. These files describe how the agent should behave on THIS machine for
// THIS checkout. Written inside the repo they showed up as untracked files in client
// codebases, where nobody wants Kaizen tooling committed.
//
// WHY A HASH IN THE KEY. The key used to be the folder name alone, so two checkouts
// called "frontend" — or two clones of the same repo in different places — shared one
// map and one adoption decision. <folder>-<6 hex of sha1(absolute path)> keeps the
// folder name readable and makes each checkout distinct.
//
// The project root is the nearest ancestor holding .git (so a session opened in a
// subfolder resolves to the same key), falling back to the directory itself. Found by
// walking the filesystem rather than spawning git: this runs in hooks on every tool
// call, and a spawn per call is felt on Windows.
//
// KEEP THIS FILE IDENTICAL in guardrails, architecture-foundations and codebase-map.
// Each plugin has to stand alone, so each carries its own copy; the guardrails self-test
// fails if the copies drift apart.
//
// Run directly to print the directory:  node project-key.js [dir]

"use strict";

const crypto = require("crypto");
const fs = require("fs");
const os = require("os");
const path = require("path");

function projectRoot(start) {
  const from = path.resolve(start || process.cwd());
  let dir = from;
  for (let i = 0; i < 64; i++) {
    if (fs.existsSync(path.join(dir, ".git"))) return dir;
    const up = path.dirname(dir);
    if (up === dir) break;
    dir = up;
  }
  return from;
}

function projectKey(start) {
  const root = projectRoot(start);
  let norm = root.split(path.sep).join("/").replace(/\/+$/, "");
  if (process.platform === "win32") norm = norm.toLowerCase();
  const hash = crypto.createHash("sha1").update(norm).digest("hex").slice(0, 6);
  const name = (path.basename(root) || "root").replace(/[^A-Za-z0-9._-]/g, "_");
  return `${name}-${hash}`;
}

function kaizenDir(start) {
  return path.join(os.homedir(), ".claude", "kaizen", projectKey(start));
}

// Where these files lived before project keys: inside the repo under .kaizen/, and
// under the bare folder name. Read as a fallback so existing decisions and maps
// aren't lost; never written to.
function legacyPaths(start, file) {
  const root = projectRoot(start);
  return [
    path.join(root, ".kaizen", file),
    path.join(os.homedir(), ".claude", "kaizen", path.basename(root), file),
  ];
}

// First existing path: the current location, then the legacy ones. null if none.
function findFile(start, file) {
  const candidates = [path.join(kaizenDir(start), file)].concat(legacyPaths(start, file));
  for (const p of candidates) {
    try {
      if (fs.existsSync(p)) return p;
    } catch {
      // unreadable location is simply not a candidate
    }
  }
  return null;
}

module.exports = { projectRoot, projectKey, kaizenDir, legacyPaths, findFile };

if (require.main === module) {
  console.log(kaizenDir(process.argv[2]));
}
