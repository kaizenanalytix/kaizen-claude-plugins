# Outline — API / Interface Specification

**Type:** Conditional. Generate when the system exposes or consumes APIs / service interfaces
(API, endpoint, REST/GraphQL, webhook, third-party integration).
**Output:** `API Specification.docx` in the `design/` folder.

```
API / INTERFACE SPECIFICATION
[Client] [Project] · Version 1.0 · Author: [Tech Lead] · Date: [today] · Status: Draft

Document Control (Version History; Reviewers)

1. INTRODUCTION
   1.1 Purpose · 1.2 Scope · 1.3 Related documents (BRD, Back-end Design, Front-end, Security)

2. REQUIREMENTS TRACEABILITY
   [Table: Req ID | Requirement (short) | Endpoint(s) | Section ref]

3. API OVERVIEW
   3.1 Style (REST / GraphQL / gRPC / events) + version (exact)
   3.2 Base URL / environments · 3.3 Versioning strategy · 3.4 Conventions (naming, paging, errors)

4. AUTHENTICATION & AUTHORISATION
   Scheme (OAuth2 / API key / JWT…), token lifecycle, scopes/roles.
   (Full security model is in the Security Design doc — reference it.)

5. ENDPOINT CATALOGUE
   5.0 Summary [Table: Method | Path | Description | Auth | Owning module]
   For each endpoint (5.N):
     5.N.1 Purpose
     5.N.2 Request  — path/query params, headers, body schema (with example)
     5.N.3 Response — success schema + example, status codes
     5.N.4 Errors   [Table: Code | Meaning | When]
     5.N.5 Rate limits / idempotency / pagination as applicable

6. SHARED SCHEMAS / DATA CONTRACTS
   Reusable request/response objects. Align field names with the data model where relevant.

7. WEBHOOKS / EVENTS (if any)
   [Table: Event | Trigger | Payload schema | Delivery/retry]

8. NON-FUNCTIONAL (API)
   Latency targets (cross-ref NFRs), throughput, deprecation policy.
```

**Notes**
- If interfaces are only inbound integrations (no exposed API), consider merging into Integration
  Design instead — the skill offers this when the signal is thin.
- Keep auth details thin here and authoritative in Security Design.
