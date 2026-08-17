# Categorization queries

Resolves accepted `temp_afschrift2` rows (rows that already passed the
upload-gate checks in `sql/upload/`) into `temp_afschrift` rows with real
foreign keys and a `processed` status.

`Rekening_ID`/`Mutatiesoort_ID` resolution is independent of `processed` —
both are expected to always resolve (the account was already validated at
upload time; `mutatiesoort_mapping` is structural reference data — an
unmatched Mutatiesoort fails the `NOT NULL` constraint rather than being
treated as "unresolved"). See docs/ARCHITECTURE.md.

`processed` reflects only the category-match outcome, from three
independent signals:

Categories and both keyword tables are per-user (like `Rekening`) — every
one of the three signals below is scoped to the categorizing user's own
`user_ID`, so one user's transactions can never match against another
user's categories or keywords, even if the keyword text happens to be
identical.

- **Simple categorization** — `Naam` (counterparty/merchant name) checked
  against the user's own `afschrift_cat_keywords` rows (short substrings,
  e.g. "Lidl" -> Levensmiddelen). Managed via `/categories`.
- **Difficult categorization** — `Mededeling` (free-text transaction
  description) checked against the user's own
  `afschrift_cat_mededeling_keywords` rows (longer phrases/sentences, not
  just single words). Each row can OPTIONALLY pair its Mededeling keyword
  with a `naam_keyword` that must ALSO be found in `Naam` for the row to
  match — e.g. Mededeling "Vakantiegeld" paired with Naam "vakantie",
  precise together even though neither substring alone would be. Left
  `NULL`, a row matches on Mededeling alone, same as before. Managed via
  `/categories`.
- **Internal transfer** — structurally different from the other two, not
  a keyword match at all: `Tegenrekening` resolving to another `Rekening`
  linked to the *same* user is categorized as "Interne overboeking"
  (`match_internal_transfer.sql`). Relies on a category existing under
  that exact name *for that user* — there's no dedicated schema flag for
  "the internal-transfer category". New users start with zero categories
  (see `sql/seed_data.sql`), so this signal simply matches nothing until a
  user adds "Interne overboeking" themselves (offered as one of the
  quick-add suggestions on `/categories`).

Current combination strategy (**not final, expected to change**): all
three signals are always checked for every row, and the categories
matched from each are unioned into one set per row before deciding
`processed`:

- `0` — no category matched (none of the three) — needs a manual category.
- `1` — exactly one category matched — eligible for migration.
- `2` — more than one category matched — ambiguous, needs a manual pick.

Files:

- `match_naam_keywords.sql` / `match_mededeling_keywords.sql` /
  `match_internal_transfer.sql` — one set-based query per signal, per
  account, returning (temp_afschrift2.ID, cat_ID) pairs for every match.
  Standalone/reusable (e.g. a future "preview matches" view);
  `categorize_batch.sql` embeds the same joins itself rather than
  including these files, since SQLite has no cross-file inclusion — some
  duplication, same pattern already used between
  `sql/upload/check_balance_chain.sql` and `check_dedup.sql`.
- `categorize_batch.sql` — the actual pipeline step: combines all three
  match sets, resolves `Mutatiesoort_ID` (`Rekening_ID` is passed in
  already resolved by the caller), computes `processed`, and inserts the
  result into `temp_afschrift` in one `INSERT ... SELECT`, preserving
  `temp_afschrift2`'s row order. Also reformats `Datum` from
  `temp_afschrift2`'s raw `YYYYMMDD` to `temp_afschrift`'s `YYYY-MM-DD` —
  see docs/ARCHITECTURE.md for why the DB stores ISO dates even though the
  UI displays European (`DD-MM-YYYY`) ones. Returns `processed` for every
  inserted row (`RETURNING`), so the caller can tally
  resolved/unresolved/ambiguous counts without a second query.
- `clear_temp_afschrift2.sql` — deletes the account's now-categorized
  backlog. Run immediately after `categorize_batch.sql`, in the same
  transaction.

Categorization must always drain an account's **entire** current
`temp_afschrift2` backlog in one atomic run, never a partial subset — the
upload-gate balance-chain check in `sql/upload/` relies on that invariant
to reconstruct a valid ordering across tables.

See docs/ARCHITECTURE.md for the full pipeline.
