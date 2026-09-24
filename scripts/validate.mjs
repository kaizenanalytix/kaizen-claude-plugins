#!/usr/bin/env node
// Repo-level consistency checks for the Kaizen plugin marketplace.
// Complements `claude plugin validate`, which checks each manifest's schema
// but not whether the marketplace and the plugins/ folder agree.
//
// Usage: node scripts/validate.mjs

import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";

const ROOT = resolve(import.meta.dirname, "..");
const PLUGINS_DIR = join(ROOT, "plugins");
const KEBAB = /^[a-z0-9]+(-[a-z0-9]+)*$/;
const SEMVER = /^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$/;

const errors = [];
const warnings = [];
const rel = (p) => relative(ROOT, p).replaceAll("\\", "/");

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

// --- marketplace --------------------------------------------------------
const marketplace = readJson(join(ROOT, ".claude-plugin", "marketplace.json"));
if (!marketplace) {
  console.error(errors.join("\n"));
  process.exit(1);
}

const listed = new Map();
for (const entry of marketplace.plugins ?? []) {
  if (listed.has(entry.name)) errors.push(`marketplace: duplicate plugin "${entry.name}"`);
  listed.set(entry.name, entry);
  if (!KEBAB.test(entry.name)) errors.push(`marketplace: "${entry.name}" is not kebab-case`);
  if (typeof entry.source !== "string" || !entry.source.startsWith("./plugins/")) {
    errors.push(`marketplace: "${entry.name}" source must be "./plugins/<name>"`);
  } else if (entry.source !== `./plugins/${entry.name}`) {
    errors.push(`marketplace: "${entry.name}" source "${entry.source}" does not match its name`);
  }
  if (!entry.description) errors.push(`marketplace: "${entry.name}" has no description`);
  if (!entry.category) warnings.push(`marketplace: "${entry.name}" has no category`);
}

// --- plugins/ -----------------------------------------------------------
const dirs = readdirSync(PLUGINS_DIR).filter((d) => statSync(join(PLUGINS_DIR, d)).isDirectory());

for (const dir of dirs) {
  if (!listed.has(dir)) errors.push(`plugins/${dir}: not listed in .claude-plugin/marketplace.json`);
}

for (const [name] of listed) {
  const root = join(PLUGINS_DIR, name);
  if (!existsSync(root)) {
    errors.push(`marketplace: "${name}" points at a missing folder`);
    continue;
  }

  const manifest = readJson(join(root, ".claude-plugin", "plugin.json"));
  if (manifest) {
    if (manifest.name !== name) errors.push(`plugins/${name}: plugin.json name is "${manifest.name}"`);
    if (!manifest.version) errors.push(`plugins/${name}: plugin.json has no version`);
    else if (!SEMVER.test(manifest.version)) errors.push(`plugins/${name}: version "${manifest.version}" is not semver`);
    if (!manifest.description) errors.push(`plugins/${name}: plugin.json has no description`);
  }

  if (!existsSync(join(root, "README.md"))) warnings.push(`plugins/${name}: no README.md`);

  const skillsDir = join(root, "skills");
  if (existsSync(skillsDir)) {
    for (const skill of readdirSync(skillsDir)) {
      const skillFile = join(skillsDir, skill, "SKILL.md");
      if (!statSync(join(skillsDir, skill)).isDirectory()) continue;
      if (!existsSync(skillFile)) {
        errors.push(`${rel(join(skillsDir, skill))}: missing SKILL.md`);
        continue;
      }
      const fm = frontmatter(skillFile);
      if (!fm) errors.push(`${rel(skillFile)}: missing YAML frontmatter`);
      else {
        if (!fm.name) errors.push(`${rel(skillFile)}: frontmatter has no name`);
        else if (fm.name !== skill) warnings.push(`${rel(skillFile)}: name "${fm.name}" differs from folder "${skill}"`);
        if (!("description" in fm)) errors.push(`${rel(skillFile)}: frontmatter has no description`);
      }
    }
  }

  const hooksFile = join(root, "hooks", "hooks.json");
  if (existsSync(hooksFile)) {
    const hooks = readJson(hooksFile);
    const commands = JSON.stringify(hooks ?? {}).matchAll(/\$\{CLAUDE_PLUGIN_ROOT\}\/([^"\\\s]+)/g);
    for (const [, target] of commands) {
      if (!existsSync(join(root, target))) errors.push(`${rel(hooksFile)}: references missing file ${target}`);
    }
  }
}

// --- report -------------------------------------------------------------
for (const w of warnings) console.warn(`warn   ${w}`);
for (const e of errors) console.error(`error  ${e}`);
console.log(`\n${listed.size} plugins, ${errors.length} error(s), ${warnings.length} warning(s)`);
process.exit(errors.length ? 1 : 0);
