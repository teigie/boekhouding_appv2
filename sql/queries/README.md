# App queries

SQL used directly by the running app (selects for viewing/sorting/reporting,
plus small reusable write templates), as opposed to the one-time
schema/seed files or the pipeline stages in `sql/categorization/` and
`sql/migration/`.

- `reference_data/` — templates for adding/removing a user's own
  categories and their categorization rules/columns/keywords (see each
  file for its expected named parameters). Category removal cascades its
  rules (`ON DELETE CASCADE` on `cat_ID`, all the way down through
  `afschrift_cat_regel_kolommen`/`afschrift_cat_regel_keywords`) but is
  blocked by the caller (`app/routes/categories.py`) if the category is
  still referenced by `temp_afschrift`/`afschrift` rows — see
  `categorieen/count_usage_for_user.sql`. `remove_regel_kolommen_for_regel.sql`
  wipes one rule's entire current column-set — the first half of the
  rule-edit page's "replace" save (see `app/routes/categories.py::save_regel`
  and `regels/` below), always paired with re-inserting whatever was
  actually submitted, in the same transaction.
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
- `regels/` — a user's own categorization rules: `list_for_user.sql`
  nests every rule (rule → column → keywords) for the profile page's
  read-only summary; `find_for_user.sql` is the ownership check for the
  rule-edit page (`/categories/regels/{regel_id}/edit`) plus its owning
  category's name for display; `list_kolommen_for_regel.sql` pre-fills
  that page's per-column textareas/modes from the rule's current state.
  See `sql/categorization/match_custom_rules.sql` for how rules are
  actually evaluated against transactions — that's a separate, standalone
  query under `categorization/`, not here, since it runs at
  categorization time rather than as an app-facing read.

The Rekeningen and categorieën/keywords management screens (formerly
separate `/accounts` and `/categories` pages) are now one combined
profile page at `/user/{username}` (`app/routes/user.py`,
`app/user_page.py`) — the POST routes that add/remove things still live
in `app/routes/accounts.py`/`app/routes/categories.py` and reuse the
queries above; only the GET view moved.

Every query the app runs should end up as a tracked `.sql` file here (or in
`categorization/`/`migration/`) — `app/db.py` only knows how to load and execute
a `.sql` file, it never builds SQL strings inline.
