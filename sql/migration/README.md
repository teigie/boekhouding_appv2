# Migration queries

Moves resolved rows from `temp_afschrift` into the permanent `afschrift`
ledger, for one account (`Rekening_ID`) at a time. Orchestrated by
`app/migration.py::migrate_account`, invoked from
`POST /review/{rekening_id}/migrate`.

- `count_unresolved.sql` — guard: counts rows for the account that aren't
  `processed = 1`. Migration refuses (raises `NotFullyResolvedError`,
  nothing is touched) unless this is zero.
- `insert_into_afschrift.sql` — inserts the account's full `temp_afschrift`
  backlog into `afschrift`, in strict original (`temp_afschrift.ID`) order.
- `delete_from_temp_afschrift.sql` — deletes that same backlog from
  `temp_afschrift`, once inserted.

The insert and delete run inside one transaction, immediately after the
guard passes — see `app/migration.py`.

This is deliberately all-or-nothing **per account**: `afschrift.Saldo_na_mutatie`
is a running balance, so a row can never be skipped and inserted later out of
order without corrupting every balance after it. Other accounts are
unaffected by one account still having unresolved rows — including rows
left over from an earlier upload, not just the most recent one.

See docs/ARCHITECTURE.md's Fase 4 for the full pipeline.
