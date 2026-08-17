# Changelog

History log of what's changed in the project, for us as programmers.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### 2026-08-17 — General rule-based categorization

- Replaced the old three categorization mechanisms — "simple"
  (`afschrift_cat_keywords`, Naam substrings), "difficult"
  (`afschrift_cat_mededeling_keywords`, Mededeling substrings optionally
  paired with a Naam substring), and "Interne overboeking"
  (auto-detected Tegenrekening-resolves-to-own-account, no table) — with
  one general, user-owned rule system. A category matches if any one of
  its **rules** (`afschrift_cat_regels`) matches (OR across a category's
  rules). A rule is a set of conditions over any of `Naam`,
  `Tegenrekening`, `Code`, `Af_bij`, `Bedrag_eur`, `Mutatiesoort`,
  `Mededeling`, `Saldo_na_mutatie`, `Tag`
  (`afschrift_cat_regel_kolommen`) — a column absent from a rule is
  simply not checked, all columns present must match (AND across a
  rule's columns). Each column-condition carries one or more
  keywords/values (`afschrift_cat_regel_keywords`) plus its own
  AND/OR `combine_mode` for how those keywords combine with each other.
  Matching is substring (`LIKE`) for free-text columns, exact text match
  for `Code`/`Af_bij`, and exact NUMERIC match (`CAST(... AS REAL)`, not
  text) for `Bedrag_eur`/`Saldo_na_mutatie` — new `app/categorization_rules.py`
  validates/normalizes a submitted value for its column before storage,
  including parsing Dutch-formatted amounts (`'.'` thousands, `','`
  decimals, e.g. `'1.234,56'`) into that canonical numeric form, and
  restricting `Af_bij` to exactly `'Af'`/`'Bij'`.
- New `sql/categorization/match_custom_rules.sql` (standalone/documented)
  and a matching rewrite of `categorize_batch.sql`'s embedded logic:
  implemented as a correlated `GROUP BY`/`HAVING` per (rule, column) —
  a column-group "fails" if fewer than 1 (OR mode) or fewer than all
  (AND mode) of its keywords match, and a rule matches iff none of its
  column-groups fail.
- Profile page (`/user/{username}`): each category now shows its rules as
  cards, each column rendered as a labeled group of removable keyword
  chips (plus a small "+ keyword" form reusing that column's existing
  combine_mode) and a "Regel verwijderen" button. A collapsible "Nieuwe
  regel toevoegen" form lets a user set every column's keywords (one
  per line, or comma-separated — except `Bedrag_eur`/`Saldo_na_mutatie`,
  where a comma is the decimal separator, so there it's one amount per
  line) and AND/OR mode in a single submission, creating the rule and
  all its non-empty columns/keywords in one transaction. Deleting a
  rule's last keyword in a column removes that now-empty column, and
  removing a rule's last column removes the now-empty rule
  (`remove_empty_regel_kolommen.sql`/`remove_empty_regels.sql`), so
  "column absent = not checked" never has to distinguish an empty group
  from a genuinely absent one.
- New `scripts/migrate_to_rule_based_categorization.py`: converts every
  existing Naam keyword into a 1-column rule, every Mededeling keyword
  (with its optional paired Naam keyword) into a 1- or 2-column rule, and
  — for any user with a category literally named "Interne overboeking"
  and 2+ linked Rekeningen — a static Tegenrekening rule listing that
  user's own IBANs (OR). This is a **static, one-time snapshot**, not the
  old dynamic "resolves to any Rekening of mine" check: a Rekening linked
  *after* running this migration isn't automatically covered, unlike
  before — add its IBAN as another Tegenrekening keyword if wanted. Then
  drops `afschrift_cat_keywords`/`afschrift_cat_mededeling_keywords`.
  Already run against the real `data/boekhouding.db` (backed up first,
  `PRAGMA foreign_key_check` clean): 15 Naam keywords → 15 rules, 1
  Mededeling keyword → 1 rule, 1 static Tegenrekening rule created (the
  other user's "Interne overboeking" category only had 1 linked Rekening,
  so correctly skipped).
- Verified on an isolated scratch copy of the migrated real data: every
  auto-migrated rule reproduces its old categorization outcome exactly
  (Naam/Mededeling/internal-transfer regression); a new multi-column AND
  rule (the "Inkomsten" example: Naam + Af_bij + Mutatiesoort +
  Mededeling all required) resolves a fully-matching row and correctly
  leaves a partially-matching row (wrong Af_bij) unresolved; an exact
  `Bedrag_eur` rule of `50` matches `50.0` but correctly does NOT
  substring-match `150.0`; an AND-combined Mededeling column ("Salaris"
  AND "maandelijks") only matches when both phrases are present. At the
  HTTP layer: invalid Af_bij/unparseable-amount/empty-rule submissions
  all render friendly Dutch errors inline on the profile page; adding a
  keyword to an existing column, deleting a single keyword (with cascade
  cleanup), and deleting a whole rule all behave correctly.

### 2026-08-17 — Profile page + real dashboard (Fase 5)

- New per-user profile page at `/user/{username}` (`app/routes/user.py`,
  `app/user_page.py`, template `user.html`), replacing the separate
  `/accounts` and `/categories` pages: Rekeningen-beheer and
  categorieën/keywords-beheer now live together on one page. The write
  routes themselves didn't move (`POST /accounts` in
  `app/routes/accounts.py`, `POST /categories/...` in
  `app/routes/categories.py`) — they now redirect to (and, on error,
  re-render) the profile page instead of their old standalone GET pages,
  via the shared `app/user_page.py::load_user_page_data`/`user_page_url`.
  `{username}` in the URL is cosmetic, not an auth boundary (`Users.Name`
  has no uniqueness constraint) — the page always shows the logged-in
  session's own data and redirects to the canonical URL if the path
  doesn't match it. Names are percent-encoded when building the URL/nav
  link so spaces or special characters in a freely-typed username don't
  break it.
- Deleted `app/templates/accounts.html` and `app/templates/categories.html`
  (merged into `user.html`); `base.html`'s nav no longer lists
  "Rekeningen"/"Categorieën" separately — the user's own name in the top
  bar is now a link to their profile page.
- Turned the dashboard (`/`, `app/routes/dashboard.py`) into an actual
  financial report instead of a static placeholder: filterable by date
  range (`?start=...&end=...`, ISO dates), defaulting to the current
  calendar month when no (or an invalid) range is given. Shows headline
  totals — total income, total expenditure, and the difference — plus a
  per-category income/expenditure breakdown table, for the selected
  range. Reads only the permanent `afschrift` ledger, never
  `temp_afschrift` — rows not yet migrated (Fase 4) don't count. New
  `sql/queries/afschrift/totals_per_category_for_user.sql` does the
  per-category sums in one query, scoped to the user's own Rekeningen;
  the page's headline totals are just that query's rows summed in
  Python, not a second query. Added quick-range preset chips (deze
  maand, vorige maand, dit jaar, alles).
- Verified against an isolated copy of the dev database seeded with real
  migrated `afschrift` rows (from testing Fase 4): default "deze maand"
  totals and the per-category breakdown matched a hand-computed sum of
  the underlying rows exactly; an empty date range showed the
  "geen gegevens"-message instead of an empty table; a reversed
  start/end range was silently normalized rather than erroring; the
  profile page correctly redirected `/user/WrongName` to the logged-in
  user's own canonical URL; adding a duplicate account/category
  correctly re-rendered the profile page (not a standalone error page)
  with the existing Rekeningen/categorieën still visible alongside the
  error.

### 2026-08-17 — Fase 4: migrate resolved rows into `afschrift`

- Implemented the `temp_afschrift` → `afschrift` migration step (Fase 4,
  see `docs/ARCHITECTURE.md`), previously just a `sql/migration/README.md`
  plan. New `app/migration.py::migrate_account(rekening_id, user_id)`:
  all-or-nothing per account, refuses (raises `NotFullyResolvedError`,
  nothing touched) unless every `temp_afschrift` row for that account —
  including leftovers from earlier uploads — is `processed = 1`
  (`sql/migration/count_unresolved.sql`). On success, inserts the account's
  full backlog into `afschrift` in strict original order
  (`sql/migration/insert_into_afschrift.sql`) and deletes it from
  `temp_afschrift` (`sql/migration/delete_from_temp_afschrift.sql`), in one
  transaction — same insert-then-delete shape as Fase 2's
  `categorize_batch.sql` + `clear_temp_afschrift2.sql`. Both the guard and
  the insert/delete are scoped through `Rekening.user_ID`, same defense in
  depth as `set_category.sql`.
- New route `POST /review/{rekening_id}/migrate`
  (`app/routes/review.py::migrate_to_afschrift`): verifies the account
  belongs to the logged-in user, then calls `migrate_account` — which
  re-checks the "fully resolved" condition against the database itself
  rather than trusting the already-rendered page. On success, redirects to
  `/review`; on `NotFullyResolvedError`, re-renders `/review` with a Dutch
  error message and a 400 status.
- `/review`'s per-account table now shows a "Migreren naar afschrift"
  button (via `formaction`, alongside the existing "Tabel opslaan" button
  in the same `<form>`) once every row in that table is resolved, instead
  of the previous static "nog niet geïmplementeerd" note.
- Verified against the dev database's two real accounts: the fully
  resolved account migrated its rows into `afschrift` and disappeared from
  `/review` once empty; the account with 2 remaining unresolved rows was
  refused with the error message and left completely untouched; a crafted
  `rekening_id` for another user's account is rejected before any check
  runs.

### 2026-08-17 — Paired Naam keyword for difficult categorization

- Added an optional `naam_keyword` column to
  `afschrift_cat_mededeling_keywords`: a difficult (Mededeling) keyword
  can now be paired with a Naam substring that must ALSO match, e.g.
  Mededeling "Vakantiegeld" + Naam "vakantie" for the "Vakantie"
  category — precise together even though neither alone would be. Left
  blank, a keyword still matches on Mededeling only, unchanged from
  before.
- Updated `sql/categorization/match_mededeling_keywords.sql` and
  `categorize_batch.sql`'s embedded copy to apply the paired condition
  when set.
- `/categories` gained an optional "Gekoppeld Naam-keyword" field on the
  difficult-keyword add form, and shows the pairing next to each keyword.
- Added `scripts/migrate_add_naam_keyword_pairing.py` — a plain `ALTER
  TABLE ADD COLUMN` (nullable, no rebuild needed) for existing databases.

### 2026-08-17 — Per-user categories & keywords

- Made spending categories (`afschrift_categorien`) and both keyword
  tables (`afschrift_cat_keywords`, `afschrift_cat_mededeling_keywords`)
  per-user, the same isolation pattern already used for `Rekening`: each
  gained a `user_ID` column + FK, and their uniqueness constraints moved
  from global to `UNIQUE(user_ID, ...)`. `cat_ID` on both keyword tables
  now cascades on delete, which is what makes category deletion safe.
- Added `afschrift_categorie_suggesties`, a small global (non-user-scoped)
  reference table seeded with the previous 14 default category names —
  offered as one-click "quick add" suggestions on the new `/categories`
  page. New users start with zero categories; these are just a template,
  never auto-inserted and never used by categorization matching.
- Added `app/routes/categories.py` + `app/templates/categories.html`: the
  first UI for managing categories and keywords at all (add/delete a
  category with an in-use guard, add/delete simple and difficult
  keywords per category) — previously only inline category creation
  existed, on `/review`, and keywords had no UI whatsoever.
- Scoped every categorization-matching query
  (`sql/categorization/match_naam_keywords.sql`,
  `match_mededeling_keywords.sql`, `match_internal_transfer.sql`,
  `categorize_batch.sql`) to the categorizing user's own `user_ID`, so one
  user's transactions can never match against another user's categories
  or keywords. Also closed a related gap in
  `sql/queries/temp_afschrift/set_category.sql`, which validated the
  `temp_afschrift` row's ownership but not the category being assigned.
- Retired `sql/optional/example_keywords.sql` (hardcoded IDs from the old
  fixed global seed order, no longer meaningful) — its purpose is now
  fully covered by the `/categories` UI.
- Added `scripts/migrate_categories_per_user.py`, a one-off script to
  upgrade an existing `data/boekhouding.db` in place: rebuilds the three
  affected tables with the new schema, backfills all existing rows to the
  current single user, and seeds `afschrift_categorie_suggesties` — with
  a timestamped backup, a `--dry-run` mode, and an idempotency guard.

### 2026-08-13 — Project scaffold

- Set up the FastAPI + SQLite project structure: `app/` (backend),
  `sql/` (all SQL as tracked files), `data/` (gitignored DB),
  `logs/` (gitignored runtime logs), `docs/` (this design documentation).
- Added `sql/schema.sql` (all tables) and `sql/seed_data.sql` (mandatory
  reference data: categories, mutation types). Category keywords were
  split out into `sql/optional/example_keywords.sql` since they're
  personal to one user, not structural data every install needs.
- Added `sql/queries/reference_data/` templates (`add_category.sql`,
  `add_keyword.sql`, `remove_keyword.sql`) for managing categories/
  keywords after installation, separate from the one-time seed file.
  Category removal deliberately not provided (FK dependency on existing
  ledger rows — see the comment in `remove_keyword.sql`).
- Added `app/db.py`: connection handling + one-time DB init from
  `schema.sql`/`seed_data.sql`, idempotent (`INSERT OR IGNORE`) and
  no-ops if the database already exists.
- Added `app/logging_config.py`: two rotating logs — `app.log`
  (technical/runtime, also echoed to console) and `audit.log`
  (data-changing events — currently just wired up, not yet emitting
  business events since upload/enrichment/migration don't exist yet).
- Added a minimal FastAPI app (`app/main.py`) with request logging
  middleware and one placeholder dashboard page (`/`) proving the
  database/templates/static files all wire up correctly.
- Documented the full upload → enrichment → review → migration pipeline,
  the `processed` status semantics (0/1/2), the per-account dedup/
  continuity/all-or-nothing-migration rules, and the portability
  approach in `docs/ARCHITECTURE.md`.
- Established that all paths are relative (`app/config.py`) and the
  database/logs are never committed, so the project can be cloned onto a
  different machine or handed to someone else without changes.

**Not yet implemented:** file upload endpoint, enrichment queries,
migration queries, review UI, ledger viewing/reporting.

### 2026-08-13 — Login/signup, accounts, and the upload pipeline

- Added a no-password login/session system (`app/session.py`,
  `app/routes/auth.py`, `login.html`): logging in means picking an
  existing `Users` row, or creating one — signup requires a `Name` and a
  `Rekening` (IBAN) together in one step, inserted atomically, since a
  user isn't useful without at least one linked account. The session
  cookie is signed (`itsdangerous`, via Starlette's `SessionMiddleware`)
  using a secret generated on first run and persisted at
  `data/.session_secret` (gitignored) — not securing a real secret, just
  making the cookie tamper-evident.
- Added `/accounts` (`app/routes/accounts.py`, `accounts.html`): view the
  current user's linked accounts, link an additional one. `Rekening.name`
  is `UNIQUE` system-wide, so linking an already-registered IBAN fails
  with a clear error rather than silently reassigning it.
- Added `app/importers/`: a `BaseImporter` interface plus `IngNlImporter`,
  the first concrete parser (semicolon-delimited, quoted, comma-decimal,
  raw `YYYYMMDD` dates — verified against a real sample export row).
  Adding a second bank later means adding one more importer class and
  registering it in `registry.py` — nothing else changes.
- Decided (and documented in `docs/ARCHITECTURE.md`) that `Datum` is
  stored as ISO `YYYY-MM-DD` in `temp_afschrift`/`afschrift` (sortable,
  works with SQLite's date functions) and only formatted as European
  `DD-MM-YYYY` at display time — `temp_afschrift2` keeps the bank's raw
  `YYYYMMDD` as-is.
- Added `sql/upload/`: `check_balance_chain.sql` (one query verifying an
  account's confirmed + pending + newly-uploaded rows have no broken
  balance link anywhere, using a documented ordering invariant across the
  three tables' independent autoincrement IDs) and `check_dedup.sql`
  (explicit duplicate-row detection, with inline date normalization since
  `temp_afschrift2` and `temp_afschrift`/`afschrift` use different date
  formats). Both verified against real accept/reject/duplicate scenarios
  before moving on.
- Added `app/upload.py`: the upload pipeline. The account in the file
  must already be registered *and* linked to the uploading user — an
  unknown or not-yours account is rejected outright (a deliberate
  narrowing of the earlier "hold it for later linking" idea, once the
  login system made "whose upload is this" answerable). Insertion is
  all-or-nothing per account, in one DB transaction: insert the batch,
  run both checks, commit only if both pass.
- Added `/upload` (`app/routes/upload.py`, `upload.html`): format picker
  (currently just ING NL) + file input, shows a per-account accept/reject
  result with the specific reason on rejection.
- Moved every remaining inline SQL string out of Python and into tracked
  `.sql` files (`sql/queries/users/`, `sql/queries/rekeningen/`,
  `sql/queries/categorieen/`, `sql/upload/insert_batch.sql`) — the
  SQL-first rule now holds with no exceptions anywhere in the app.
- Verified end-to-end with a real ING-shaped CSV: accepted a valid
  2-row upload, rejected a chain-breaking row with the correct row/date
  identified, rejected an exact re-upload as a duplicate, rejected an
  unregistered account and a different user's account, then accepted a
  valid continuation row — and confirmed via direct DB inspection that
  only the 3 accepted rows exist in `temp_afschrift2`, with no leftovers
  from any rejected attempt.

**Not yet implemented:** enrichment queries, migration queries, review
UI, ledger viewing/reporting.

### 2026-08-13 — Last-login display, Dutch translation

- `Users.last_logged_in` now means "when you logged in *before* this
  session" rather than "now": the old value is captured into the session
  at login time (`app/session.py`'s `log_in()` gained a `previous_login`
  param), then the DB field is updated to the current time. Signup also
  touches it, so a user's *next* login has something to show.
- Added `app/formatting.py` (`format_date_eu`/`format_datetime_eu`),
  registered as Jinja filters (`eu_date`/`eu_datetime`) in
  `app/templating.py` — storage stays ISO, display converts to European
  `DD-MM-YYYY[ HH:MM]`, consistent with the `Datum` decision already
  documented for the ledger.
- `/accounts` now shows "Laatste keer ingelogd" (last login) and
  formats account-added dates the same way.
- Translated the whole user-facing surface to Dutch: all templates
  (`base.html`, `login.html`, `accounts.html`, `upload.html`,
  `index.html` — including `lang="nl"`), and every user-facing string
  generated in Python (`app/routes/auth.py`, `app/routes/accounts.py`,
  `app/upload.py`'s rejection reasons, `app/importers/ing_nl.py`'s parse
  errors). `docs/ARCHITECTURE.md` and `README.md` were translated too;
  `CHANGELOG.md` and all code/SQL comments stay in English, per explicit
  scope decision. Also fixed a leftover line on the dashboard that
  described the old (now superseded) "unknown accounts get created
  automatically" behavior.
- Verified every template still renders correctly (no Jinja errors,
  correct Dutch text, correct date formatting) against mock data,
  without touching the live database.

### 2026-08-13 — Confirmed per-account isolation of the upload checks

- A concern came up: does the balance-chain/dedup check for one account
  get confused by another account's rows sitting physically between its
  own in `temp_afschrift2` (whose `ID` is a single shared counter across
  *all* accounts)? Checked the actual SQL and confirmed every branch of
  both `check_balance_chain.sql` and `check_dedup.sql` filters by
  `Rekening_ID`/`Rekening` *before* any ordering happens — another
  account's rows never enter the sequence being validated at all.
- Proved it empirically on an isolated scratch DB: uploaded account A's
  first batch, then account B's, then A's valid continuation, then B's,
  then a deliberately broken continuation for A — each account's chain
  validated completely independently of the other's interleaved
  activity, with the broken case correctly rejected against A's own
  expected balance. No code change needed; this was already correct.
- Tightened the "cross-table ordering" explanation in
  `docs/ARCHITECTURE.md` (Stage 1) to say explicitly that this is always
  per-account and why — the previous "reconstructs a valid global order"
  phrasing was ambiguous enough to read as cross-account ordering, which
  is exactly what prompted the concern.

### 2026-08-14 — Categorization (`temp_afschrift2` → `temp_afschrift`)

- Renamed this pipeline stage from "enrichment"/"verrijking" to
  "categorization"/"categorisering" everywhere it's a living reference
  (`README.md`, `docs/ARCHITECTURE.md`, `sql/README.md` and friends,
  code comments) — `sql/enrichment/` moved to `sql/categorization/` via
  `git mv`. Historical `CHANGELOG.md` entries above were left as-is.
- Loaded `sql/optional/example_keywords.sql`'s 16 example keywords into
  the dev database, to have real data to categorize against.
- Corrected `processed`'s documented meaning: it reflects only the
  category-match outcome, not FK resolution. `Rekening_ID`/`Mutatiesoort_ID`
  resolve independently and are always expected to succeed — an unmapped
  `Mutatiesoort` now rejects the whole upload batch (see below) rather
  than landing as `processed = 0`. `temp_afschrift.Mutatiesoort_ID` stayed
  `NOT NULL` on purpose to match.
- Added `afschrift_cat_mededeling_keywords` (schema.sql): category
  keywords/phrases matched against `Mededeling` (up to 200 chars, since
  these can be full phrases, not just merchant names), separate from the
  existing `afschrift_cat_keywords` (`Naam`-only, up to 30 chars).
  "Simple" categorization checks `Naam`; "difficult" categorization checks
  `Mededeling` — both always run for every row, and their matched
  categories are unioned into one set per row before deciding `processed`
  (0 = no match, 1 = exactly one, 2 = ambiguous). This combination
  strategy is explicitly provisional — flagged as likely to change in
  `sql/categorization/README.md`.
- Added `sql/categorization/`: `match_naam_keywords.sql` and
  `match_mededeling_keywords.sql` (standalone per-field match queries),
  `categorize_batch.sql` (the real pipeline step — one account's entire
  `temp_afschrift2` backlog resolved and inserted into `temp_afschrift` in
  a single `INSERT ... SELECT`, preserving row order, `RETURNING
  processed` so the caller can tally outcomes without a second query),
  and `clear_temp_afschrift2.sql` (drains the now-categorized backlog).
- Added `app/categorization.py`: `categorize_pending(rekening_text)` runs
  one account's full backlog atomically and returns
  resolved/unresolved/ambiguous counts, or `None` if nothing was pending.
- Added a second kind of upload gate to `app/upload.py`, pre-insert this
  time (unlike the existing post-insert balance-chain/dedup checks):
  every row's `Mutatiesoort` must already resolve via the new
  `sql/queries/mutatiesoorten/find_by_name.sql`, mirroring how `Rekening`
  was already checked before any insert. An unmapped `Mutatiesoort`
  rejects the entire batch, nothing is inserted — consistent with
  `mutatiesoort_mapping` being complete structural reference data, not
  something a row's manual review should have to fix.
- Wired categorization into the upload pipeline: right after an account's
  batch commits to `temp_afschrift2`, `app/upload.py` immediately calls
  `categorize_pending()` for that account, so a successful upload response
  already reflects the categorized (resolved/unresolved/ambiguous) counts.
  No separate trigger or UI step. Categorization runs on its own
  connection as its own atomic step — a failure there doesn't undo the
  already-committed upload, the rows just stay in `temp_afschrift2` for
  the next attempt (expected not to happen in practice, since `Rekening`/
  `Mutatiesoort` are already guaranteed resolvable by the pre-insert
  gates).
- `upload.html` now shows the categorization counts alongside each
  accepted account's result.
- Verified end-to-end on a scratch copy of the dev database (never the
  real one): a Naam-only match, a no-match row, a row matching *only* via
  Mededeling (proving the "difficult" path works standalone, not just as
  a tiebreaker), a row matching via both fields on different categories
  (→ `processed = 2`), a full `process_upload()` run through the real ING
  NL importer that rejects an entire batch over one unmapped
  `Mutatiesoort`, and the same batch (minus that row) accepted and
  categorized in one request.

**Not yet implemented:** the manual review UI for `processed = 0`/`2`
rows sitting in `temp_afschrift`, migration queries, ledger viewing/
reporting.

### 2026-08-14 — Read-only `/review` overview

- Added `/review` (`app/routes/review.py`, `review.html`): lists every
  `temp_afschrift` row still pending (`processed` 0 or 2) across the
  logged-in user's own accounts, grouped per account with
  unresolved/ambiguous counts. Deliberately read-only for now — no way to
  actually resolve a row from this screen yet, that's a separate, later
  feature (assigning a category, correcting an account, picking between
  ambiguous matches).
- Added `sql/queries/temp_afschrift/list_pending_for_user.sql` — joins
  `Rekening` (to scope to the user) and `mutatiesoort` (the canonical
  vocabulary table, not `mutatiesoort_mapping`, for a clean display name).
- Added a `/review` nav link, and minimal `table`/`.table-scroll` CSS
  (none existed yet) plus a `.result-ambiguous` status color alongside the
  existing ok/fail ones.
- Verified the query and template render correctly against a scratch
  database seeded through the real upload+categorization pipeline (one
  account with an unresolved row, another with an ambiguous one) — the
  resolved row was correctly excluded from the listing.

### 2026-08-14 — Third categorization signal: internal transfers

- Added a third, structurally different categorization signal alongside
  Naam/Mededeling keywords: a row whose `Tegenrekening` resolves to
  another `Rekening` linked to the *same* user is categorized as "Interne
  overboeking" — not a keyword match at all, a `Rekening`-to-`Rekening`
  lookup. Added `sql/categorization/match_internal_transfer.sql`
  (standalone) and folded the same join into `categorize_batch.sql`'s
  `combined_matches`, so it participates in the existing
  0/1/2 (`processed`) combination logic exactly like the other two
  signals — including going ambiguous if a transfer *also* happens to hit
  a Naam/Mededeling keyword for a different category.
  `app/categorization.py` now passes the account's `user_id` through as a
  query param (already had it from the existing Rekening lookup, just
  wasn't threaded through before).
- Verified end-to-end on a scratch copy: a transfer between two of the
  same user's own accounts → resolved to "Interne overboeking"
  (`processed = 1`); a transfer to an unregistered/external account → no
  match, stays unresolved; a transfer to a linked account whose Naam also
  happens to hit an unrelated keyword → correctly ambiguous
  (`processed = 2`).

### 2026-08-14 — Hand-driven test data for the upload pipeline

- Added `testdata/` (tracked, not gitignored — reference fixtures like
  `sql/optional/example_keywords.sql`): `testdata/README.md` walks through
  the whole pipeline by hand via the real running app (setup steps, an
  upload order, and an exact expected result per file), and
  `testdata/upload/*.csv` are the five ING-NL-format fixtures it
  references — one clean batch exercising all three categorization
  signals plus both unresolved and ambiguous outcomes, and one per
  rejection reason (unregistered account, unmapped mutatiesoort, wrong
  user, broken balance chain).
- Every expected result in `testdata/README.md` was cross-checked by
  actually running `process_upload()` against a scratch copy of the dev
  database with the documented setup steps applied — not guessed.
- Added `"vakantiegeld" -> Vakantie` to the real dev database's
  `afschrift_cat_mededeling_keywords` (that table started out empty), so
  batch 1 can demonstrate the Mededeling-only categorization path for
  real, not just on a scratch copy.

### 2026-08-14 — Two more isolated test batches; `/review` shows everything

- Added `testdata/upload/06_batch_ambiguous.csv` (single row, Naam and
  Mededeling each hit a different category → `processed = 2`, no
  dependency on the second linked account) and
  `07_batch_interne_overboeking.csv` (single row, Tegenrekening-only match
  → `processed = 1`, Interne overboeking, no Naam/Mededeling keyword
  involved) — isolated, one-signal-at-a-time versions of what batch 1
  already covered combined. Both verified against a scratch copy
  continuing the real dev database's actual balance chain.
  `testdata/README.md` also now explains what happens to batch 1's rows
  2/6 if the second account isn't linked yet at upload time (they don't
  error, they just lose the internal-transfer signal and categorize
  differently) — this is what actually happened when this was tested by
  hand, which is what prompted adding 06/07 as an account-independent way
  to see both cases regardless.
- Reworked `/review` from "pending rows only, grouped per account" to a
  single flat table of **every** `temp_afschrift` row (any `processed`
  value) across the user's accounts, with `Rekening` and `Categorie` shown
  by name (not ID) as explicit columns, plus an overall
  opgelost/onopgelost/ambigu count line. Renamed the backing query
  `sql/queries/temp_afschrift/list_pending_for_user.sql` ->
  `list_all_for_user.sql` (dropped the `processed` filter, added a
  `LEFT JOIN afschrift_categorien` for the category name) since it's no
  longer just the pending subset.

### 2026-08-14 — `/review`: per-account tables, editable category

- `/review` now groups rows into one table per Rekening (ordered by
  account name, matching the backing query's existing sort) instead of a
  single flat table across every account — each group has its own
  opgelost/onopgelost/ambigu subtotal, plus the overall total still shown
  above all of them. The `Rekening` column itself is gone since the group
  heading now carries that.
- Categorie went from a display-only column to a per-row form: a dropdown
  of every existing category, plus a "+ nieuwe categorie…" option that
  reveals a text input. Submitting either path
  (`POST /review/{id}/category`, new `sql/queries/temp_afschrift/
  set_category.sql`) sets `Afschrift_cat_ID` and always marks the row
  `processed = 1` — picking a category is itself the resolution, whether
  the row was unresolved, ambiguous, or already resolved differently
  before. A typed name that already exists (case-insensitively) is reused
  rather than creating a near-duplicate category (new
  `sql/queries/categorieen/find_by_name.sql`); a genuinely new name goes
  through the existing `reference_data/add_category.sql` template. The
  update is scoped to the logged-in user by a Rekening-ownership check
  baked into the `UPDATE`'s `WHERE` clause, not a separate lookup —
  verified that a crafted row ID belonging to another user's account is
  silently rejected (`rowcount == 0`, no change, warning logged).
- Table CSS reworked for readability: full cell borders instead of just a
  bottom rule, alternating row shading, a hover highlight, and amounts
  right-aligned with tabular figures and colored by Af/Bij so a
  statement's amount reads as one glanceable unit on one line instead of
  free-floating text.
- Verified end-to-end against a scratch copy of the dev database: both
  category-setting paths, the dedup-on-reuse behavior, and the ownership
  check, all called directly through `app/routes/review.py` (no browser
  needed — `httpx`/`TestClient` aren't installed in this environment).

### 2026-08-14 — `/review`: save per table, "ready for migration" check, wider page

- Replaced the per-row save button with one save button per Rekening
  table: `POST /review/{id}/category` is gone, replaced by
  `POST /review/{rekening_id}/save`, which reads every `cat_id_<row>` /
  `new_category_name_<row>` field submitted by that table's single
  `<form>` (wrapping the whole table, not just one row) and resolves each
  the same way as before (reuse-by-name, create-if-new, always
  `processed = 1`). The account in the URL is checked against the logged
  -in user (new `sql/queries/rekeningen/find_by_id_for_user.sql`) before
  anything is touched; each row update is still additionally scoped by
  `set_category.sql`'s own ownership check.
- After saving, the same "is every row for this account now
  `processed = 1`?" check the future migration step will need runs
  immediately, and the page says so under that table — "klaar voor
  migratie naar afschrift (nog niet geïmplementeerd)" if true, "nog niet
  alle rijen zijn opgelost" otherwise. **Nothing is migrated into
  `afschrift` yet** — that's still Fase 4, deliberately not built here,
  this only surfaces whether an account *would* qualify.
- `list_all_for_user.sql` now also selects `Rekening.ID` (not just the
  name) so the per-table form's action URL and the post-save readiness
  check have something to key off of.
- Added a `content_class` block to `base.html` so an individual page can
  widen its own `<main>` without affecting the others; `/review` uses it
  (`content--wide`, 1440px vs. the default 960px) — combined with the
  category cell shrinking back down to just a dropdown (no more per-row
  button crowding it), this is enough that the table no longer needs its
  horizontal scrollbar on a normal screen.
- Verified against a scratch copy of the actual dev database (which by
  now has two real accounts with a mix of resolved/unresolved/ambiguous
  rows from hand-testing): both grouped tables render with working
  per-table forms, a bulk save resolves multiple rows (including a
  brand-new category) in one submit, the affected table's readiness note
  flips to "klaar voor migratie" while the other account's doesn't, and a
  crafted `rekening_id` that isn't the current user's is rejected before
  any row is touched.
