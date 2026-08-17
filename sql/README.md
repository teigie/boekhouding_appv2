# sql/

Every SQL statement the app runs — table creation, reference data,
categorization, migration, and app queries — lives here as a tracked `.sql`
file. Python (`app/db.py`) only knows how to open a connection and execute
a `.sql` file's contents; it never assembles SQL strings inline. This keeps
the actual logic reviewable/diffable independent of the Python code, per
the project's design (see docs/ARCHITECTURE.md).

| Path | Purpose | Run when |
|---|---|---|
| `schema.sql` | `CREATE TABLE` statements for the whole database | once, on first run against a fresh database |
| `seed_data.sql` | Mandatory structural reference data (category suggestions, mutation types) | once, right after `schema.sql` |
| `upload/` | Post-insert continuity gates per account (balance-chain + dedup) | every upload, inside the insert transaction |
| `categorization/` | Resolves accepted raw uploads into FK-linked, categorized rows | automatically, right after a batch is accepted |
| `migration/` | Moves fully-resolved rows into the permanent ledger | not yet implemented — see its README |
| `queries/` | App-facing selects, plus reference-data add/remove templates | ongoing, as features are built |

The database file itself (`data/boekhouding.db`) is generated from these
files and is gitignored — it's never committed, so a fresh clone on any
machine rebuilds the same structure from source.
