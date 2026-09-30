# Reporting

Use this module when producing executive summaries, technical summaries, recommendations, or structured findings.

## What this supports

- Technical summaries
- Executive summaries
- Recommendations
- Assumptions and limitations
- Next steps

Templates are available in `templates/executive-summary.md` and `templates/technical-summary.md`.

## Using the templates

When the user asks for a **named** report type ("executive summary", "technical summary"), follow the matching template's section structure rather than inventing an ad hoc layout — fill every section, and write "None found" / "Not applicable" where a section is empty rather than dropping it. For casual or one-line questions, do not force a full template; match the requested detail level (see first behavior point below).

- **Executive summary** → use `templates/executive-summary.md` (Objective · Key Findings · Business Implications · Risks/Limitations · Recommendations · Next Steps).
- **Technical summary** → use `templates/technical-summary.md`, and **populate its "Verification Notes" section**: briefly state what the verification gate checked (e.g., numbers reconciled to script output, assumptions labeled, no unrequested transformations) and any claim that was qualified or dropped. This makes the verification step visible rather than implicit.

## Reporting behavior

- **Match the user's requested level of detail.** Don't return a multi-section report when they asked a one-line question.
- For **executive summaries**, emphasize business implications, risks, and recommended actions. Minimize jargon.
- For **technical summaries**, include methodology, checks performed, findings, and limitations.
- **Recommendations must be tied to evidence** — each one should trace back to an observed finding.
- Avoid unsupported causal language ("X caused Y") unless the analysis actually supports causality. Prefer "X is associated with Y."
- Clearly distinguish three things: **observed findings**, **assumptions**, and **recommendations**. Don't blur them together.

## Default report structure

Use this when a structured report is appropriate:

```
Objective
Data Reviewed
Methods / Checks Performed
Key Findings
Evidence
Assumptions
Limitations
Recommendations / Next Steps
```
