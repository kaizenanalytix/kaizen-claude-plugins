# Testing middleware-enforced, request-signed auth

`conftest.py`'s `dependency_overrides` mechanism — used everywhere else in this
skill to swap in test doubles — only intercepts `Depends()`-injected
dependencies. **It cannot bypass auth enforced by Starlette middleware.** If a
project verifies requests via middleware (a signed-request scheme checking a
header against an HMAC computed from the request itself, for example) rather
than a per-route `Depends()` check, `dependency_overrides` simply never runs for
it — the middleware sees every test request exactly as it would see a real one.

This matters for two different layers, for the same underlying reason:

- **Integration tests** (`assets/conftest.py`'s `client` fixture) hit real
  routes through real middleware — a request missing the right signature gets
  a real 401 from the middleware, not from anything this skill's fixtures do.
- **Contract tests** (`references/contract-testing.md`'s Schemathesis layer)
  generate a request per operation in the schema — every one of those has to
  carry a valid signature, or every one fails identically regardless of what
  the test is actually trying to check.

## A static header doesn't work here

A bearer token is the same value on every request, so a single `auth_headers`
fixture value works for as many requests as needed. A signature is computed
**over the request itself** — method, path, body, a timestamp — so it's
different for every request and has to be recomputed each time, not baked into
a fixture once.

```python
import hashlib
import hmac
import time

TEST_HMAC_SECRET = "test-secret-do-not-use-in-prod"  # matches the test app's config


def sign_request(method: str, path: str, body: bytes, timestamp: str) -> str:
    """Mirrors the backend's own signing-middleware logic -- keep this in
    lockstep with the real implementation, not a separate guess at what it
    checks. If the middleware's signing scheme changes, this must change with
    it, or every test starts failing for a reason that has nothing to do with
    what it's actually testing."""
    payload = f"{method}:{path}:{timestamp}:{body.decode()}"
    return hmac.new(TEST_HMAC_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
```

Applied to an integration test:

```python
async def test_create_order_with_signed_request(client):
    timestamp = str(int(time.time()))
    body = b'{"product_id": "widget-1", "quantity": 1}'
    signature = sign_request("POST", "/api/v1/orders", body, timestamp)

    response = await client.post(
        "/api/v1/orders",
        content=body,
        headers={"X-Signature": signature, "X-Timestamp": timestamp},
    )

    assert response.status_code == 201
```

Applied to a contract test — every generated case needs its own signature,
computed from that case's own method/path/body, not a fixture shared across all
of them:

```python
@schema.parametrize()
def test_api_conforms_to_schema(case):
    timestamp = str(int(time.time()))
    body = case.body or b""
    signature = sign_request(case.method, case.path, body, timestamp)
    headers = {"X-Signature": signature, "X-Timestamp": timestamp}

    response = case.call(headers=headers)
    case.validate_response(response)
```

## Two rules that matter more than the code above

- **Prefer real, correctly-computed headers over bypassing the middleware.**
  The examples above are the default, not a fallback — they're what actually
  proves the real auth path works end to end, not just the business logic
  sitting behind it.
- **A middleware-skip escape hatch, if a project adds one, is narrow and named,
  never silent.** Occasionally a large integration suite genuinely needs to
  test business logic in isolation from its own signing middleware, because
  computing a real signature on every one of hundreds of requests is
  prohibitively slow. If that's added, it's an explicit, clearly-labeled flag —
  `create_app(skip_auth_middleware=True)`, used only in a specifically-marked
  subset of tests — **never** wired into the default `client`/`db_session`
  fixtures every other test in the suite already relies on. State the
  consequence in the same place the flag is defined: any test using it cannot
  catch a real bug in the middleware itself (a broken signature check, a
  timing/replay issue). Auth enforcement itself must still be covered by at
  least one test using genuinely computed headers — deliberately sending a
  wrong signature and asserting a 401 — since that's the only way anything
  actually verifies the middleware is doing its job.
