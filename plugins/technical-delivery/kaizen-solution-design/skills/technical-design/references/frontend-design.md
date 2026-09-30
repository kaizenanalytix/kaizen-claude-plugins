# Outline — Front-end / UI Design

**Type:** Conditional. Generate when the requirements show a user-facing UI (screens, dashboard,
portal, web/mobile app, UX, wireframes, usability/accessibility NFRs).
**Output:** `Front-end Design.docx` in the `design/` folder.

```
FRONT-END / UI DESIGN
[Client] [Project] · Version 1.0 · Author: [Front-end Lead] · Date: [today] · Status: Draft

Document Control (Version History; Reviewers)

1. INTRODUCTION
   1.1 Purpose · 1.2 Scope · 1.3 Related documents (BRD, Overview, API Spec)

2. REQUIREMENTS TRACEABILITY
   [Table: Req ID | Requirement (short) | UI element / screen | Section ref]

3. UX OVERVIEW
   3.1 Target users / personas (from BRD stakeholders)
   3.2 Information architecture / navigation map
   3.3 Key user journeys [Table: Journey | Steps | Screens involved]

4. SCREEN / COMPONENT INVENTORY
   [Table: Screen/View | Purpose | Key components | Data shown | API(s) called]

5. COMPONENT DESIGN
   For each significant component: responsibility, state, props/inputs, events/outputs,
   reuse notes. Reference the front-end framework + version (exact).

6. STATE MANAGEMENT & DATA FLOW (client-side)
   Store/state approach, caching, optimistic updates, error/loading states.

7. UI-TO-API CONTRACT
   How the front-end consumes the API Specification (endpoints per screen, auth handling).
   [Table: Screen/Action | Endpoint | Method | Notes]  — must align with the API Spec doc.

8. ACCESSIBILITY & RESPONSIVENESS
   WCAG target, breakpoints, keyboard/screen-reader considerations, i18n if required.

9. NON-FUNCTIONAL (front-end)
   Performance budgets (bundle size, TTI), browser/device support matrix.

10. RISKS & OPEN ITEMS  [Table: ID | Item | Mitigation / [TO CONFIRM] | Priority]
```

**Notes**
- If there is no UI in scope, this document is not generated — do not stub it.
- Section 7 must be consistent with the API Specification doc; cross-reference, don't restate.
