# Migration queries (not yet implemented)

This folder will hold the SQL that moves resolved rows from `temp_afschrift`
into the permanent `afschrift` ledger. Planned file:

- `migrate_account.sql` — for a single `Rekening_ID`: only runs if every
  pending `temp_afschrift` row for that account has `processed = 1` (checked
  first, in Python or a guard query — see docs/ARCHITECTURE.md). Inserts
  those rows into `afschrift` in strict original sequence, then deletes them
  from `temp_afschrift`.

This is deliberately all-or-nothing **per account**: `afschrift.Saldo_na_mutatie`
is a running balance, so a row can never be skipped and inserted later out of
order without corrupting every balance after it. Other accounts are
unaffected by one account still having unresolved rows.

See docs/ARCHITECTURE.md for the full pipeline.
