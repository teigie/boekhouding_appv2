# Categorization queries

Resolves accepted `temp_afschrift2` rows (rows that already passed the
upload-gate checks in `sql/upload/`) into `temp_afschrift` rows with real
foreign keys and a `processed` status.

`Rekening_ID`/`Mutatiesoort_ID` resolution is independent of `processed` —
both are expected to always resolve (the account was already validated at
upload time; `mutatiesoort_mapping` is structural reference data — an
unmatched Mutatiesoort fails the `NOT NULL` constraint rather than being
treated as "unresolved"). See docs/ARCHITECTURE.md.

`processed` reflects only the rule-match outcome. A category is matched
by any number of independent **rules** (`afschrift_cat_regels`, one row
per rule, `cat_ID` cascades on delete) — a category matches a row if AT
LEAST ONE of its rules matches (OR across a category's rules).

A rule is a set of per-column conditions
(`afschrift_cat_regel_kolommen` — one row per column the rule cares
about, over `Naam`, `Tegenrekening`, `Code`, `Af_bij`, `Bedrag_eur`,
`Mutatiesoort`, `Mededeling`, `Saldo_na_mutatie`, `Tag`). A column simply
absent from a rule is never checked ("no value = no check"). ALL columns
a rule *does* have must match for the rule itself to match (AND across
columns). Each column-condition carries one or more keywords/values
(`afschrift_cat_regel_keywords`) plus its own `combine_mode`: `'OR'`
matches if ANY of that column's keywords match the row, `'AND'` requires
ALL of them to match simultaneously. All of the above is per-user, like
`afschrift_categorien` itself, and every layer (rule/column/keyword) is
scoped to the categorizing user's own `user_ID`.

Matching depends on the column's type:

- **Naam, Tegenrekening, Mededeling, Tag, Mutatiesoort** — substring
  (`LIKE '%...%'`), same idea as the old "simple"/"difficult" keywords.
- **Code, Af_bij** — exact text match. Af_bij is restricted to exactly
  `'Af'`/`'Bij'` at the app layer (`app/categorization_rules.py`).
- **Bedrag_eur, Saldo_na_mutatie** — exact match as a NUMBER
  (`CAST(... AS REAL)`), not text — `'25'` and `'25.00'` are the same
  value. User input is Dutch-formatted (`'.'` thousands, `','` decimals,
  e.g. `'1.234,56'`) and parsed into this canonical numeric form before
  storage.

There used to be three separate signals here — "simple" (Naam
substrings), "difficult" (Mededeling substrings, optionally paired with a
Naam substring), and "Interne overboeking" (Tegenrekening resolving to
another `Rekening` of the same user, auto-detected, no keyword involved).
All three are now expressible as rules under the one general mechanism
above: a Naam-only rule, a Mededeling+Naam rule (two columns, both
required — the AND-across-columns default), and a Tegenrekening rule
listing your own account IBAN(s) as keywords, respectively. There's no
dedicated internal-transfer detection anymore — it's just an ordinary
user-owned rule now, which also means it no longer updates itself
automatically when you link a new account; add its IBAN as another
Tegenrekening keyword if you want it covered too.

`processed`:

- `0` — no category matched (no rule fired) — needs a manual category.
- `1` — exactly one category matched — eligible for migration.
- `2` — more than one category matched — ambiguous, needs a manual pick.

Files:

- `match_custom_rules.sql` — the one matching signal, returning
  (`temp_afschrift2.ID`, `cat_ID`) pairs for every match. Standalone/
  reusable (e.g. a future "preview matches" view); `categorize_batch.sql`
  embeds the same query itself rather than including this file, since
  SQLite has no cross-file inclusion.
- `categorize_batch.sql` — the actual pipeline step: embeds
  `match_custom_rules.sql`'s logic, resolves `Mutatiesoort_ID`
  (`Rekening_ID` is passed in already resolved by the caller), computes
  `processed`, and inserts the result into `temp_afschrift` in one
  `INSERT ... SELECT`, preserving `temp_afschrift2`'s row order. Also
  reformats `Datum` from `temp_afschrift2`'s raw `YYYYMMDD` to
  `temp_afschrift`'s `YYYY-MM-DD` — see docs/ARCHITECTURE.md for why the
  DB stores ISO dates even though the UI displays European
  (`DD-MM-YYYY`) ones. Returns `processed` for every inserted row
  (`RETURNING`), so the caller can tally resolved/unresolved/ambiguous
  counts without a second query.
- `clear_temp_afschrift2.sql` — deletes the account's now-categorized
  backlog. Run immediately after `categorize_batch.sql`, in the same
  transaction.
- `recategorize_temp_afschrift.sql` — the "Categorisatie opnieuw
  proberen" button on `/upload` (`app/categorization.py::recategorize_pending`).
  Re-runs the same rule-matching logic, but against `temp_afschrift`
  (not `temp_afschrift2`) and across *all* of a user's rows/accounts at
  once, any `processed` value — so rows that didn't match anything at
  upload time get a fresh shot after the user adds/edits a rule, without
  re-uploading the file. `processed = 1` rows are handled asymmetrically:
  since there's no flag distinguishing an automatic match from a manual
  pick on `/review` (both are just `processed = 1`, see
  `sql/queries/temp_afschrift/set_category.sql`), an already-resolved row
  is only ever *promoted* to ambiguous (`processed = 2`) — when a newly
  added rule now also matches it, surfacing that conflict instead of
  silently keeping the old single answer — and is never demoted back to
  unresolved (the normal outcome for a manual pick, which no rule has to
  match) or have its category silently swapped for a different single
  match. Rows that were already 0 or 2 move freely to whatever the fresh
  match implies. Rows already migrated to `afschrift` aren't touched
  (they're not in this table). Returns only the rows whose outcome
  actually changed. One necessary adaptation: `temp_afschrift` only has
  `Mutatiesoort_ID`, not the original raw text, so a `Mutatiesoort` rule
  condition is checked against any raw label in `mutatiesoort_mapping`
  that resolves to the same ID instead.

Categorization must always drain an account's **entire** current
`temp_afschrift2` backlog in one atomic run, never a partial subset — the
upload-gate balance-chain check in `sql/upload/` relies on that invariant
to reconstruct a valid ordering across tables.

See docs/ARCHITECTURE.md for the full pipeline.
