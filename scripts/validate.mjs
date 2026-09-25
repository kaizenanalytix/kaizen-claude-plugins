#!/usr/bin/env node
// Repo-level consistency checks for the Kaizen plugin marketplace.
// Complements `claude plugin validate`, which checks each manifest's schema
// but not whether the marketplace and the folders on disk agree.
//
// Usage:
//   node scripts/validate.mjs                  check only (CI)
//   node scripts/validate.mjs --fix            rewrite marketplace.json to match the folders
//   node scripts/validate.mjs --base origin/main   also require version bumps for changed plugins
//
// Layout it expects:
//   plugins/<vertical>/<plugin>/.claude-plugin/plugin.json   a full plugin
//   skills/<vertical>/<skill>/SKILL.md                       a standalone skill; every vertical's
//                                                            skills publish as one "<vertical>-skills" plugin

import { execFileSync } from "node:child_process";
import { existsSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { join, relative, resolve } from "node:path";

const ROOT = resolve(import.meta.dirname, "..");
const MARKETPLACE = join(ROOT, ".claude-plugin", "marketplace.json");
const KEBAB = /^[a-z0-9]+(-[a-z0-9]+)*$/;
const SEMVER = /^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$/;

const args = process.argv.slice(2);
const FIX = args.includes("--fix");
const BASE = args.includes("--base") ? args[args.indexOf("--base") + 1] : null;

const errors = [];
const warnings = [];
const fixes = [];
const rel = (p) => relative(ROOT, p).replaceAll("\\", "/");
const subdirs = (dir) =>
  existsSync(dir) ? readdirSync(dir).filter((d) => statSync(join(dir, d)).isDirectory()).sort() : [];

function readJson(path) {
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch (e) {
    errors.push(`${rel(path)}: ${e.message}`);
    return null;
  }
}

function frontmatter(path) {
  const text = readFileSync(path, "utf8").replace(/^﻿/, "");
  const match = text.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!match) return null;
  const fields = {};
  for (const line of match[1].split(/\r?\n/)) {
    const kv = line.match(/^([A-Za-z_-]+):\s*(.*)$/);
    if (kv) fields[kv[1]] = kv[2].trim();
  }
  return fields;
}

function checkSkill(skillDir) {
  const skillFile = join(skillDir, "SKILL.md");
  const folder = skillDir.split(/[\\/]/).pop();
  if (!existsSync(skillFile)) return errors.push(`${rel(skillDir)}: missing SKILL.md`);
  const fm = frontmatter(skillFile);
  if (!fm) return errors.push(`${rel(skillFile)}: missing YAML frontmatter`);
  if (!fm.name) errors.push(`${rel(skillFile)}: frontmatter has no name`);
  else if (fm.name !== folder) warnings.push(`${rel(skillFile)}: name "${fm.name}" differs from folder "${folder}"`);
  if (!("description" in fm)) errors.push(`${rel(skillFile)}: frontmatter has no description`);
}

function checkHooks(root) {
  const hooksFile = join(root, "hooks", "hooks.json");
  if (!existsSync(hooksFile)) return;
  const hooks = readJson(hooksFile);
  for (const [, target] of JSON.stringify(hooks ?? {}).matchAll(/\$\{CLAUDE_PLUGIN_ROOT\}\/([^"\\\s]+)/g)) {
    if (!existsSync(join(root, target))) errors.push(`${rel(hooksFile)}: references missing file ${target}`);
  }
}

// --- discover what is on disk -------------------------------------------
const pluginVerticals = subdirs(join(ROOT, "plugins"));
const skillVerticals = subdirs(join(ROOT, "skills"));
for (const v of [...pluginVerticals, ...skillVerticals]) {
  if (!KEBAB.test(v)) errors.push(`vertical "${v}" is not kebab-case`);
}
for (const v of skillVerticals) {
  if (!pluginVerticals.includes(v)) warnings.push(`skills/${v} has no matching plugins/${v} vertical`);
}

const onDisk = new Map(); // name -> { vertical, dir, manifest }
for (const vertical of pluginVerticals) {
  for (const name of subdirs(join(ROOT, "plugins", vertical))) {
    const dir = join(ROOT, "plugins", vertical, name);
    const manifestPath = join(dir, ".claude-plugin", "plugin.json");
    if (!existsSync(manifestPath)) {
      errors.push(`${rel(dir)}: no .claude-plugin/plugin.json (plugins go in plugins/<vertical>/<plugin>/)`);
      continue;
    }
    if (onDisk.has(name)) errors.push(`plugin "${name}" exists in two verticals`);
    onDisk.set(name, { vertical, dir, manifest: readJson(manifestPath) });
  }
}

const packs = new Map(); // "<vertical>-skills" -> { vertical, skills }
for (const vertical of skillVerticals) {
  const skills = subdirs(join(ROOT, "skills", vertical));
  if (skills.length) packs.set(`${vertical}-skills`, { vertical, skills });
}
for (const name of packs.keys()) {
  if (onDisk.has(name)) errors.push(`skill pack "${name}" collides with a plugin of the same name`);
}

// --- marketplace --------------------------------------------------------
const marketplace = readJson(MARKETPLACE);
if (!marketplace) {
  console.error(errors.join("\n"));
  process.exit(1);
}

if (FIX) {
  const kept = [];
  for (const entry of marketplace.plugins) {
    const plugin = onDisk.get(entry.name);
    const pack = packs.get(entry.name);
    if (plugin) {
      Object.assign(entry, { source: `./plugins/${plugin.vertical}/${entry.name}`, category: plugin.vertical });
      kept.push(entry);
    } else if (pack) {
      Object.assign(entry, {
        source: `./skills/${pack.vertical}`,
        strict: false,
        category: pack.vertical,
        skills: pack.skills.map((s) => `./${s}`),
      });
      kept.push(entry);
    } else {
      fixes.push(`removed "${entry.name}" (no longer on disk)`);
    }
  }
  const listedNames = new Set(kept.map((e) => e.name));
  for (const [name, plugin] of onDisk) {
    if (listedNames.has(name)) continue;
    kept.push({
      name,
      source: `./plugins/${plugin.vertical}/${name}`,
      description: plugin.manifest?.description ?? "",
      category: plugin.vertical,
    });
    fixes.push(`added plugin "${name}" (review its description and add keywords)`);
  }
  for (const [name, pack] of packs) {
    if (listedNames.has(name)) continue;
    kept.push({
      name,
      source: `./skills/${pack.vertical}`,
      strict: false,
      version: "1.0.0",
      description: `Standalone ${pack.vertical.replaceAll("-", " ")} skills.`,
      category: pack.vertical,
      skills: pack.skills.map((s) => `./${s}`),
    });
    fixes.push(`added skill pack "${name}" (review its description)`);
  }
  marketplace.plugins = kept;
  writeFileSync(MARKETPLACE, JSON.stringify(marketplace, null, 2) + "\n");
}

const listed = new Map();
for (const entry of marketplace.plugins ?? []) {
  if (listed.has(entry.name)) errors.push(`marketplace: duplicate entry "${entry.name}"`);
  listed.set(entry.name, entry);
  if (!KEBAB.test(entry.name)) errors.push(`marketplace: "${entry.name}" is not kebab-case`);
  if (!entry.description) errors.push(`marketplace: "${entry.name}" has no description`);

  const plugin = onDisk.get(entry.name);
  const pack = packs.get(entry.name);
  if (plugin) {
    const expected = `./plugins/${plugin.vertical}/${entry.name}`;
    if (entry.source !== expected) errors.push(`marketplace: "${entry.name}" source should be "${expected}"`);
    if (entry.category !== plugin.vertical) errors.push(`marketplace: "${entry.name}" category should be "${plugin.vertical}"`);
  } else if (pack) {
    const expected = pack.skills.map((s) => `./${s}`);
    if (entry.source !== `./skills/${pack.vertical}`) errors.push(`marketplace: "${entry.name}" source should be "./skills/${pack.vertical}"`);
    if (entry.strict !== false) errors.push(`marketplace: "${entry.name}" needs "strict": false`);
    if (!entry.version || !SEMVER.test(entry.version)) errors.push(`marketplace: "${entry.name}" needs a semver version`);
    if (JSON.stringify([...(entry.skills ?? [])].sort()) !== JSON.stringify(expected)) {
      errors.push(`marketplace: "${entry.name}" skills list is out of date with skills/${pack.vertical}/`);
    }
  } else {
    errors.push(`marketplace: "${entry.name}" has no matching folder on disk`);
  }
}
for (const name of onDisk.keys()) if (!listed.has(name)) errors.push(`plugin "${name}" is not listed in marketplace.json`);
for (const name of packs.keys()) if (!listed.has(name)) errors.push(`skill pack "${name}" is not listed in marketplace.json`);

// --- per-plugin and per-skill checks ------------------------------------
for (const [name, { dir, manifest }] of onDisk) {
  if (manifest) {
    if (manifest.name !== name) errors.push(`${rel(dir)}: plugin.json name is "${manifest.name}"`);
    if (!manifest.version) errors.push(`${rel(dir)}: plugin.json has no version`);
    else if (!SEMVER.test(manifest.version)) errors.push(`${rel(dir)}: version "${manifest.version}" is not semver`);
    if (!manifest.description) errors.push(`${rel(dir)}: plugin.json has no description`);
  }
  if (!existsSync(join(dir, "README.md"))) warnings.push(`${rel(dir)}: no README.md`);
  for (const skill of subdirs(join(dir, "skills"))) checkSkill(join(dir, "skills", skill));
  checkHooks(dir);
}
for (const { vertical, skills } of packs.values()) {
  for (const skill of skills) checkSkill(join(ROOT, "skills", vertical, skill));
}

// --- version bumps (CI on pull requests) --------------------------------
if (BASE) {
  const git = (...a) => execFileSync("git", a, { cwd: ROOT, encoding: "utf8" });
  const showAtBase = (path) => {
    try {
      return JSON.parse(git("show", `${BASE}:${path}`));
    } catch {
      return null;
    }
  };
  // Pure moves (R100) and a plugin's own README don't change what users
  // receive, so they don't need a bump.
  const changed = git("diff", "--name-status", "-M", `${BASE}...HEAD`)
    .split("\n")
    .filter((l) => l && !l.startsWith("R100"))
    .map((l) => l.split("\t").pop())
    .filter((f) => !/^plugins\/[^/]+\/[^/]+\/README\.md$/.test(f));

  const baseMarketplace = showAtBase(".claude-plugin/marketplace.json");
  const baseVersion = (name) => baseMarketplace?.plugins?.find((p) => p.name === name)?.version;

  for (const [name, { vertical, manifest }] of onDisk) {
    const prefix = `plugins/${vertical}/${name}/`;
    if (!changed.some((f) => f.startsWith(prefix))) continue;
    // Look the plugin up where the base catalog had it, so a plugin that
    // moved vertical in this change is still compared with its old version.
    const baseSource = baseMarketplace?.plugins?.find((p) => p.name === name)?.source?.replace(/^\.\//, "");
    const before = showAtBase(`${baseSource ?? prefix.slice(0, -1)}/.claude-plugin/plugin.json`);
    if (before && before.version === manifest?.version) {
      errors.push(`${prefix}: changed but version is still ${before.version} — bump it in plugin.json`);
    }
  }
  for (const [name, { vertical }] of packs) {
    if (!changed.some((f) => f.startsWith(`skills/${vertical}/`))) continue;
    const before = baseVersion(name);
    if (before && before === listed.get(name)?.version) {
      errors.push(`skills/${vertical}/: changed but "${name}" version is still ${before} — bump it in marketplace.json`);
    }
  }
}

// --- report -------------------------------------------------------------
for (const f of fixes) console.log(`fixed  ${f}`);
for (const w of warnings) console.warn(`warn   ${w}`);
for (const e of errors) console.error(`error  ${e}`);
console.log(`\n${onDisk.size} plugins, ${packs.size} skill packs, ${errors.length} error(s), ${warnings.length} warning(s)`);
process.exit(errors.length ? 1 : 0);
