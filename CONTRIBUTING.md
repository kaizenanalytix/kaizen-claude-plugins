# Contributing

This repo is where the ET team publishes Kaizen's plugins, standalone skills and MCP connectors.
This guide covers where each kind of thing goes, how to add one, and how to test it before you
open a pull request.

## Repo layout

```
.claude-plugin/marketplace.json            the catalog (kept in sync by scripts/validate.mjs --fix)
plugins/<vertical>/<plugin>/               a full plugin
├── .claude-plugin/plugin.json             manifest: name, version, description, author
├── README.md                              what it does, its skills, how it fits with the rest
├── skills/<skill>/SKILL.md                its skills (plus references/, scripts/, templates/)
├── hooks/hooks.json                       optional
└── .mcp.json                              optional MCP servers
skills/<vertical>/<skill>/SKILL.md         a standalone skill (plus any assets/ or scripts/)
docs/                                      cross-plugin guides
templates/                                 settings files people copy into their own repos
scripts/validate.mjs                       catalog sync + consistency checks (runs in CI)
```

**Verticals:** `general-productivity`, `operations`, `sales-marketing`, `technical-delivery`.
A new vertical is just a new folder under `plugins/` (and `skills/`) plus a code-owner entry.

## Which one am I adding?

| You have… | Put it in | Users install |
|---|---|---|
| One self-contained skill | `skills/<vertical>/<skill>/` | `<vertical>-skills@kaizen-plugins` (one pack per vertical) |
| Several skills that work together, or anything with hooks | `plugins/<vertical>/<plugin>/` | `<plugin>@kaizen-plugins` |
| An MCP connector | `plugins/<vertical>/<connector>/` with a `.mcp.json` | `<connector>@kaizen-plugins` |

Rule of thumb: start a skill in `skills/`. Promote it to a plugin once it grows companions, needs
hooks, or people want to install it on its own.

## Adding a standalone skill

1. Create `skills/<vertical>/<skill-name>/SKILL.md` with `name` (matching the folder) and
   `description` frontmatter. The description is what Claude matches against, so include the
   phrases people actually say. Put any files the skill needs next to it (e.g. `assets/`).
2. Run `node scripts/validate.mjs --fix`. It adds the skill to that vertical's
   `<vertical>-skills` entry in `marketplace.json`, and creates the entry if this is the
   vertical's first skill.
3. Bump that pack's `version` in `marketplace.json`, and update its `description` if the new
   skill changes what the pack is for.
4. Add it to the vertical's table in the root `README.md`.

## Adding a plugin

1. Create `plugins/<vertical>/<name>/.claude-plugin/plugin.json`:

   ```json
   {
     "name": "<name>",
     "displayName": "<Human Name>",
     "version": "0.1.0",
     "description": "One or two sentences on what it helps people do.",
     "author": { "name": "Kaizen Analytix LLC" }
   }
   ```

2. Add skills under `plugins/<vertical>/<name>/skills/<skill-name>/SKILL.md`.
3. Write `plugins/<vertical>/<name>/README.md` (copy the shape of an existing one).
4. Run `node scripts/validate.mjs --fix` to add it to `marketplace.json`, then tighten the
   generated `description` to one line and add `keywords`.
5. Add it to the vertical's table in the root `README.md`.

## Adding an MCP connector

A connector is a plugin whose main content is a `.mcp.json`. Follow **Adding a plugin**, and put
the server definition at `plugins/<vertical>/<name>/.mcp.json`:

```json
{
  "mcpServers": {
    "<server-name>": {
      "type": "http",
      "url": "https://<host>/mcp"
    }
  }
}
```

For a local server, use `"command"` / `"args"` and reference bundled files as
`${CLAUDE_PLUGIN_ROOT}/...`. **Never commit tokens or keys.** Reference them as `${ENV_VAR}` and
document in the README which variables people need to set.

## Rules of the road

- **Folder name = manifest name = catalog entry name**, all kebab-case. The validator enforces
  this.
- **Bump the version on every change.** Claude Code only delivers an update when the version
  changes: `plugin.json` for plugins, `marketplace.json` for skill packs. Use semver: patch for
  wording fixes, minor for new skills or behavior, major for renamed/removed skills or changed
  outputs. CI rejects a PR that changes content without a bump.
- **Moving between verticals is free.** Names don't include the vertical, so a move doesn't
  affect anyone who has it installed. Run `--fix` afterwards to update the catalog.
- **Never rename a plugin or skill casually.** People enable plugins as `name@kaizen-plugins` and
  invoke skills as `/plugin:skill`. A rename silently breaks both.
- **Stay inside your folder.** Installed plugins and skill packs are copied to a cache, so
  anything outside their own folder doesn't exist at runtime. In plugins, reference bundled files
  through `${CLAUDE_PLUGIN_ROOT}`.
- **No client data or secrets.** Templates and example configs only.

## Testing locally

Point Claude Code at your working copy instead of GitHub:

```bash
claude plugin marketplace add ./
```

```bash
claude plugin install <name>@kaizen-plugins
```

Restart Claude Code, then try the skill with the phrases from its description. After further
edits, run `/plugin marketplace update kaizen-plugins` and restart to pick them up.

Before pushing:

```bash
node scripts/validate.mjs --base origin/main
```

```bash
claude plugin validate .
```

Plugins with their own test suites (currently `kvantum-data-prep`) run them in CI too.

## Pull requests

Branch from `main`, keep one plugin or skill per PR where you can, and fill in the PR checklist.
CI must pass and a code owner must approve before merge.
