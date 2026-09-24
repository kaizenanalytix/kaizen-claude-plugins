# Kaizen Claude Plugins

[![Validate marketplace](https://github.com/rohituddagiri-kaizenglobal/kaizen-claude-plugins/actions/workflows/validate.yml/badge.svg)](https://github.com/rohituddagiri-kaizenglobal/kaizen-claude-plugins/actions/workflows/validate.yml)

The Kaizen Analytix plugin marketplace for **Claude Code** and **Claude Cowork**. The plugins
teach Claude how Kaizen works: the Project Delivery Process (PDP) from sales handoff to closeout,
our full-stack engineering conventions, and client-specific data tooling.

**Marketplace name:** `kaizen-plugins` · **15 plugins** · **Owner:** Kaizen Analytix LLC

---

## Quick start

In Claude Code, add the marketplace once:

```
/plugin marketplace add rohituddagiri-kaizenglobal/kaizen-claude-plugins
```

Then browse and install from the `/plugin` menu, or install directly:

```
/plugin install kaizen-pdp-foundation@kaizen-plugins
```

Restart Claude Code after installing. Skills trigger automatically when what you ask matches
their description; you can also call one explicitly, e.g. `/kaizen-solution-design:data-model`.

> If this repo is private, you need read access to it and working git credentials
> (`gh auth login` is the easiest way). For background auto-updates of a private repo, also set
> `GITHUB_TOKEN` in your environment.

---

## Plugins

### Delivery — the Kaizen PDP lifecycle

Install `kaizen-pdp-foundation` first; the other PDP plugins build on its folder structure and
guardrails.

| Plugin | Phase | What it does |
|---|---|---|
| [kaizen-pdp-foundation](plugins/kaizen-pdp-foundation) | All | Project onboarding (standard folders, checklists, report card), guardrails, file conventions, the PDP phase reference |
| [kaizen-sales-handoff](plugins/kaizen-sales-handoff) | 0 – 1 | KT brief, kickoff deck and project plan, initial backlog pushed to Jira, RAID log and RACI chart |
| [kaizen-solution-design](plugins/kaizen-solution-design) | Analyze & Design | BRD, technical design, data models, E2E / data-flow / sequence / architecture diagrams, design handoff |
| [kaizen-project-governance](plugins/kaizen-project-governance) | Governance | Status reports from the plan and Jira, governance scorecard |
| [kaizen-project-delivery](plugins/kaizen-project-delivery) | Build | Sprint and monthly review summaries from Jira |
| [kaizen-project-closeout](plugins/kaizen-project-closeout) | Closure | Support plan, client sign-off, case study, lessons learned, archive |

### Engineering — full-stack conventions

A suite that works together; see the [full-stack guide](docs/full-stack-guide.md) for how the
pieces connect.

| Plugin | What it does |
|---|---|
| [architecture-foundations](plugins/architecture-foundations) | Stack-agnostic architecture principles, greenfield kickoff, adopt-vs-defer for existing codebases (ships hooks) |
| [codebase-map](plugins/codebase-map) | Cached, git-checkpointed map of the codebase so skills orient without re-reading it (ships hooks) |
| [design-system](plugins/design-system) | Typography scale, design tokens, breakpoints, Tailwind adapter |
| [frontend](plugins/frontend) | React (Vite, React Router, RTK Query, shadcn/ui, Vitest), plus Vue and Angular adapters |
| [backend](plugins/backend) | Clean-architecture FastAPI, plus Node.js, NestJS, Django and Spring adapters |
| [api-contract](plugins/api-contract) | OpenAPI as the single source of truth, typed DTOs for both sides |
| [e2e-testing](plugins/e2e-testing) | Cross-stack Playwright tests from UI to database |
| [deployment](plugins/deployment) | Deployment shape, Dockerfiles, CI/CD, environments, secrets, rollback |

### Data

| Plugin | What it does |
|---|---|
| [kvantum-data-prep](plugins/kvantum-data-prep) | Kvantum Element X pre-load prep: intake, reconciliation, validation gate, template fill, input-review dashboard |

---

## Rolling it out to a team

**Everyone on a project gets the plugins on clone.** Commit a `.claude/settings.json` to the
project repo that registers the marketplace and enables what that repo needs. Start from
[`templates/project-settings.json`](templates/project-settings.json) and trim it:

```json
{
  "extraKnownMarketplaces": {
    "kaizen-plugins": {
      "source": { "source": "github", "repo": "rohituddagiri-kaizenglobal/kaizen-claude-plugins" }
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

Plugins only update when their `version` is bumped, so every change here ships with a version
bump. Each plugin's version is in its `.claude-plugin/plugin.json`.

## Repository layout

```
.claude-plugin/marketplace.json   the catalog of all plugins
plugins/                          one folder per plugin
docs/                             cross-plugin guides
templates/                        settings files to copy into project repos
scripts/validate.mjs              consistency checks run in CI
.github/                          CI workflow, PR template, code owners
```

## Contributing

New plugins and fixes are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) for the conventions
and how to test a plugin locally before opening a PR.
