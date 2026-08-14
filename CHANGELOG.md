# Changelog

History log of what's changed in the project, for us as programmers.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

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
