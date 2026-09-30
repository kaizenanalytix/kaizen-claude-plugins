// PreToolUse hook (Edit|Write|NotebookEdit): blocks writing to an existing codebase
// until this project/discipline has gone through the existing-codebase-adoption
// skill — which also triggers codebase-map-sync (see that skill's step 1a). Without
// this, nothing forces either the map or the adopt-vs-defer decision to exist before
// code gets written to someone else's project.
//
// Fails open everywhere it's uncertain: no file path, no git repo, no resolvable
// discipline, no HEAD yet (pre-first-commit greenfield), a tiny scaffold (<=20 files,
// matching project-kickoff's own "seeding is free" threshold), or any script error.
// A hook that blocks incorrectly is worse than no hook at all.

const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

function allow() {
  process.exit(0);
}

function block(message) {
  process.stderr.write(message + "\n");
  process.exit(2);
}

function git(cwd, args) {
  return execSync(`git ${args}`, { cwd, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
}

const DISCIPLINE_EXTS = {
  frontend: [".ts", ".tsx", ".js", ".jsx", ".vue", ".css", ".scss"],
  backend: [".py", ".java", ".kt", ".ts", ".js"],
};

// Walks up from the touched file looking for the nearest manifest that identifies
// a stack. Returns { discipline, scopeDir } — scopeDir is the directory the
// tracked-file count should be scoped to (the manifest's own folder), so a monorepo
// with separate frontend/ and backend/ package.json files doesn't have one side's
// file count bleed into the other's. A manifest resolving a discipline is not
// enough on its own — README.md, .env, and lockfiles sitting next to that same
// manifest aren't source files for it, so every match is also checked against
// the touched file's own extension before being returned.
function classify(filePath, projectRoot) {
  const ext = path.extname(filePath).toLowerCase();
  const absFile = path.isAbsolute(filePath) ? filePath : path.join(projectRoot, filePath);
  let dir = path.dirname(absFile);
  const root = path.resolve(projectRoot);

  function matchIfSource(discipline, scopeDir) {
    return DISCIPLINE_EXTS[discipline].includes(ext) ? { discipline, scopeDir } : null;
  }

  for (let i = 0; i < 25; i++) {
    const pkgPath = path.join(dir, "package.json");
    if (fs.existsSync(pkgPath)) {
      try {
        const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf8"));
        const deps = Object.assign({}, pkg.dependencies, pkg.devDependencies);
        if (deps.vue || deps["@angular/core"] || deps.next || deps.react) {
          return matchIfSource("frontend", dir);
        }
        if (deps["@nestjs/core"] || deps.express || deps.fastify) {
          return matchIfSource("backend", dir);
        }
      } catch {
        // corrupt/unreadable package.json — fall through to the extension fallback below
      }
      break; // nearest package.json found but inconclusive; don't keep walking past it
    }
    if (fs.existsSync(path.join(dir, "manage.py"))) {
      return matchIfSource("backend", dir);
    }
    if (
      fs.existsSync(path.join(dir, "pyproject.toml")) ||
      fs.existsSync(path.join(dir, "requirements.txt")) ||
      fs.existsSync(path.join(dir, "pom.xml")) ||
      fs.existsSync(path.join(dir, "build.gradle")) ||
      fs.existsSync(path.join(dir, "build.gradle.kts"))
    ) {
      return matchIfSource("backend", dir);
    }
    if (dir === root || dir === path.dirname(dir)) break;
    dir = path.dirname(dir);
  }

  // No manifest resolved anything. Only guess from extension where it's
  // unambiguous — .ts/.js/.vue with no manifest could be either side of a Node
  // frontend/backend split, so those stay unresolved rather than guessed.
  if (ext === ".py" || ext === ".java" || ext === ".kt") {
    return { discipline: "backend", scopeDir: null };
  }
  if (ext === ".vue") {
    return { discipline: "frontend", scopeDir: null };
  }
  return null;
}

function countTrackedFiles(projectRoot, scopeDir, discipline) {
  const relScope = scopeDir ? path.relative(projectRoot, scopeDir) : "";
  const listArgs = relScope ? `ls-files -- "${relScope}"` : "ls-files";
  const files = git(projectRoot, listArgs).split("\n").filter(Boolean);
  const exts = DISCIPLINE_EXTS[discipline] || [];
  return files.filter((f) => exts.includes(path.extname(f).toLowerCase())).length;
}

try {
  const raw = fs.readFileSync(0, "utf8");
  const input = JSON.parse(raw);
  const toolInput = input.tool_input || {};
  const file = toolInput.file_path || toolInput.notebook_path;
  if (!file) allow();

  if (/[\\/](node_modules|dist|build|\.git|\.kaizen)[\\/]/.test(file)) allow();

  const projectRoot = input.cwd || process.cwd();

  try {
    if (git(projectRoot, "rev-parse --is-inside-work-tree") !== "true") allow();
  } catch {
    allow();
  }

  const classified = classify(file, projectRoot);
  if (!classified) allow();
  const { discipline, scopeDir } = classified;

  const adoptionPath = path.join(projectRoot, ".kaizen", "adoption.json");
  if (fs.existsSync(adoptionPath)) {
    try {
      const adoption = JSON.parse(fs.readFileSync(adoptionPath, "utf8"));
      if (adoption[discipline] && adoption[discipline].decision) allow();
    } catch {
      allow(); // corrupt adoption.json isn't this hook's problem to fix
    }
  }

  let head;
  try {
    head = git(projectRoot, "rev-parse HEAD");
  } catch {
    allow(); // no commits yet — greenfield / pre-kickoff
  }

  const trackedCount = countTrackedFiles(projectRoot, scopeDir, discipline);
  if (trackedCount <= 20) allow(); // matches project-kickoff's own "seeding ~20 files is free"

  block(
    `Editing ${path.relative(projectRoot, file)} touches an existing ${discipline} codebase ` +
      `(${trackedCount} tracked ${discipline} files, no .kaizen/adoption.json entry for "${discipline}"). ` +
      `Run the architecture-foundations plugin's existing-codebase-adoption skill first — it also ` +
      `triggers codebase-map-sync — then retry this edit.`
  );
} catch {
  allow();
}
