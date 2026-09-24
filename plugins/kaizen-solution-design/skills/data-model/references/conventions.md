# Kaizen Data Modeling Conventions

Apply these while building the model — don't retrofit them at the end. All are checked in
Step 3 (`best-practices.md`) but should be second nature by the time you get there.

## Normalization

- **OLTP / transactional models**: 3NF by default — no repeating groups, no partial or
  transitive dependencies on a composite key.
- **Dimensional models**: intentionally denormalized. Star schema is the default; only use a
  snowflake schema when a dimension is heavily reused across facts or the client specifically
  asks for it. Denormalization here is a deliberate choice, not an oversight — say so in the
  data dictionary notes if it might look like an error to a reviewer.

## SCD (Slowly Changing Dimension) Types

- **Type 2 default** for dimensions that change meaningfully over time and where history
  matters: customer, product, employee, and similar "things that describe the business."
- **Type 1 default** for reference/lookup data that just gets overwritten with no need for
  history: status codes, currency codes, unit-of-measure tables.
- Every dimension's SCD type must be **explicitly flagged** in the data dictionary — never leave
  it implicit or assumed.

## Naming Conventions

- `snake_case` throughout — tables, columns, everything.
- Tables named as the **singular** business entity: `customer`, not `customers`.
- Dimensional model prefixes: `dim_`, `fact_`, `bridge_` (for resolving many-to-many
  relationships — see BP-9 in the best-practices checklist).
- Surrogate keys: `<table>_sk` (dimensional models). Natural/business keys: `<table>_id` or
  `<table>_key` (OLTP models, or the business key carried alongside a surrogate key in a
  dimension).
- Foreign keys: name to match the referenced primary key — `<referenced_table>_sk` or
  `<referenced_table>_id`, whichever the referenced table uses.

## Target Platforms

Primary: **Snowflake**, **SQL Server**, **PostgreSQL**. Secondary (generate only if asked):
**SAP HANA**. Default to Snowflake when the user hasn't specified a platform. See
`ddl-dialects.md` for the type mappings per platform.

## Standard Data Types

- **Dates/timestamps**: `DATE` for date-only; `TIMESTAMP_NTZ` (Snowflake) or platform
  equivalent for date+time. Always be explicit about time zone handling in the data dictionary
  notes — don't leave it ambiguous whether a timestamp is UTC, local, or naive.
- **Surrogate keys**: `NUMBER`/`BIGINT`. **Natural/business keys**: `VARCHAR` unless the source
  system's own type dictates otherwise (e.g. a source system uses a numeric customer ID).
- **Currency/money**: fixed-precision decimal — `NUMBER(18,2)` or the platform's decimal
  equivalent. Never use a float type for money; rounding errors compound and this is a common,
  avoidable modeling mistake.
- **Free text**: bounded `VARCHAR` lengths, chosen deliberately and documented in the data
  dictionary — never leave a text column unbounded by default.

## Required Metadata Columns

- **OLTP tables**: `created_at`, `updated_at`, `created_by`, `updated_by`, `is_deleted` (soft
  delete flag rather than hard-deleting rows).
- **Dimensional tables**: `effective_date`, `expiration_date`, `is_current` (needed for Type 2
  SCD tracking), `dw_load_date`, `dw_source_system` (lineage — which source system the row came
  from, useful when a dimension is fed by more than one upstream system).

## How the Stages Build on Each Other

Conceptual → Logical → Physical → Dimensional isn't strictly linear in practice — a user might
ask only for a conceptual model to align with business stakeholders, then come back weeks later
for logical/physical once requirements firm up. Treat each stage as extending the one before it
rather than starting over: a logical model should be traceable back to the conceptual entities it
came from, and physical DDL should be traceable back to the logical attributes.
