# Contract testing

Contract tests check that what the API *actually returns* conforms to its
declared OpenAPI schema — this is the layer that catches frontend/backend
drift, which unit and integration tests don't, since integration tests
only assert against example payloads the test author wrote by hand.

## Schemathesis against the app's own OpenAPI schema

```python
import schemathesis

schema = schemathesis.openapi.from_dict(app.openapi())


@schema.parametrize()
def test_api_conforms_to_schema(case, auth_headers):
    response = case.call(headers=auth_headers)
    case.validate_response(response)
```

Build the schema from `app.openapi()` directly, in-memory — not by hitting
`/openapi.json` over ASGI. `app.openapi()` always works regardless of the
app's config; the `/openapi.json` *route* only exists when `openapi_url` is
set, and `fastapi-project-bootstrap`'s `app.py` disables it whenever
`debug=False` (the default), specifically so it isn't exposed outside
development. Contract tests shouldn't depend on a route that's deliberately
absent in a production-shaped app instance.

**Pass auth headers into every generated case — don't call `case.call()`
bare.** Schemathesis generates a case for *every* operation the schema
declares. If most of those routes require auth (the normal case), an
unauthenticated `case.call()` gets a 401/403 on nearly everything, which
tells you nothing about whether the API actually conforms to its schema.
Reuse `assets/conftest.py`'s `auth_headers` fixture — Schemathesis's
`@schema.parametrize()` functions are ordinary pytest tests and can take
other fixtures as parameters, exactly as shown above.

A single, uniformly-applied `auth_headers` fixture covers the common case:
one auth scheme, or a scheme where sending a valid token to a public route
is harmless. It does **not** cover an API with genuinely role-varying
endpoints (an admin-only `DELETE` alongside public `GET`s) — for that,
group operations by required role using Schemathesis's own per-operation
filtering (`case.operation`) into separate parametrized test functions, one
per role, rather than forcing one fixture to satisfy every endpoint.

**If auth is enforced by middleware rather than a `Depends()`-based check**
(a signed-request scheme, HMAC-style — not just a bearer token), a static
header won't work at all, since the signature has to be computed over the
actual request being sent. Read `references/testing-custom-auth.md` before
assuming `auth_headers` alone is enough.

This property-based-tests every operation in the schema: for each
endpoint, Schemathesis generates inputs from the declared parameter/body
schemas and asserts the response matches the declared response schema
(status codes, required fields, types) — not just one example case.

## Preferring the `api-contract` plugin's schema, when present

If a sibling `api-contract` plugin's `contract-first` skill owns the canonical
OpenAPI/Pydantic schema definitions (e.g. because the frontend generates
its types from that same schema), point Schemathesis at that schema
instead of the FastAPI app's self-generated one:

```python
schema = schemathesis.openapi.from_path("path/to/api-contract/openapi.json")
schema = schema.configure(base_url="http://localhost:8000")
```

Running contract tests against the shared schema (rather than each side's
own generated copy) is what actually catches drift — if the backend
silently changes a response shape without updating the shared contract,
this is the test that fails, before a frontend consumer ever notices at
runtime.

## Where this fits in CI

Run contract tests after integration tests, against a running instance of
the app (or via `from_asgi`, which doesn't need a live server). Treat a
contract test failure as equivalent in severity to a broken integration
test — it means a real consumer of the API would break, even though every
hand-written example-based test still passes.
