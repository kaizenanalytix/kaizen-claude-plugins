---
name: vite-plugins
description: >
  Provides a decision framework for whether a task actually needs a Vite
  plugin versus just a regular npm dependency, and lists common plugin
  categories without committing to specific packages. Use when the user
  says things like "do I need a vite plugin for this", "add SVG support",
  "vite plugin for X", or "which vite plugins do we need".
---

# Vite Plugins

Use this skill when deciding whether something the project needs requires
adding a Vite plugin, or is better solved as a plain runtime dependency.
This is decision guidance, not a fixed list of plugins to install — it
doesn't commit the project to any specific plugin beyond the one every
setup already needs.

## 1. What a Vite plugin actually is

A Vite plugin hooks into the build/transform pipeline: it can transform
non-JavaScript assets into importable modules, inject or modify code during
the build, or modify the dev server's behavior. A plugin changes *how Vite
processes files* — it operates at build/transform time, not at runtime in
the browser.

## 2. The decision test

Ask: **does this require changing how Vite processes or transforms a
file at build time?**

- **Yes** → it's a Vite plugin candidate. Examples: importing an `.svg`
  file directly as a component, generating a PWA manifest and service
  worker from the build output, visualizing bundle size after a build.
  These all require Vite to do something with a file type or the build
  process itself that it doesn't do out of the box.
- **No, it's just code the app calls at runtime** → it's a regular npm
  dependency, installed and imported normally. Don't reach for a Vite
  plugin just because a library exists that has one — most libraries
  don't need one, and adding a plugin for something that's really just an
  `import` from `node_modules` adds build complexity for no benefit.

Read `references/plugin-decision-guide.md` for a worked table of common
"needs" mapped to the plugin category (not a specific package) they fall
under, if any.

## 3. The one plugin every setup needs

Regardless of which UI framework is in use, that framework has its own
official Vite plugin, and it's expected to already be in the `plugins`
array (e.g. `@vitejs/plugin-vue` for Vue, or the equivalent official
package for whichever other framework the project uses). This skill
doesn't pick one — installing and wiring the correct framework plugin is
the job of that framework's adapter (see `vite-config-basics` for where it
sits in the config).

## 4. Common plugin categories (not a fixed list)

These are categories to recognize when they come up, not a checklist to
install upfront:

- **Asset-as-component transforms** — e.g. importing an SVG file directly
  as a usable component instead of a raw file path/URL.
- **PWA tooling** — generating a manifest and service worker from the
  build so the app can be installed/work offline.
- **Bundle analysis/visualization** — producing a visual breakdown of
  what's inside the production bundle, useful for diagnosing bundle size
  (note: choosing to act on what a bundle analyzer shows is an
  optimization concern, out of scope for this skill — this skill only
  covers recognizing that visualization itself is a plugin-shaped need).

Only add a plugin from one of these categories when there's an actual,
current need for it — not speculatively "because the project might want
that later."

## 5. Plugin ordering

Most plugins don't care about their position in the `plugins` array. When
order does matter, it's typically because a transform plugin needs to run
before or after the framework plugin (e.g. a plugin that rewrites a file
type the framework plugin also touches). Read
`references/plugin-decision-guide.md` for the ordering note; when in
doubt, check the specific plugin's own documentation for an ordering
requirement rather than assuming.

---
_Last reviewed: 2026-08-05_
