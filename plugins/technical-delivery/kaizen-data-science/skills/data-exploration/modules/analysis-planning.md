# Analysis Planning

Use this module at the **start of every analysis task**, before performing any analysis. Its job is to make sure you understand what you are being asked to do and what the data represents, so the rest of the workflow stays focused and evidence-based.

## What to identify

Work out the following before proceeding. Some will come from the user, some you will infer from the data — label inferred items as assumptions.

- **Business objective** — What decision or question is the analysis supporting?
- **Dataset context** — What does the dataframe or file represent?
- **Unit of analysis** — What does each row represent (a customer, a transaction, a day, etc.)?
- **Key columns** — Which fields appear most relevant to the objective?
- **Expected output** — What should the deliverable look like (a quick answer, a technical summary, an executive summary, a cleaned file)?
- **Assumptions** — What is being inferred because the user did not specify it?
- **Constraints** — Are there time, tool, data, or scope limitations?
- **Relevant modules** — Which modules should be used for this request?

## Behavior

- Ask a concise clarification question **only if essential context is missing**. One good question beats several.
- If the task can proceed with reasonable assumptions, proceed and record those assumptions rather than blocking on the user.
- Do not run advanced modules by default.
- Choose the **smallest sufficient workflow** for the user's request. If they asked for a data quality check, do not silently expand into modeling or forecasting.

## Internal planning output

Capture your plan in this structure before you begin. It can be brief — it is a working contract, not a deliverable. (It is fine to keep this internal and summarize it for the user only when useful.)

```
Objective:
Dataset/context:
Unit of analysis:
Relevant columns:
Relevant modules:
Assumptions:
Planned analysis steps:
Expected output:
```
