# Outline — Security Design

**Type:** Universal (always generated). The authoritative security document for the solution.
**Output:** `Security Design.docx` in the `design/` folder.
Other docs (API Spec, Integration, Back-end) reference this one for auth/security detail.

```
SECURITY DESIGN
[Client] [Project] · Version 1.0 · Author: [Security Lead / Architect] · Date: [today] · Status: Draft

Document Control (Version History; Reviewers)

1. INTRODUCTION
   1.1 Purpose · 1.2 Scope · 1.3 Related documents (BRD NFRs, Overview, API Spec, Infra & Deployment)

2. REQUIREMENTS TRACEABILITY
   [Table: Req ID | Requirement (short, esp. security/compliance NFRs) | Control | Section ref]

3. IDENTITY & ACCESS
   3.1 Authentication (mechanism, IdP, MFA, sessions/tokens + lifetimes)
   3.2 Authorisation (RBAC/ABAC, roles ↔ permissions) [Table: Role | Permissions | Resource]
   3.3 Service-to-service / machine identity

4. DATA PROTECTION
   4.1 Classification (PII/PHI/confidential) — reference the data model
   4.2 Encryption in transit (TLS versions) and at rest (algorithm, key location)
   4.3 Secrets management (vault/KMS, rotation)
   4.4 Data retention, masking/anonymisation, right-to-erasure if applicable

5. APPLICATION SECURITY
   Input validation, output encoding, OWASP Top 10 posture, dependency/vulnerability scanning,
   SAST/DAST in the pipeline (cross-ref Infra & Deployment CI/CD).

6. NETWORK & INFRASTRUCTURE SECURITY
   Segmentation, firewalls/security groups, private endpoints, WAF — coordinate with Infra & Deployment.

7. LOGGING, AUDIT & MONITORING
   Security events logged, audit trail, alerting (cross-ref Infra & Deployment observability).

8. COMPLIANCE & GOVERNANCE
   Applicable regimes (GDPR/HIPAA/SOC2/etc.), controls mapping, data-residency constraints.

9. THREAT MODEL & RISKS
   [Table: Threat | Vector | Likelihood/Impact | Mitigation | Status]

10. OPEN ITEMS  [Table: ID | Item | [TO CONFIRM] | Owner]
```

**Notes**
- This doc is authoritative for security; elsewhere keep auth/security thin and link here.
- If no compliance regime is stated, mark §8 `[TO CONFIRM]` rather than assuming none applies.
