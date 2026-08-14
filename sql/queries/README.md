# App queries

SQL used directly by the running app (selects for viewing/sorting/reporting,
plus small reusable write templates), as opposed to the one-time
schema/seed files or the pipeline stages in `sql/categorization/` and
`sql/migration/`.

- `reference_data/` — templates for adding/removing categories and
  category-keywords after installation (see each file for its expected
  named parameters). Removal is deliberately limited to keywords only —
  see `reference_data/remove_keyword.sql` for why categories aren't
  removable by default.
- `users/` — login/signup: list, create, find-by-id, touch last-logged-in.
- `rekeningen/` — accounts: list for a user, create/link, find-by-name
  (used by the upload pipeline to resolve + authorize an account),
  find-by-id-for-user (used by `/review`'s per-table save to confirm the
  account in the URL is actually the logged-in user's).
- `mutatiesoorten/` — find-by-name (used by the upload pipeline's
  pre-insert Mutatiesoort gate, and by categorization to resolve
  `Mutatiesoort_ID`).
- `categorieen/` — spending categories: the dashboard's listing, plus
  find-by-name (used by `/review`'s "add new category" flow to reuse an
  existing name instead of creating a near-duplicate).
- `temp_afschrift/` — the `/review` page: every row (any `processed`
  value) across a user's accounts, with Rekening/category names resolved
  for display (`list_all_for_user.sql`), and the write behind its
  per-table save button (`set_category.sql`, run once per row submitted)
  — scoped to the logged-in user via a Rekening ownership check baked
  into the UPDATE itself.
- Ledger view/sort/report queries (per category, per account, per period,
  etc.) will be added here once the `afschrift` viewing UI is built.

Every query the app runs should end up as a tracked `.sql` file here (or in
`categorization/`/`migration/`) — `app/db.py` only knows how to load and execute
a `.sql` file, it never builds SQL strings inline.
