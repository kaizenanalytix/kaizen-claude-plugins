# DDL Dialects — Type Mappings and Syntax Notes

Use this when generating physical-stage DDL. Default to Snowflake if the user hasn't specified a
platform. Generate one `.sql` file per platform requested.

## Type Mapping Table

| Logical Type | Snowflake | SQL Server | PostgreSQL | SAP HANA |
|---|---|---|---|---|
| Surrogate key (int) | `NUMBER(38,0)` | `BIGINT` | `BIGINT` | `BIGINT` |
| Natural/business key (text) | `VARCHAR(n)` | `VARCHAR(n)` | `VARCHAR(n)` | `NVARCHAR(n)` |
| Date | `DATE` | `DATE` | `DATE` | `DATE` |
| Timestamp (no tz) | `TIMESTAMP_NTZ` | `DATETIME2` | `TIMESTAMP` | `TIMESTAMP` |
| Timestamp (with tz) | `TIMESTAMP_TZ` | `DATETIMEOFFSET` | `TIMESTAMPTZ` | `SECONDDATE` |
| Currency/money | `NUMBER(18,2)` | `DECIMAL(18,2)` | `NUMERIC(18,2)` | `DECIMAL(18,2)` |
| Boolean flag | `BOOLEAN` | `BIT` | `BOOLEAN` | `BOOLEAN` |
| Free text (bounded) | `VARCHAR(n)` | `VARCHAR(n)` | `VARCHAR(n)` | `NVARCHAR(n)` |
| Long text | `VARCHAR(16777216)` | `NVARCHAR(MAX)` | `TEXT` | `NCLOB` |

## Auto-increment / Identity Syntax

| Platform | Syntax |
|---|---|
| Snowflake | `NUMBER(38,0) IDENTITY(1,1)` |
| SQL Server | `BIGINT IDENTITY(1,1)` |
| PostgreSQL | `BIGINT GENERATED ALWAYS AS IDENTITY` |
| SAP HANA | `BIGINT GENERATED ALWAYS AS IDENTITY` |

## Primary/Foreign Key Syntax

All four platforms support standard ANSI `PRIMARY KEY` and `FOREIGN KEY ... REFERENCES` syntax at
the column or table-constraint level — use table-level constraints for composite keys:

```sql
CONSTRAINT pk_<table> PRIMARY KEY (<col>[, <col>...])
CONSTRAINT fk_<table>_<ref_table> FOREIGN KEY (<col>) REFERENCES <ref_table> (<ref_col>)
```

## Indexing / Clustering Notes

- **Snowflake**: no traditional indexes — use `CLUSTER BY` on large fact tables for
  micro-partition pruning. Only specify this if the table is expected to be large; skip it for
  small dimension tables.
- **SQL Server**: `CREATE CLUSTERED INDEX` on the primary key by default (often automatic);
  add `CREATE NONCLUSTERED INDEX` on frequently filtered/joined foreign key columns.
- **PostgreSQL**: primary keys get an implicit unique index; add explicit `CREATE INDEX` on
  foreign key columns (Postgres does not auto-index FKs the way some platforms do).
- **SAP HANA**: primary keys are indexed automatically; consider column store vs. row store per
  table based on whether it's analytical (fact/dimension → column store) or transactional
  (→ row store, though HANA defaults to column store generally).

## Soft Delete / Metadata Columns

Apply the metadata columns from `conventions.md` using the type mapping above — e.g. `is_deleted`
uses the Boolean row, `created_at`/`updated_at` use the Timestamp row.

## File Naming

One file per platform: `DDL (Snowflake).sql`, `DDL (SQL Server).sql`, etc. Each
file is self-contained and runnable independently — don't split a single platform's DDL across
multiple files.
