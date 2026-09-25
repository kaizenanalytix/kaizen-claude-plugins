# PDP Foundation

**Version 1.2.0** · Kaizen Analytix LLC

The shared foundation every Kaizen delivery plugin builds on. It sets up a new project's standard
folder structure and checklists in SharePoint/OneDrive (or brings an existing project into line),
keeps file naming and organization consistent, and applies common safeguards such as approval and
confirmation steps before important actions. It also serves as the reference for how a Kaizen
project is structured across its phases.

## Skills

| Skill | What it does |
|---|---|
| [guardrails](skills/guardrails/README.md) | Reference-only single source of truth for the mandatory guardrails (G1–G5) and file conventions (F1–F3) every PDP delivery skill must follow. |
| [kaizen-pdp-phases](skills/kaizen-pdp-phases/README.md) | Interactive reference for the PDP checklist — phases, mandatory items, gate logic, and what to do next. Does not generate documents. |
| [project-onboarding](skills/project-onboarding/README.md) | Scaffolds a new project's 9 PDP phase folders, per-phase checklists, and Project Report Card (greenfield), or reorganises an existing project into a PDP-compliant structure (brownfield). |
| [generate-report-card](skills/generate-report-card/README.md) | Read-only re-scan of an already-onboarded project that refreshes the Project Report Card (Dashboard + D1–D41 tracker) to match what's on disk. |

## How it fits the Kaizen PDP

This is the **foundation** layer: every other Kaizen delivery plugin (sales handoff, solution
design, project governance, delivery, closeout) references the guardrails and file conventions
defined here, writes into the phase folders that `project-onboarding` creates, and follows the
phase/deliverable taxonomy documented in `kaizen-pdp-phases`. `guardrails` and `kaizen-pdp-phases`
are read-only references; `project-onboarding` and `generate-report-card` do the deterministic
work of standing up and tracking the on-disk project structure.

Typical flow: run **project-onboarding** once to scaffold or reorganise a project (it builds the
first Report Card), then run **generate-report-card** for a fast status refresh on every later
re-scan.

## Requirements / dependencies

- Python 3 with `openpyxl` (for the `project-onboarding` and `generate-report-card` scripts):
  `pip install openpyxl --break-system-packages` if missing.
- A project root following the F1 convention `[Client Familiar Name] [Timing] [Project Name]`,
  optionally with a `.kaizen-project.json` carrying `PROJECT_ID` and `engagement_type`.
