# Kaizen Claude Plugins

[![Validate marketplace](https://github.com/kaizenanalytix/kaizen-claude-plugins/actions/workflows/validate.yml/badge.svg)](https://github.com/kaizenanalytix/kaizen-claude-plugins/actions/workflows/validate.yml)

The Kaizen Analytix marketplace for **Claude Code** and **Claude Cowork**: the one place where
Kaizen's plugins, standalone skills and MCP connectors are published and maintained. Everything
is organized by company vertical.

**Marketplace name:** `kaizen-plugins` · **Owner:** Kaizen Analytix LLC

---

## Quick start

In Claude Code, add the marketplace once:

```
/plugin marketplace add kaizenanalytix/kaizen-claude-plugins
```

Then browse and install from the `/plugin` menu, or install directly:

```
/plugin install general-productivity-skills@kaizen-plugins
```

Restart Claude Code after installing. Skills trigger automatically when what you ask matches
their description; you can also call one explicitly, e.g. `/kaizen-solution-design:data-model`.

> If this repo is private, you need read access to it and working git credentials
> (`gh auth login` is the easiest way). For background auto-updates of a private repo, also set
> `GITHUB_TOKEN` in your environment.

---

## What's available

Three kinds of things are published here. All of them install the same way, with
`/plugin install <name>@kaizen-plugins`:

- **Plugins** (`plugins/<vertical>/`): a bundle of related skills, and sometimes hooks or MCP
  connectors, that work together.
- **Skill packs** (`skills/<vertical>/`): standalone skills that don't belong to a plugin. Each
  vertical's skills are published together as one `<vertical>-skills` pack.
- **Connectors**: MCP servers, published as small plugins whose main content is a `.mcp.json`.

### General productivity

| Name | Type | What it does |
|---|---|---|
| `general-productivity-skills` | Skill pack | `kaizen-pptx-template`: decks built on the Kaizen 2026 branded template · `meeting-brief`: daily/weekly meeting briefs and a rolling action tracker from Teams transcripts |

### Operations: the Kaizen PDP lifecycle

Install `kaizen-pdp-foundation` first; the other PDP plugins build on its folder structure and
guardrails.

| Plugin | Phase | What it does |
|---|---|---|
| [kaizen-pdp-foundation](plugins/operations/kaizen-pdp-foundation) | All | Project onboarding (standard folders, checklists, report card), guardrails, file conventions, the PDP phase reference |
| [kaizen-sales-handoff](plugins/operations/kaizen-sales-handoff) | 0 – 1 | KT brief, kickoff deck and project plan, initial backlog pushed to Jira, RAID log and RACI chart |
| [kaizen-project-governance](plugins/operations/kaizen-project-governance) | Governance | Status reports from the plan and Jira, governance scorecard |
| [kaizen-project-delivery](plugins/operations/kaizen-project-delivery) | Build | Sprint and monthly review summaries from Jira |
| [kaizen-project-closeout](plugins/operations/kaizen-project-closeout) | Closure | Support plan, client sign-off, case study, lessons learned, archive |

### Technical delivery

Solution design, the full-stack engineering suite (see the
[full-stack guide](docs/full-stack-guide.md) for how its pieces connect), data science, and
client data tooling.

| Plugin | What it does |
|---|---|
| [kaizen-solution-design](plugins/technical-delivery/kaizen-solution-design) | BRD, technical design, data models, E2E / data-flow / sequence / architecture diagrams, design handoff |
| [architecture-foundations](plugins/technical-delivery/architecture-foundations) | Stack-agnostic architecture principles, greenfield kickoff, adopt-vs-defer for existing codebases (ships hooks) |
| [codebase-map](plugins/technical-delivery/codebase-map) | Cached, git-checkpointed map of the codebase so skills orient without re-reading it (ships hooks) |
| [design-system](plugins/technical-delivery/design-system) | Typography scale, design tokens, breakpoints, Tailwind adapter |
| [frontend](plugins/technical-delivery/frontend) | React (Vite, React Router, RTK Query, shadcn/ui, Vitest), plus Vue and Angular adapters |
| [backend](plugins/technical-delivery/backend) | Clean-architecture FastAPI, plus Node.js, NestJS, Django and Spring adapters |
| [api-contract](plugins/technical-delivery/api-contract) | OpenAPI as the single source of truth, typed DTOs for both sides |
| [e2e-testing](plugins/technical-delivery/e2e-testing) | Cross-stack Playwright tests from UI to database |
| [deployment](plugins/technical-delivery/deployment) | Deployment shape, Dockerfiles, CI/CD, environments, secrets, rollback |
| [kaizen-data-science](plugins/technical-delivery/kaizen-data-science) | Data exploration, statistics, modeling (predictive, forecasting, Bayesian, optimization), charts, and export to a reproducible Jupyter notebook |
| [kvantum-data-prep](plugins/technical-delivery/kvantum-data-prep) | Kvantum Element X pre-load prep: intake, reconciliation, validation gate, template fill, input-review dashboard |

### Sales & marketing

Nothing published yet. See [CONTRIBUTING.md](CONTRIBUTING.md) to add the first one.

---

## Rolling it out to a team

**Everyone on a project gets the plugins on clone.** Commit a `.claude/settings.json` to the
project repo that registers the marketplace and enables what that repo needs. Start from
[`templates/project-settings.json`](templates/project-settings.json) and trim it:

```json
{
  "extraKnownMarketplaces": {
    "kaizen-plugins": {
      "source": { "source": "github", "repo": "kaizenanalytix/kaizen-claude-plugins" }
    }
  },
  "enabledPlugins": {
    "kaizen-pdp-foundation@kaizen-plugins": true
  }
}
```

Teammates are prompted to trust the marketplace and install the enabled plugins the first time
they open the repo.

**Everyone in the org gets the marketplace.** An admin can put the same `extraKnownMarketplaces`
block in Claude Code's managed settings so every machine knows about `kaizen-plugins` without
anyone running `/plugin marketplace add`.

**Claude Cowork.** An org admin can add this GitHub repo as a plugin marketplace in the
organization's Claude settings so the plugins appear for Cowork users.

---

## Staying up to date

```
/plugin marketplace update kaizen-plugins
```

Something only updates for users when its version is bumped: in `plugin.json` for a plugin, or
in `marketplace.json` for a skill pack. CI blocks a pull request that changes either without a
bump.

## Repository layout

```
.claude-plugin/marketplace.json     the catalog, generated/checked by scripts/validate.mjs
plugins/<vertical>/<plugin>/        full plugins (skills, hooks, MCP connectors)
skills/<vertical>/<skill>/          standalone skills, published as "<vertical>-skills"
docs/                               cross-plugin guides
templates/                          settings files to copy into project repos
scripts/validate.mjs                catalog sync + consistency checks (runs in CI)
.github/                            CI workflow, PR template, code owners
```

Verticals: `general-productivity`, `operations`, `sales-marketing`, `technical-delivery`.

## Contributing

New plugins, skills and connectors are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) for the
conventions and how to test locally before opening a PR.
