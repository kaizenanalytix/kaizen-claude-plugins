# Concern → skill map (expanded)

Use this table to route a request to the right skill once you've applied
the three-zone model. Each row gives trigger phrasing, what the skill
actually does, and why it's the right fit.

| Concern | Trigger phrases (examples) | Skill | Why this skill |
|---|---|---|---|
| Starting a brand-new domain area inside an existing app | "add a module", "new feature", "new domain", "scaffold the X module" | `fastapi-module-scaffold` | Creates the standard five-folder module skeleton and wires it into `core/app.py` and `core/container.py` in one pass, so every module starts from the same shape. |
| Adding a single endpoint, a repository, or DI wiring | "add an endpoint", "add a repository", "wire up the database", "dependency injection", "business logic goes where" | `fastapi-data-layer` | Owns the repository-interface / service / DI patterns — the actual mechanics of getting data in and out through the right layer. |
| Exposing, versioning, or securing HTTP routes | "add a route", "set up routing", "protect an endpoint", "version the API" | `fastapi-routing` | Owns `APIRouter` mounting conventions, prefix/versioning constants, and the `Depends(get_current_user)` auth pattern. |
| Writing any kind of test | "write tests", "test this service/repository/route", "add integration tests" | `fastapi-testing` | Owns the test pyramid mapped onto Pytest/an async httpx client/Schemathesis, plus shared fixtures. |
| Standing up a new project from nothing | "new FastAPI project", "set up the backend", "configure the project" | `fastapi-project-bootstrap` | Owns the actual starter files (`pyproject.toml`, `settings.py`, `app.py`) that the other 5 skills assume already exist. |
| "Where does this code belong" / general structure questions | "structure my backend", "where does this code belong", "set up the API architecture" | `backend-architecture` (this skill) | Stays here — it's the orchestrator, not a hand-off target. |

If a request spans more than one row (e.g. "add a new module with tests
and an authenticated endpoint"), apply `fastapi-module-scaffold` first for
the skeleton, then `fastapi-routing` for the endpoint, then
`fastapi-testing` for coverage — in that order, since later steps depend on
the module existing.
