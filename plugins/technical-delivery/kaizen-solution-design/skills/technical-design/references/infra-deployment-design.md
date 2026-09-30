# Outline — Infrastructure & Deployment Design

**Type:** Universal (always generated). The design-time infrastructure & deployment topology.
This is the *design* view (how it's provisioned and shipped), not a runtime operations runbook.
**Output:** `Infrastructure & Deployment Design.docx` in the `design/` folder.

```
INFRASTRUCTURE & DEPLOYMENT DESIGN
[Client] [Project] · Version 1.0 · Author: [DevOps / Platform Lead] · Date: [today] · Status: Draft

Document Control (Version History; Reviewers)

1. INTRODUCTION
   1.1 Purpose · 1.2 Scope · 1.3 Related documents (BRD NFRs, Overview, Back-end, Security)

2. REQUIREMENTS TRACEABILITY
   [Table: Req ID | Requirement (short, esp. availability/scalability/perf NFRs) | Infra element | Section ref]

3. TARGET ENVIRONMENT
   3.1 Cloud / platform (provider, regions) — exact services + tiers
   3.2 Topology (network, subnets, compute, data stores, gateways) — describe; cross-ref the
       solution overview diagram rather than redrawing
   3.3 Environment matrix [Table: Environment | Purpose | Sizing | Config source | URL]

4. INFRASTRUCTURE AS CODE
   Tooling (Terraform/Bicep/CloudFormation + version), module/repo layout, state management.

5. COMPUTE & RUNTIME
   Containers/serverless/VMs, orchestration (K8s/etc. + version), image strategy, runtime config.

6. CI/CD PIPELINE
   6.1 Stages: Build → Test → Scan → Package → Deploy → Verify
   6.2 [Table: Stage | Tool | Gate/criteria]
   6.3 Promotion & release strategy (blue-green / canary / rolling), rollback approach

7. SCALING & RESILIENCE
   Auto-scaling triggers, HA topology, backup/DR (RPO/RTO — cross-ref availability NFRs).

8. OBSERVABILITY
   8.1 Metrics [Table: Metric | Threshold | Alert channel]
   8.2 Logging & tracing stack · 8.3 Dashboards · 8.4 On-call/alert routing (design-level)

9. COST & CAPACITY (optional)
   Rough sizing/cost drivers — no financial figures computed (keep financial figures verbatim); mark [FINANCIAL — EL].

10. RISKS & OPEN ITEMS  [Table: ID | Item | Mitigation / [TO CONFIRM] | Priority]
```

**Notes**
- Design-time topology only. A runtime support/hypercare runbook belongs to a delivery/closeout
  skill, not here.
- Security controls on the infrastructure are authoritative in Security Design — coordinate, link.
