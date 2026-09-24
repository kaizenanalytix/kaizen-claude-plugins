# Epic Format Reference

All epics in the project backlog must follow this structure.

## Epic Fields

| Field | Required | Description |
|---|---|---|
| Epic Name | Yes | Short name for the functional area (3-5 words) |
| Epic Key | Yes | Abbreviated identifier used for cross-referencing |
| Summary | Yes | One-line description of what this epic covers |
| Scope | Yes | Bullet list of specific deliverables and work items |
| SOW Mapping | Yes | Which SOW deliverables / line items this epic addresses |
| Acceptance Criteria | Yes | High-level conditions that define "done" for the epic |
| Priority | Yes | Highest / High / Medium / Low |
| Est. Duration | Yes | Rough duration in sprints |
| Dependencies | No | Other epic keys this depends on |

## Grouping Rules

- Group by **function of work** (what the solution does), not by PDP phase or timeline
- Each epic = one cohesive functional area a sub-team could own
- Mutually exclusive scope — no overlap between epics
- Every SOW deliverable maps to exactly one epic

## Mandatory Cross-Cutting Epics

These appear on every engagement regardless of solution type:

1. **Project Governance** — Status reporting, RAID log, RACI, steering committee, change requests
2. **Environment & Infrastructure** — Environment provisioning, access management, CI/CD, deployment

## Priority Guide

| Priority | Criteria |
|---|---|
| Highest | Blocks all other epics; foundational work |
| High | Core solution functionality; on the critical path |
| Medium | Important but not blocking; can start after High items |
| Low | Nice-to-have or can be deferred without impacting delivery |
