# Data Model Best Practices Checklist (BP-1 .. BP-10)

Run through this checklist against the generated model before presenting it to the user (Step 3
of SKILL.md). This is a **self-check**, not a separate review pass — no multi-turn loop.
Fix anything that fails, then move on. Only stop to ask the user if the fix requires a judgment
call the sources don't resolve (e.g. an ambiguous fact grain).

| # | Best Practice | What to check |
|---|---|---|
| BP-1 | Naming consistency | Every table/column follows `snake_case`. Dimensional prefixes (`dim_`, `fact_`, `bridge_`) are applied correctly and consistently. |
| BP-2 | Key integrity | Every table has a primary key. Every foreign key resolves to an existing primary key somewhere in the model — no dangling/orphaned references. |
| BP-3 | Normalization correctness | OLTP tables pass 3NF — no repeating groups, no partial or transitive dependencies. Dimensional tables are denormalized **on purpose**, not by accident (i.e. the design rationale is documented, not just messy). |
| BP-4 | SCD type applied and flagged | Every dimension table has an explicit SCD type recorded in the data dictionary. Type 2 dimensions include `effective_date`, `expiration_date`, and `is_current` columns. |
| BP-5 | No unbounded free text | Every `VARCHAR`/text column has a documented, reasonable length — not left as a default/unbounded type. |
| BP-6 | No float for currency | Every currency/money column uses a fixed-precision decimal type. Flag and fix any float/double used for money. |
| BP-7 | Metadata columns present | Every table has the required audit/metadata columns for its kind (OLTP vs. dimensional) per `conventions.md`. |
| BP-8 | Fact table grain is explicit | Every fact table has a one-sentence grain statement in the data dictionary notes (e.g. "one row per order line item per day"). |
| BP-9 | No many-to-many without a bridge | Any M:M relationship is resolved through a `bridge_` table — never modeled as a direct M:M link. |
| BP-10 | Dictionary completeness | Every table and column that appears in the ERD/DDL has a matching row in the data dictionary. No gaps between what's modeled and what's documented. |

## Applying the checklist

Walk the list in order once the model is built. For each item:
1. Check it against the current model.
2. If it fails, fix it directly (rename a column, add a missing metadata column, flag an SCD
   type, etc.) — these are mechanical fixes, not judgment calls, so just make them.
3. If a fix genuinely requires information the sources don't provide (most commonly: fact grain,
   or which SCD type fits an ambiguous dimension), ask the user rather than guessing.

Report the outcome briefly in the Step 6 chat summary — either "best-practices check: passed" or
a short note on what was corrected automatically.
