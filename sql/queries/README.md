# App queries

SQL used directly by the running app (selects for viewing/sorting/reporting,
plus small reusable write templates), as opposed to the one-time
schema/seed files or the pipeline stages in `sql/enrichment/` and
`sql/migration/`.

- `reference_data/` — templates for adding/removing categories and
  category-keywords after installation (see each file for its expected
  named parameters). Removal is deliberately limited to keywords only —
  see `reference_data/remove_keyword.sql` for why categories aren't
  removable by default.
- `users/` — login/signup: list, create, find-by-id, touch last-logged-in.
- `rekeningen/` — accounts: list for a user, create/link, find-by-name
  (used by the upload pipeline to resolve + authorize an account).
- `categorieen/` — spending categories: currently just the dashboard's
  listing; will grow once categorization/reporting exist.
- Ledger view/sort/report queries (per category, per account, per period,
  etc.) will be added here once the `afschrift` viewing UI is built.

Every query the app runs should end up as a tracked `.sql` file here (or in
`enrichment/`/`migration/`) — `app/db.py` only knows how to load and execute
a `.sql` file, it never builds SQL strings inline.
