# App queries

SQL used directly by the running app (selects for viewing/sorting/reporting,
plus small reusable write templates), as opposed to the one-time
schema/seed files or the pipeline stages in `sql/categorization/` and
`sql/migration/`.

- `reference_data/` — templates for adding/removing a user's own
  categories and category-keywords (see each file for its expected named
  parameters). Category removal cascades its keywords (`ON DELETE CASCADE`
  on `cat_ID`) but is blocked by the caller (`app/routes/categories.py`)
  if the category is still referenced by `temp_afschrift`/`afschrift`
  rows — see `categorieen/count_usage_for_user.sql`.
- `users/` — login/signup: list, create, find-by-id, touch last-logged-in.
- `rekeningen/` — accounts: list for a user, create/link, find-by-name
  (used by the upload pipeline to resolve + authorize an account),
  find-by-id-for-user (used by `/review`'s per-table save to confirm the
  account in the URL is actually the logged-in user's).
- `mutatiesoorten/` — find-by-name (used by the upload pipeline's
  pre-insert Mutatiesoort gate, and by categorization to resolve
  `Mutatiesoort_ID`).
- `categorieen/` — a user's own spending categories: list-for-user (the
  dashboard's category filter, `/review`'s dropdown, the profile page),
  find-by-name (used by `/review`'s "add new category" flow and the
  profile page to reuse an existing name instead of creating a
  near-duplicate), find-by-id-for-user (ownership check before mutating),
  list-suggestions (the global, non-user-scoped template list of category
  names offered as quick-add chips on the profile page),
  count-usage-for-user (the delete guard).
- `temp_afschrift/` — the `/review` page: every row (any `processed`
  value) across a user's accounts, with Rekening/category names resolved
  for display (`list_all_for_user.sql`), and the write behind its
  per-table save button (`set_category.sql`, run once per row submitted)
  — scoped to the logged-in user via a Rekening ownership check baked
  into the UPDATE itself.
- `afschrift/` — reporting over the permanent ledger: the dashboard's
  date-range totals per category (`totals_per_category_for_user.sql`),
  scoped to the logged-in user's own Rekeningen. Only reads `afschrift`,
  never `temp_afschrift` — rows not yet migrated (Fase 4) don't count
  towards real totals.

The Rekeningen and categorieën/keywords management screens (formerly
separate `/accounts` and `/categories` pages) are now one combined
profile page at `/user/{username}` (`app/routes/user.py`,
`app/user_page.py`) — the POST routes that add/remove things still live
in `app/routes/accounts.py`/`app/routes/categories.py` and reuse the
queries above; only the GET view moved.

Every query the app runs should end up as a tracked `.sql` file here (or in
`categorization/`/`migration/`) — `app/db.py` only knows how to load and execute
a `.sql` file, it never builds SQL strings inline.
