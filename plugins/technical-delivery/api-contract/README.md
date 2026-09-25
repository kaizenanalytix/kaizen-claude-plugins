# api-contract

The seam between a sibling `frontend` plugin and a sibling `backend` plugin:
the single source of truth for data shapes crossing the boundary. Depends on
nothing at runtime; consumed by both domain plugins at build/dev time.

Unlike `architecture-foundations`, this plugin's skill ships runnable tooling,
not just concepts — that functional difference (does something vs. teaches
something) is why it's a separate plugin rather than a fourth foundations
skill.

## Components

| Skill | Purpose |
|---|---|
| `contract-first` | Generates typed DTOs for both sides from one OpenAPI schema (backend-first + CI diff gate), so frontend and backend never drift. Includes runnable `generate_types.py` and `diff_schema.py` scripts. |

## Setup

Python 3.10+ and a running/exported FastAPI `openapi.json` to point the scripts at.

## Usage

- "Define the API contract" / "generate API types" / "sync frontend and backend types" → `contract-first`
