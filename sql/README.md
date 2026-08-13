# sql/

Every SQL statement the app runs — table creation, reference data,
enrichment, migration, and app queries — lives here as a tracked `.sql`
file. Python (`app/db.py`) only knows how to open a connection and execute
a `.sql` file's contents; it never assembles SQL strings inline. This keeps
the actual logic reviewable/diffable independent of the Python code, per
the project's design (see docs/ARCHITECTURE.md).

| Path | Purpose | Run when |
|---|---|---|
| `schema.sql` | `CREATE TABLE` statements for the whole database | once, on first run against a fresh database |
| `seed_data.sql` | Mandatory structural reference data (categories, mutation types) | once, right after `schema.sql` |
| `optional/example_keywords.sql` | One example set of category-keywords — personal, not required | manually, only if useful as a starting point |
| `upload/` | Gates a raw upload per account (balance-chain + dedup) before it's kept | every upload, inside the insert transaction |
| `enrichment/` | Resolves accepted raw uploads into FK-linked, categorized rows | not yet implemented — see its README |
| `migration/` | Moves fully-resolved rows into the permanent ledger | not yet implemented — see its README |
| `queries/` | App-facing selects, plus reference-data add/remove templates | ongoing, as features are built |

The database file itself (`data/boekhouding.db`) is generated from these
files and is gitignored — it's never committed, so a fresh clone on any
machine rebuilds the same structure from source.
