# Test-case documentation format

Document every designed scenario in this format before implementation:

```
Test ID:
Feature:
Scenario:
Preconditions:
Test Data:
Steps:
Expected Result:
Priority:
Automation Candidate:
Test Type:
```

## Field notes

- **Test ID** — a short prefix tied to the feature (`LOGIN-`, `ORDER-`,
  `CHECKOUT-`) plus a zero-padded sequence number. Keeps scenarios
  referenceable in bug reports, PRs, and CI output.
- **Priority** — use the standard order from the main skill: critical
  business workflows > authentication > payments/transactions > data
  creation/modification > permissions > integrations > error handling >
  regression > edge cases > cosmetic UI.
- **Automation Candidate** — Yes/No/Manual-only. A scenario that requires
  human visual judgment (e.g. "does this look right on a real device") is a
  legitimate "No" — don't force everything into Playwright just because
  this plugin exists.
- **Test Type** — End-to-End / API / Integration / Unit. Most scenarios
  designed with this skill are End-to-End, but a scenario might reveal that
  part of what it's checking is really API-only (route to `backend`'s
  `fastapi-testing`) or component-only (route to `frontend`'s
  `react-testing`).

## Worked example

```
Test ID: LOGIN-001

Feature:
Authentication

Scenario:
Valid customer login

Preconditions:
Active customer account exists.

Test Data:
customer@example.com / a valid, unexpired password

Steps:
1. Open login page.
2. Enter valid email.
3. Enter valid password.
4. Click Login.

Expected Result:
- Login API returns 200 with a session/access token.
- User is redirected to the dashboard.
- The customer's name appears in the header.
- A subsequent authenticated API call succeeds using the created session.

Priority:
Critical

Automation Candidate:
Yes

Test Type:
End-to-End
```

Note the last line of Expected Result: it verifies the session actually
works for a follow-up call, not just that the redirect happened — that's
the difference between checking the UI looked right and checking the
business result (an authenticated session) actually exists.

---
_Last reviewed: 2026-08-07_
