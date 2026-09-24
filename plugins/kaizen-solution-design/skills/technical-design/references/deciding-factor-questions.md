# Deciding-Factor Question Bank

The **mandatory interview** the skill runs with the solution architect **before** generating any
document content (SKILL.md Step 3). The architect's answers are the source of truth for the
technology and approach written into the documents — they override anything inferred and are
recorded verbatim in the **Design Decisions Register** (Overview doc).

## Rules for asking

- **Always run the interview** before content generation — even when the source docs look complete.
  When a value is already found in the technical checklist, SOW, or existing docs, pre-fill it
  as the **proposed answer** and ask the architect to **confirm or override**, rather than asking
  cold. Show the source next to each pre-filled answer.
- **Ask only what's relevant** to the confirmed document set. Skip a question block whose document
  was not selected in Step 2 (e.g. don't ask front-end questions if no Front-end Design is being
  generated).
- **Batch the questions** (use `AskUserQuestion` where available). Group by block; offer sensible
  options with a recommended default, and always allow a free-text/"decide later" answer.
- **Never invent a decision.** If the architect defers a question, that value becomes `[TO CONFIRM]`
  in the documents — it is not guessed.
- Record every answer (chosen value, source = architect / technical checklist / SOW, and any rationale the architect
  gives) in the Design Decisions Register.

---

## Block A — Global decisions (ALWAYS asked)

Consumed by the Overview + most child docs.

| # | Decision | Typical options / examples | Written into |
|---|---|---|---|
| A1 | Architecture style | Monolith · Modular monolith · Microservices · Serverless / event-driven | Overview §3, Back-end §3.1 |
| A2 | Cloud / hosting platform + region(s) | AWS · Azure · GCP · Snowflake-native · on-prem / hybrid | Overview §3.3, Infra §3 |
| A3 | Primary language(s) & runtime + version | Python 3.12 · Node 20 · Java 21 · .NET 8 … | Overview §3.3, Back-end §3.2 |
| A4 | Environments | dev / test / staging / prod (which exist) | Infra §3.3 |
| A5 | Deployment / release strategy | Blue-green · Canary · Rolling · manual | Infra §6 |
| A6 | Authentication approach & identity provider | Entra ID · Okta · Cognito · custom | Security §3.1, API §4 |
| A7 | Compliance / data-residency regime | None stated · GDPR · HIPAA · SOC 2 · other | Security §8 |
| A8 | Key third-party / build-vs-buy calls | e.g. buy an auth service, use a managed warehouse | Overview §6, relevant doc |

---

## Block B — Front-end / UI (only if Front-end Design is in the set)

| # | Decision | Typical options | Written into |
|---|---|---|---|
| B1 | Framework + version | React 18 · Angular 17 · Vue 3 · Blazor … | Front-end §5 |
| B2 | Rendering model | SPA · SSR · SSG · hybrid | Front-end §5 |
| B3 | State management | Redux · Zustand · Context · NgRx … | Front-end §6 |
| B4 | Design system / component library | MUI · Ant · Tailwind + custom · client system | Front-end §5 |
| B5 | Accessibility target | WCAG 2.1 AA · other · none stated | Front-end §8 |
| B6 | Browser / device support | evergreen only · specific matrix | Front-end §9 |

---

## Block C — API / Interface (only if API Specification is in the set)

| # | Decision | Typical options | Written into |
|---|---|---|---|
| C1 | API style | REST · GraphQL · gRPC · event/webhook | API §3.1 |
| C2 | Auth scheme | OAuth2 · API key · JWT · mTLS | API §4 (detail in Security) |
| C3 | Versioning strategy | URI (/v1) · header · none | API §3.3 |
| C4 | Payload conventions | JSON casing, paging style, error format | API §3.4 |

---

## Block D — Integration (only if Integration Design is in the set)

| # | Decision | Typical options | Written into |
|---|---|---|---|
| DI1 | Integration style | Sync request/response · Async messaging · Batch/file · CDC/streaming | Integration §4 |
| DI2 | Messaging / streaming tech | Kafka · SQS/SNS · Service Bus · none | Integration §4 |
| DI3 | Error/reconciliation approach | Retry+DLQ · reconciliation job · manual | Integration §5 |

---

## Block E — Processing / Algorithm / ML (only if that doc is in the set)

| # | Decision | Typical options | Written into |
|---|---|---|---|
| E1 | Processing mode | Batch · Streaming · On-request | Processing §3.2 |
| E2 | ML framework + version (if ML) | scikit-learn · XGBoost · PyTorch · none | Processing §5 |
| E3 | Model hosting / serving | Batch scoring · real-time endpoint · embedded | Processing §5 |
| E4 | Retraining & monitoring cadence | on-demand · scheduled · drift-triggered | Processing §5 |

---

## Block F — Back-end (universal — always in the set)

| # | Decision | Typical options | Written into |
|---|---|---|---|
| F1 | Back-end framework + version | FastAPI · Spring Boot · Express · Django … | Back-end §3.2 |
| F2 | Data access approach | ORM (which) · query builder · raw SQL | Back-end §5 |
| F3 | Async / background processing | queue+workers · scheduler · none | Back-end §6/§7 |

---

## Block G — Infrastructure & Deployment (universal — always in the set)

| # | Decision | Typical options | Written into |
|---|---|---|---|
| G1 | IaC tooling + version | Terraform · Bicep · CloudFormation · none | Infra §4 |
| G2 | Compute / runtime | Containers (K8s/ECS) · Serverless · VMs | Infra §5 |
| G3 | CI/CD tooling | GitHub Actions · Azure DevOps · GitLab CI | Infra §6 |
| G4 | Observability stack | CloudWatch · Datadog · Grafana/Prometheus · ELK | Infra §8 |
| G5 | Backup / DR targets (RPO/RTO) | values or [TO CONFIRM] | Infra §7 |

---

## Block H — Security (universal — always in the set)

Most security decisions come from A6/A7; add these only if not already answered.

| # | Decision | Typical options | Written into |
|---|---|---|---|
| H1 | Secrets management | Vault · AWS Secrets Manager · Key Vault | Security §4.3 |
| H2 | Encryption standards | TLS 1.2+/1.3 · at-rest algorithm/key location | Security §4.2 |
| H3 | Data classification present? | PII/PHI/confidential — reference data model | Security §4.1 |

---

## After the interview

Compile the answers into the **Design Decisions Register** (Overview §6). Each generated document
then draws its technology/approach statements from this register — so the whole set is internally
consistent — and any deferred decision is written as `[TO CONFIRM]` with the owner noted.
