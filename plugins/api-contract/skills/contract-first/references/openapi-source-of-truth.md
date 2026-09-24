# OpenAPI as the Source of Truth

## Backend-first + diff gate (recommended default)

The backend is the one place that actually implements the API, so let it be
the one place that describes it. In FastAPI:

```python
from fastapi import FastAPI

app = FastAPI(title="My Service", version="1.4.0")

# ... routers, models, dependencies ...

if __name__ == "__main__":
    import json
    with open("openapi.json", "w") as f:
        json.dump(app.openapi(), f, indent=2)
```

Or simply hit the app's own `/openapi.json` endpoint (FastAPI serves this
automatically) during a build/export step:

```bash
curl http://localhost:8000/openapi.json -o openapi.json
```

Either way, `openapi.json` is:
1. **Generated**, not hand-maintained — it can never drift from the real
   route definitions, request/response models, and status codes, because it
   is derived directly from them.
2. **Committed as a build artifact.** Check it into version control (e.g.
   `contracts/openapi.json` in a shared repo, or published to a package
   registry/artifact store consumable by the frontend build). This gives you
   a diffable history of the contract itself, independent of the backend's
   implementation history.
3. **The only thing the frontend build depends on.** The frontend never reads
   backend source — it reads this one file.

### Full pipeline

```
FastAPI app (routes + Pydantic models)
        │
        │  app.openapi()  /  GET /openapi.json
        ▼
   openapi.json  ──────────────► committed as build artifact
        │
        │  scripts/generate_types.py
        ▼
  ┌─────────────┴─────────────┐
  ▼                           ▼
TS interfaces           Pydantic-compatible types
(frontend repo/package,  (other backend services that
 imported, never          federate/consume this service's
 hand-edited)              schema, never hand-edited)
```

On every backend PR, `openapi.json` is regenerated and diffed against the
previously committed version (see `diff_schema.py` and
`breaking-change-policy.md`). That diff — not code review of the backend
implementation — is what actually catches contract drift, because it
compares the artifact both sides depend on, not the implementation either
side happens to have today.

## Schema-first (alternative, use when appropriate)

Sometimes the API shape needs to be agreed on *before* anyone writes
implementation code:
- Multi-vendor integrations where several teams implement against the same
  spec independently.
- Public or partner-facing APIs where the contract is effectively a legal/
  support commitment and needs sign-off before implementation.
- Greenfield projects where frontend and backend teams want to parallelize
  work from day one.

In this mode, someone hand-authors the OpenAPI document in a tool like
Stoplight Studio or Swagger Editor. That hand-authored file *is* the
contract. The backend is then expected to implement routes/models that match
it (validated with the same `diff_schema.py`, run in the other direction —
diffing the backend's actual emitted schema against the hand-authored one to
catch implementation drift), and the frontend generates types from it exactly
as in the backend-first flow.

## Recommendation

Default to backend-first + diff gate. It has zero risk of the schema
describing something that doesn't exist, requires no separate design tool,
and fits naturally into a normal PR-based workflow. Reach for schema-first
only when the API must be negotiated as a deliverable in its own right before
implementation starts.
