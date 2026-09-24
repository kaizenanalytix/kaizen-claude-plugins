# Contributing

Thanks for improving the Kaizen plugins. This guide covers how the repo is laid out, how to add
or change a plugin, and how to test before you open a pull request.

## Repo layout

```
.claude-plugin/marketplace.json   the catalog: every plugin must be listed here
plugins/<plugin-name>/            one folder per plugin
├── .claude-plugin/plugin.json    manifest: name, version, description, author
├── README.md                     what it does, its skills, how it fits with the rest
├── skills/<skill-name>/SKILL.md  one folder per skill (plus references/, scripts/, templates/)
├── hooks/hooks.json              optional
└── .mcp.json                     optional
docs/                             cross-plugin guides
templates/                        settings files people copy into their own repos
scripts/validate.mjs              repo consistency checks (runs in CI)
```

## Rules of the road

- **Plugin folder name = `plugin.json` name = marketplace entry name**, all kebab-case. The
  validator enforces this.
- **Bump the version on every change.** Claude Code only delivers an update when a plugin's
  `version` changes. Use semver: patch for wording fixes, minor for new skills or behavior,
  major for renamed/removed skills or changed outputs.
- **Never rename a plugin or skill casually.** People enable plugins as `name@kaizen-plugins` and
  invoke skills as `/plugin:skill`. A rename silently breaks both.
- **Reference bundled files through `${CLAUDE_PLUGIN_ROOT}`**, never absolute or `../` paths out
  of the plugin. Installed plugins are copied to a cache, so anything outside the plugin folder
  does not exist at runtime.
- **No client data or secrets.** Templates and example configs only. Credentials go in the
  user's environment, never in a plugin.

## Adding a plugin

1. Create `plugins/<name>/.claude-plugin/plugin.json`:

   ```json
   {
     "name": "<name>",
     "displayName": "<Human Name>",
     "version": "0.1.0",
     "description": "One or two sentences on what it helps people do.",
     "author": { "name": "Kaizen Analytix LLC" }
   }
   ```

2. Add skills under `plugins/<name>/skills/<skill-name>/SKILL.md`, each with `name` and
   `description` frontmatter. The description is what Claude matches against, so end it with the
   phrases people actually say ("Trigger on: ...").
3. Write `plugins/<name>/README.md` (copy the shape of an existing one).
4. Add an entry to `.claude-plugin/marketplace.json` with `name`, `source`
   (`./plugins/<name>`), a one-line `description`, a `category` (`delivery`, `engineering` or
   `data`) and `keywords`.
5. Add it to the plugin table in the root `README.md`.

## Testing locally

Point Claude Code at your working copy instead of GitHub:

```bash
claude plugin marketplace add ./
```

```bash
claude plugin install <plugin-name>@kaizen-plugins
```

Restart Claude Code, then try the skill with the phrases from its description. After further
edits, run `/plugin marketplace update kaizen-plugins` and restart to pick them up.

Before pushing:

```bash
node scripts/validate.mjs
```

```bash
claude plugin validate .
```

Plugins with their own test suites (currently `kvantum-data-prep`) run them in CI too.

## Pull requests

Branch from `main`, keep one plugin per PR where you can, and fill in the PR checklist. CI must
pass and a code owner must approve before merge.
