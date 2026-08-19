# Changelog

History log of what's changed in the project, for us as programmers.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

Versienummering is puur intern (deze app heeft geen "releases" in de
klassieke zin) — elke regel hieronder is één werksessie/wijziging,
opgeteld sinds het begin van het project. Gebruikt door de app zelf om te
bepalen of er een update beschikbaar is (zie `app/version.py`) en om te
tonen wat je gemist hebt sinds je laatste versie. Entries tot en met
0.0.29 zijn in het Engels geschreven, van vóór deze afspraak — alles
daarna is in het Nederlands.


## [0.0.32] - 2026-08-19 — Updatemechanisme: versiebeheer + update-banner

- **Nieuw**: Test is goed gegaan met versiecontrole. Nu test met failure.

## [0.0.31] - 2026-08-19 — Updatemechanisme: versiebeheer + update-banner

- **Nieuw**: Test met update versiecontrol.

## [0.0.30] - 2026-08-19 — Updatemechanisme: versiebeheer + update-banner

- **Nieuw**: elke pagina toont bovenaan een banner zodra er een nieuwere
  versie op de git-remote staat, met een "Nu bijwerken"-knop en een
  uitklapbare lijst van *alle* changelog-secties die je gemist hebt (niet
  alleen de nieuwste) — precies zodat iemand die de app gedownload heeft
  ook daadwerkelijk kan merken dát er updates zijn, wat tot nu toe niet
  kon. "Niet nu" onthoudt de weggeklikte versie (`localStorage`), en komt
  vanzelf terug zodra er een écht nieuwere versie verschijnt.
- Deze changelog is de enige bron van waarheid voor het versienummer —
  geen apart `VERSION`-bestand. Elke regel hierboven heeft nu een
  `## [x.y.z] - datum — titel`-kop; alle 29 bestaande entries (tot en met
  deze) zijn met terugwerkende kracht op chronologische volgorde
  hernummerd vanaf `0.0.1` (oudste, 2026-08-13) tot `0.0.29`. De volgorde
  in het bestand is daarbij consistent nieuwste-boven-oudste gemaakt —
  de oudste ~11 entries stonden voorheen in omgekeerde volgorde
  (oudste-eerst) onderaan het bestand.
- **Nieuw** `app/version.py`: `parse_changelog()` leest de
  `## [x.y.z] - ...`-koppen; `current_version()` is simpelweg de bovenste
  (nieuwste) in de lokale `CHANGELOG.md`. `check_for_update()` doet een
  best-effort `git fetch` en leest daarna `origin/main`'s `CHANGELOG.md`
  rechtstreeks uit de opgehaalde geschiedenis (`git show
  origin/main:CHANGELOG.md`, dus zonder de working tree aan te raken) —
  is de bovenste versie daar hoger, dan komt het resultaat (huidige
  versie, nieuwste versie, gemiste secties) in een module-cache die de
  banner via een nieuwe Jinja-global (`update_info()`,
  `app/templating.py`) op elke pagina kan uitlezen zonder dat een route
  het apart hoeft door te geven. Draait als achtergrondtaak bij het
  opstarten (`app/main.py`'s `lifespan`, via `asyncio.to_thread`) zodat
  een trage of offline controle de server nooit ophoudt met starten; elke
  storing (geen internet, geen git, geen echte checkout) wordt
  stilzwijgend als "niets gevonden" behandeld, nooit als fout.
- **Nieuw** `POST /update/apply` (`app/routes/update.py` →
  `app/version.py::apply_update`) achter de "Nu bijwerken"-knop — nooit
  automatisch. `git pull --ff-only` (weigert bij divergentie in plaats
  van te mergen), gevolgd door `pip install -r requirements.txt` als dat
  bestand meeveranderde. Herstarten verschilt per manier van draaien: in
  launcher-modus (`BOEKHOUDING_RELOAD=0`) spawnt `apply_update` eerst
  zelf een vervangend `python run.py`-proces (losgekoppeld, cross-
  platform) vóórdat de huidige server wordt gevraagd te stoppen —
  anders blijft de launcher (die de server maar één keer start en daarna
  niets bewaakt) de gebruiker zonder draaiende server achterlaten. In
  dev-modus (`python run.py`, `reload=True`) is dat niet nodig: de zojuist
  door `git pull` overschreven `.py`-bestanden zijn voor uvicorn's eigen
  file-watcher al genoeg reden om zichzelf te herstarten. Bij een
  mislukte pull verandert er niets (`update_failed.html` toont de
  foutmelding); bij succes toont `update_pending.html` een tussenpagina
  die zichzelf elke 1-1,5s opnieuw probeert te laden tot de server weer
  antwoordt.
- **Afspraak vanaf nu**: nieuwe changelog-entries worden in het
  Nederlands geschreven (bestaande Engelse entries blijven ongewijzigd).
- **Geverifieerd** end-to-end met twee lokale git-repo's (een bare
  "origin" + een clone die als draaiende app fungeerde, geen echt netwerk
  nodig): een schone checkout toont geen banner; een nieuwe versie op
  "origin" wordt bij de eerstvolgende opstart gedetecteerd met exact de
  juiste gemiste sectie(s); "Nu bijwerken" pullt succesvol, het oude
  serverproces sluit pas af nadat de tussenpagina is verstuurd, een nieuw
  proces staat vrijwel gelijktijdig weer op dezelfde poort te luisteren,
  en de banner is daarna verdwenen; een expres botsende lokale wijziging
  laat de pull correct weigeren zonder dat code, database of de draaiende
  server worden aangeraakt.

## [0.0.29] - 2026-08-19 — CSV export: Dutch number format

- `Bedrag_eur`/`Saldo_na_mutatie` in the dashboard's CSV export now use
  Dutch notation (`,` decimal, `.` thousands, e.g. `1.234,50`) instead of
  a plain dot-decimal float — new `app/formatting.py::format_amount_nl`,
  the reverse of `app/categorization_rules.py::_parse_dutch_amount`.
  Paired with switching the CSV's field delimiter from `,` to `;`: a
  Dutch-locale spreadsheet reads `,` as the decimal separator, so it
  needs `;` between fields to parse correctly — the standard Dutch/
  Excel-NL CSV convention.

## [0.0.28] - 2026-08-19 — Dashboard: CSV export + select-all/deselect-all checkboxes

- New "Exporteren naar CSV" link below the "Per categorie" table
  (`GET /export`, `app/routes/dashboard.py::export_csv`) downloads
  exactly the currently selected Rekeningen/categorieën/period as a
  standalone CSV — every `afschrift` column, with foreign keys
  (Rekening, Mutatiesoort, categorie) resolved to their names instead of
  left as IDs, via a new query (`sql/queries/afschrift/export_for_user.sql`).
  The link's URL is built server-side from the request that rendered the
  page (`_export_url`), so it always matches what's on screen rather than
  offering a separate export filter. Refactored the month-range/
  selected-ID resolution `home()` already did into two shared helpers
  (`_resolve_month_range`, `_resolve_selected_ids`) so `export_csv`
  applies identical filtering semantics, including the same
  "everything selected" fallback when hit without params.
- "Alles selecteren"/"Alles deselecteren" chip buttons above both the
  Categorieën and Lijnen-in-de-grafiek checkbox groups
  (`app/static/js/dashboard.js`) — toggles just that group's checkboxes,
  doesn't submit the form.

## [0.0.27] - 2026-08-19 — Dashboard: expandable "Per categorie" rows

- Each row of the dashboard's "Per categorie" table can now be clicked
  (or activated with Enter/Space) to expand a nested table of the
  individual `afschrift` statements that row's Inkomsten/Uitgaven totals
  were summed from — so a total can be traced back to what actually
  makes it up, without leaving the dashboard. New query
  `sql/queries/afschrift/list_for_user.sql`, the unaggregated counterpart
  of `monthly_totals_for_user.sql` (same `:user_id`/`:start`/`:end`
  scoping, individual rows instead of monthly sums), run through the
  exact same Python-side Rekening/categorie selection filtering as the
  totals themselves (`app/routes/dashboard.py::home`) — the expanded
  list can never disagree with the total above it. Both the summary and
  detail row are server-rendered up front; `app/static/js/dashboard.js`
  only toggles the detail row's `hidden` attribute, no extra request.
- **Verified** on an isolated scratch copy: seeded statements across two
  categories plus an uncategorized one, one of them dated outside the
  filtered month — confirmed each category's expanded rows exactly match
  what its totals add up to, the out-of-range row never appears,
  unchecking the account empties the whole table, and selecting a single
  category shows only its own expand target.

## [0.0.26] - 2026-08-19 — Rekening verwijderen + docs cleanup

- **New**: an account (`Rekening`) can now be deleted from the profile
  page (`/user/{username}`), next to its entry in the Rekeningen list.
  This is all-or-nothing — there's no way to unlink a bank statement row
  from its account, so deleting one takes its *entire* `temp_afschrift`
  backlog and already-migrated `afschrift` history with it, in one
  transaction (`POST /accounts/{rekening_id}/delete`,
  `app/routes/accounts.py::delete_account`; new queries
  `sql/queries/temp_afschrift/delete_for_rekening.sql`,
  `sql/queries/afschrift/delete_for_rekening.sql`,
  `sql/queries/rekeningen/delete_rekening.sql`, run child-before-parent
  since neither table has `ON DELETE CASCADE` on `Rekening_ID`). Before
  the button is ever clicked, the page shows a JavaScript confirmation
  (`app/static/js/user.js`) that names the exact number of rows about to
  be removed (`sql/queries/rekeningen/count_data_for_user.sql`, wired
  in via `app/user_page.py::load_user_page_data`'s new `data_count` per
  Rekening) — there's no undo, so this is the only safety net.
- **Docs**: cleaned up several stale "not built yet" claims left over
  from before migration, ambiguous-match resolution, and the dashboard
  were actually finished — `README.md`, `docs/ARCHITECTURE.md` (Fase 3),
  `app/routes/review.py`'s docstring, and `review.html`'s on-page
  disclaimer all previously still said "Rekening corrigeren en kiezen
  tussen ambigue matches komen in latere stappen" even though picking a
  category on `/review` already resolves ambiguous rows exactly like
  unresolved ones, and migration/dashboard have been live since
  2026-08-17/18. "Rekening corrigeren" itself (reassigning a row to a
  different account, or editing an already-linked IBAN) turned out to
  not be worth building — deleting and re-linking the account, as above,
  covers the same need — so the docs now say that instead of leaving it
  listed as a future step.

## [0.0.25] - 2026-08-18 — Moved "Categorisatie opnieuw proberen" to /review + status filter

- **Moved** the "Categorisatie opnieuw proberen" button from `/upload` to
  the top of `/review` (Controle) — that's the page where its outcome
  (newly resolved/ambiguous rows) actually matters and is visible.
  `POST /upload/recategorize` → `POST /review/recategorize`
  (`app/routes/review.py`); removed from `app/routes/upload.py`/
  `upload.html` entirely. `app/categorization.py::recategorize_pending`
  itself is unchanged. The result message renders inline at the top of
  `/review`, unfiltered (all statuses shown), so anything that just
  changed is visible regardless of whatever status filter was active
  before the click.
- **New status filter on `/review`**: checkboxes (Onopgelost/Opgelost/
  Ambigu, `?status=&filtered=1` — same hidden-`filtered`-marker pattern
  as the dashboard) control which rows are *displayed* per Rekening
  table (`group.display_rows`). Counts, the "fully resolved" check, and
  migration eligibility always use the account's full, unfiltered row
  set (`group.rows`/`group.counts`/`group.all_resolved`) — filtering can
  never make an account look (or not look) migration-ready just because
  some rows are filtered out of view. A group with no rows matching the
  current filter shows a short message instead of an empty table.
- Docs: `docs/ARCHITECTURE.md` Fase 2 (recategorize location) and Fase 3
  (status filter, display-vs-full-set distinction) updated.
- **Verified** on an isolated scratch copy (real dev DB/server untouched,
  checksummed before/after): confirmed the button no longer appears on
  `/upload` and appears first (above the explanatory paragraph) on
  `/review`; the status filter correctly narrows the displayed rows
  while the totals line and migrate-button state stay based on the full
  set (e.g. filtering to "Opgelost" only showed 2 of 6 rows while the
  page still correctly reported "nog niet alle rijen opgelost"); a
  filter matching zero rows in a group shows the fallback message;
  `/review/recategorize` still resolves/flags rows correctly and
  re-renders unfiltered; the full save → migrate pipeline was exercised
  end-to-end afterward and still moved all 6 rows into `afschrift`
  correctly, confirming the filter changes didn't regress the existing
  save/migrate flow.

## [0.0.24] - 2026-08-18 — Upload page: "Categorisatie opnieuw proberen" button

- New button on `/upload` that re-runs automatic rule-based categorization
  on demand, without a re-upload — for when the user adds or edits a
  category/rule *after* already uploading a file. Reconsiders **all**
  of the user's `temp_afschrift` rows across all their accounts, any
  `processed` value — including already-resolved ones, in case a newly
  added rule now also matches a row that was previously resolved to
  exactly one category (surfaced as a fresh conflict, not silently kept).
- New query `sql/categorization/recategorize_temp_afschrift.sql`: same
  matching logic as `categorize_batch.sql`/`match_custom_rules.sql`, but
  targets `temp_afschrift` (not `temp_afschrift2`). Handles `processed = 1`
  rows asymmetrically, since there's no flag distinguishing an automatic
  match from a manual pick on `/review` (both are just `processed = 1`,
  see `sql/queries/temp_afschrift/set_category.sql`): an already-resolved
  row is only ever *promoted* to ambiguous (`processed = 2`) when a new
  rule now also matches it — never demoted back to unresolved just
  because zero rules currently match it (the normal case for a manual
  pick), and never has its category silently swapped for a different
  single match. Rows already `processed` 0 or 2 move freely to whatever
  the fresh match implies. Only rows whose outcome actually changed are
  updated/returned. One adaptation: `temp_afschrift` only keeps
  `Mutatiesoort_ID`, not the original raw text, so a rule's `Mutatiesoort`
  condition is checked against any raw label in `mutatiesoort_mapping`
  that resolves to the same ID.
- `app/categorization.py::recategorize_pending` (+ `RecategorizeResult`
  dataclass, counting only *changed* rows) orchestrates it;
  `POST /upload/recategorize` (`app/routes/upload.py`) wires it to the
  new button and re-renders `upload.html` with the outcome (rows changed
  / now resolved / now unresolved / now ambiguous — with a note pointing
  at `/review` when a new conflict appeared — or a "nothing changed"
  message).
- Docs: `docs/ARCHITECTURE.md` Fase 2 and `sql/categorization/README.md`
  updated to describe the new query and its promote-only-to-ambiguous and
  `Mutatiesoort` adaptations.
- **Verified** on isolated scratch copies (real dev DB/server untouched
  throughout, checksummed before/after): a plain positive case (rows
  unresolved → now match a new rule) counts and categorizes correctly and
  reports only the changed rows; a row manually resolved on `/review`
  (matching zero rules) is left completely untouched by a later retry
  even after a new rule is added that happens to also match it singly
  (protection against silently swapping a manual pick's category); an
  **automatically**-resolved row that a newly added rule now *also*
  matches is correctly promoted to ambiguous with its category cleared,
  and shows up in the "nu ambigu" count with the `/review` pointer;
  repeated retries with no rule changes are idempotent (`None`, "nothing
  changed"); a second, ruleless user's own pending rows are unaffected by
  the first user's rules (per-user isolation holds) even though the row
  content would otherwise match. Also confirmed via `/login` +
  `POST /upload/recategorize` against real throwaway servers that all
  three message states (nothing changed / resolved / newly ambiguous)
  render correctly end-to-end.

## [0.0.23] - 2026-08-18 — Fix: ING NL importer had the balance-chain row order backwards

- **Bug**: `app/importers/ing_nl.py::parse()` returned rows in the CSV's own
  file order and `BaseImporter`'s contract assumed that file order *was*
  chronological ascending (oldest first). That assumption was wrong for
  ING's actual "Alle transacties" export, which lists the **newest**
  transaction first and the **oldest** last — the reverse. A real 428-row
  export uploaded today was rejected with "Saldoketen doorbroken" (see
  `logs/audit.log`, 2026-08-18 15:48) purely because of this — every row's
  `Saldo_na_mutatie` was being chained against the wrong predecessor.
- **Fix**: `BaseImporter.parse()`'s contract (`app/importers/base.py`) now
  states explicitly that it must return chronological-ascending order
  regardless of the source format's own native order; each importer is
  responsible for reordering internally if needed.
  `IngNlImporter.parse()` now does `rows.reverse()` before returning, with
  a comment explaining why. `docs/ARCHITECTURE.md`'s Fase 1 section
  (uploadpijplijn) updated to match, including a short note on why the old
  assumption broke real uploads.
- **Test fixtures**: `testdata/upload/01_batch_ok.csv`,
  `08_batch_ok_2e_rekening.csv`, and `03_batch_unmapped_mutatiesoort.csv`
  (the multi-row fixtures, where relative order actually matters) were
  rewritten newest-first, matching real ING export order, so they still
  exercise the importer's reversal instead of accidentally being "already
  correct" in file order. `testdata/README.md` notes that its row-by-row
  walkthrough table numbers rows chronologically (Rij 1 = oldest = the
  *last* line in the file), not by file position.
- **Verified** on an isolated scratch copy (schema + seed + a throwaway
  user/Rekening pair, real dev DB/server untouched — checksum confirmed
  unchanged before/after): uploading the corrected `01_batch_ok.csv`
  now inserts rows in true chronological order (`ID` 1..6 = 2026-08-01
  through 2026-08-06, checked directly against `temp_afschrift`) and is
  **accepted**; the balance-break fixture, an exact re-upload of batch 1,
  and the unmapped-mutatiesoort fixture are all still correctly
  **rejected**, order-independent; the second account's batch (`08_...`)
  accepts independently of the first. No migration needed for the real
  dev DB — the earlier real-world rejection rolled back before ever
  committing, so no corrupted rows exist to clean up.

## [0.0.22] - 2026-08-18 — Dashboard: month-range filtering, Rekening/categorie selection, linegraph

- Date filtering is now whole calendar months only (`?start_month=&end_month=`,
  "YYYY-MM" via `<input type="month">`) instead of arbitrary dates —
  `app/dashboard_chart.py`'s `parse_month`/`month_range`/`month_end`.
  Default changed from "this month" to the **last 6 months**, since a
  single month would make the new linegraph a single dot. Presets: deze
  maand, laatste 6 maanden, dit jaar, alles (now computed from the
  user's actual earliest/latest ledger date via the new
  `sql/queries/afschrift/date_bounds_for_user.sql`, not an arbitrary
  epoch range — that stopped making sense once the input widget requires
  a real "YYYY-MM").
- The user can now choose exactly which Rekeningen and categorieën count
  towards Inkomsten/Uitgaven/Verschil (checkboxes; everything selected by
  default on a fresh page load). A hidden `filtered=1` field distinguishes
  "just filtered — trust exactly what's checked, including a deliberate
  all-zero selection" from "fresh load — default to everything". Selection
  filtering happens in Python, not a dynamic SQL `IN (...)` list (this
  project keeps all SQL as static tracked files — see the new note at the
  bottom of `sql/queries/README.md`): one query,
  `sql/queries/afschrift/monthly_totals_for_user.sql` (replaces
  `totals_per_category_for_user.sql`), fetches per-month/per-Rekening/
  per-category sums for the whole range — a small fixed result set — and
  `app/routes/dashboard.py` filters/sums it according to the checked IDs.
  "Zonder categorie" (uncategorized rows) is its own selectable
  pseudo-category throughout, so it's never silently in- or excluded.
- New linegraph, one point per selected month, for any combination of
  Inkomsten/Uitgaven/Verschil totals and/or individual (still in-scope)
  categories — a category's line is its net (bij − af) per month, the
  same unit as Verschil. Rendered as inline SVG, built server-side by the
  new `app/dashboard_chart.py` (pure coordinate math) and
  `app/templates/index.html` (the actual `<svg>` markup) — no charting
  library, consistent with the project's plain-CSS/JS frontend.
  `app/static/js/dashboard.js` adds a crosshair + one shared tooltip
  listing every visible line at the nearest month, and makes the preset
  buttons re-submit the filter form with just the month range changed
  (a plain link would have reset the Rekening/categorie/line checkboxes).
- Colors follow the dataviz skill's validated categorical palette
  (`--series-*` custom properties in `style.css`, with the theme
  toggle's light/dark pairing). Inkomsten/Uitgaven/Verschil get fixed
  colors + dash patterns always; each category's color and dash pattern
  are derived from its own `cat_id` (`cat_id % n`), never from its
  position in the current selection — checking/unchecking one category
  never repaints another's line. Ran the skill's palette validator: the
  3 aggregate lines pass all-pairs cleanly; the full aggregates+5-category
  set does not clear the all-pairs CVD floor (a known limit of any
  8-hue categorical set per the skill's own reference palette docs) —
  mitigated with per-line dash patterns (not color-only identity), a
  legend, hover tooltips with text values, and the always-present
  per-category table as the exact-numbers fallback.
- Verified end-to-end against an isolated scratch copy seeded with 7
  months of realistic multi-Rekening, multi-category data: default view
  totals, explicit Rekening/categorie/graph-line filtering (including an
  isolated "Zonder categorie"-only view), the deliberate all-unchecked
  zero state, and a graph-line request for a category outside the
  calculation scope being silently (and correctly) dropped rather than
  erroring. Confirmed no impact on unrelated pages (`/review`, `/upload`,
  the profile page) or the real dev DB/server.

## [0.0.21] - 2026-08-18 — Light/dark theme toggle

- Theming was purely `prefers-color-scheme`-driven before (no way to
  override the OS/browser setting). Added a 🌙/☀️ button in the topbar
  (`base.html`, `#theme-toggle`) that sets an explicit `data-theme="light"`
  or `"dark"` attribute on `<html>`, persisted in
  `localStorage["boekhouding-theme"]`.
- `style.css`: `:root` now holds the light palette as the unconditional
  default; `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {...} }`
  still auto-follows the system when the user hasn't chosen, and
  `:root[data-theme="dark"] {...}` lets an explicit choice win over the
  system in either direction — an explicit `light` overrides a dark
  system, an explicit `dark` overrides a light system.
- New `app/static/js/theme.js` (the project's first JS file — `defer`-
  loaded) drives the button: computes the currently *effective* theme
  (explicit attribute, else system preference) so the very first click
  always flips what's actually on screen rather than "confirming" the
  current system theme as a no-op. A small inline script at the top of
  `base.html`'s `<head>` (must run before the stylesheet, so it can't
  live in the external file) re-applies a stored choice immediately on
  every page load, avoiding a flash of the wrong theme before the
  deferred script would otherwise fix it up.
- Verified against an isolated scratch copy: `theme.js` and the button
  markup are served/rendered correctly; traced the CSS cascade by hand
  for all four (explicit choice × system preference) combinations against
  actual selector specificity — each resolves to the intended theme.

## [0.0.20] - 2026-08-18 — Idle auto-shutdown for the launcher scripts

- The server can now shut itself down after a period of no HTTP traffic —
  scoped specifically to the "launcher" way of starting the app
  (`start_app.sh`/`.bat`/`.ps1`), not to `python run.py` during
  development. Considered and rejected "shut down when the browser tab
  closes": this app is server-rendered, full-page-navigation (Jinja2), so
  every internal link click fires the same `beforeunload`/`pagehide`
  events a real tab close would — there's no reliable way to tell those
  apart client-side, making idle time the only robust signal.
- `run.py` now branches on `BOEKHOUDING_RELOAD` (default unset/"1" =
  today's `uvicorn.run(..., reload=True)`, unchanged). Set to `"0"` (what
  the launcher scripts export) and it instead builds `uvicorn.Config` +
  `uvicorn.Server` directly and stashes the server on
  `app.state.uvicorn_server` — the hook the idle-shutdown watchdog needs
  to flip `should_exit` and trigger a normal graceful shutdown. `reload`
  mode has no such single, addressable server instance (the actual app
  runs in a supervised subprocess), so idle-shutdown is a deliberate
  no-op there — verified: default `python run.py` stays up indefinitely
  with zero traffic. Also added `BOEKHOUDING_PORT` (default unchanged,
  8000) purely so this could be tested on a throwaway port without
  touching the real dev server.
- New `app/idle_shutdown.py`: `record_activity()` (called from the
  existing `log_requests` middleware in `app/main.py` on every request)
  resets a last-activity timestamp on `app.state`; a `watch_idle()`
  background task (started from the FastAPI `lifespan`, cancelled on
  shutdown) polls every 15s and sets `should_exit = True` once idle time
  crosses `BOEKHOUDING_IDLE_TIMEOUT_MINUTES` (env var, default 30 for the
  launcher scripts, `0` = disabled). Logged in `logs/app.log` same as any
  other startup/shutdown event.
- Verified end-to-end against an isolated scratch copy of the app (own
  DB, alternate port): a launcher-mode server left idle self-terminates
  gracefully within one ~15s check cycle past the configured timeout;
  periodic requests keep resetting the clock and keep it alive; default
  reload-mode `python run.py` is completely unaffected (confirmed alive
  after 20+ idle seconds). The real dev DB/server were never touched by
  any of this testing.

## [0.0.19] - 2026-08-18 — Windows launcher

- Added `start_app.ps1` (the launcher logic, ported from `start_app.sh`:
  poll `http://127.0.0.1:8000`, start `.venv\Scripts\python.exe run.py`
  in the background if it's not already up, wait for it, open the
  default browser) and `start_app.bat` (a double-clickable entry point
  that just invokes the `.ps1`, since `.ps1` files don't run on
  double-click by default). Background process output goes to
  `logs\launcher-stdout.log`/`logs\launcher-stderr.log`. No app code
  changes were needed — `app/config.py` already resolves every path via
  `pathlib`, and `run.py`'s only dependency (`uvicorn[standard]`) already
  skips its Unix-only `uvloop` extra on Windows via its own packaging
  markers. README's "Snelkoppeling om te starten" section now documents
  both platforms, including the standard Windows "Verzenden naar →
  Bureaublad" way to turn `start_app.bat` into a desktop shortcut.

## [0.0.18] - 2026-08-18 — One-click desktop launcher (Linux)

- Added `start_app.sh`: starts `run.py` in the background if it isn't
  already running (checked by polling `http://127.0.0.1:8000`), waits for
  it to come up, then opens it in the default browser via `xdg-open`
  (falls back to `gio open`). Safe to click repeatedly — if the server's
  already up it just (re)opens the browser instead of starting a second
  instance. Launcher output goes to `logs/launcher.log`; the app's own
  logs are unaffected.
- Added `boekhouding.desktop` (freedesktop `.desktop` entry, points at
  `start_app.sh` by absolute path) so the launcher can be dropped onto
  the GNOME desktop and/or the applications menu as a real clickable
  shortcut — see the new "Snelkoppeling om te starten" section in
  `README.md` for the copy/`chmod` steps and the one-time GNOME "trust
  this launcher" prompt.

## [0.0.17] - 2026-08-17 — Dedicated rule-edit page

- Replaced the profile page's inline per-column "+ keyword" mini-forms
  and per-keyword delete buttons with a single "Aanpassen" button per
  rule, linking to a new dedicated page,
  `GET/POST /categories/regels/{regel_id}/edit`
  (`app/routes/categories.py::edit_regel_page`/`save_regel`, template
  `regel_edit.html`). The profile page's rule cards are now read-only
  summaries (column + keyword chips, no inline edit controls) plus
  "Aanpassen" and "Regel verwijderen".
- The edit page shows **all nine** supported columns at once (not just
  the ones the rule currently has), each pre-filled with its existing
  keywords (one per line) and combine_mode where set. Saving replaces
  the rule's entire column/keyword set wholesale in one transaction
  (`remove_regel_kolommen_for_regel.sql`, then the same insert queries
  `add_regel` uses) — only after the submission validates, so a rejected
  save never touches the existing rule. This means a column can now be
  added, have its AND/OR mode changed, or be cleared out entirely (=
  removed from the rule) just by editing that column's textarea, lifting
  the earlier v1 limitation that adding a new column or changing
  combine_mode required deleting and recreating the whole rule.
  Multi-keyword-per-column entry (one per line, or comma-separated except
  for `Bedrag_eur`/`Saldo_na_mutatie` where a comma is the decimal
  separator) now works identically on both the create-rule form and this
  edit page.
- On a validation error (e.g. an invalid Af_bij value, an unparseable
  amount, or clearing every column), the edit page re-renders with
  exactly what was just typed, not the stale pre-edit values — so a typo
  in one column doesn't lose edits already made to others.
- Removed the now-superseded granular endpoints
  (`POST /categories/regels/{regel_id}/kolommen/{kolom_id}/keywords`,
  `POST /categories/regels/keywords/{keyword_id}/delete`) and their
  now-dead cleanup queries (`remove_empty_regel_kolommen.sql`,
  `remove_empty_regels.sql` — no longer needed since the edit page never
  leaves a column-condition or rule empty, it just deletes and
  recreates the whole set atomically).
- Verified against an isolated scratch copy of the real (already
  rule-migrated) database: the edit page pre-fills correctly from an
  existing rule; adding a brand-new column to an existing rule and
  removing an existing column in the same save both work; submitting all
  columns empty is rejected (400, rule left untouched) with the empty
  state preserved on the re-rendered page; a second user attempting to
  view or save another user's rule is redirected without touching
  anything, on both the GET and POST route. No schema change was needed
  for this, so nothing further to migrate on the real database.

## [0.0.16] - 2026-08-17 — General rule-based categorization

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

## [0.0.15] - 2026-08-17 — Profile page + real dashboard (Fase 5)

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

## [0.0.14] - 2026-08-17 — Fase 4: migrate resolved rows into `afschrift`

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

## [0.0.13] - 2026-08-17 — Paired Naam keyword for difficult categorization

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

## [0.0.12] - 2026-08-17 — Per-user categories & keywords

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

## [0.0.11] - 2026-08-14 — `/review`: save per table, "ready for migration" check, wider page

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

## [0.0.10] - 2026-08-14 — `/review`: per-account tables, editable category

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

## [0.0.9] - 2026-08-14 — Two more isolated test batches; `/review` shows everything

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

## [0.0.8] - 2026-08-14 — Hand-driven test data for the upload pipeline

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

## [0.0.7] - 2026-08-14 — Third categorization signal: internal transfers

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

## [0.0.6] - 2026-08-14 — Read-only `/review` overview

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

## [0.0.5] - 2026-08-14 — Categorization (`temp_afschrift2` → `temp_afschrift`)

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

## [0.0.4] - 2026-08-13 — Confirmed per-account isolation of the upload checks

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

## [0.0.3] - 2026-08-13 — Last-login display, Dutch translation

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

## [0.0.2] - 2026-08-13 — Login/signup, accounts, and the upload pipeline

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

## [0.0.1] - 2026-08-13 — Project scaffold

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
