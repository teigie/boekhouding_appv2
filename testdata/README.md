# Testdata: hand-driven upload pipeline walkthrough

CSV fixtures for manually exercising the whole pipeline — upload gates
(both kinds), categorization, and the `/review` overview — through the
actual running app, not just the automated verification already done in
`CHANGELOG.md`. Every outcome below was cross-checked by running
`app.upload.process_upload()` directly against a scratch copy of the dev
database with the setup steps applied, so the expected results are exact,
not guesses.

Format: ING NL CSV (see `app/importers/ing_nl.py`) — this is what you pick
as "ING NL (CSV export)" on `/upload`.

These fixtures list rows **newest-first**, matching ING's actual export
order — the top data row (right after the header) is the most recent
transaction, the bottom row the oldest. `app/importers/ing_nl.py::parse()`
reverses this to chronological order before anything downstream sees it,
so the "Rij" numbers in the row-by-row table below refer to that
chronological order (Rij 1 = oldest = the *last* data row in the file),
not the file's own top-to-bottom position.

## Setup (once)

1. Log in / sign up as a user — e.g. `TestUser` — with account
   `NL01TEST0000000001` (signup requires a Name + a Rekening together).
2. On `/accounts`, link a second account: `NL01TEST0000000002`. It's the
   counterparty used by the "Interne overboeking" rows below (batch 1's
   rows 2/6, and batch 7). **If this account isn't linked yet when you
   upload a batch, those rows just don't get the internal-transfer match**
   — they fall back to whatever the other signals decide (see the note
   under batch 1 below) — nothing breaks, but the categorization outcome
   changes. Link it before uploading if you want the internal-transfer
   cases to behave as described here.
3. Leave `NL01TEST0000000009` unlinked to anyone — it's used by batch 2 to
   test the "unregistered account" rejection.
4. Optional, only needed for batch 4 (the "wrong user" rejection): log
   out, sign up as a second user (e.g. `OtherUser`) with account
   `NL01TEST0000000003`, then log out and log back in as `TestUser`.
   Skip batch 4 if you don't want to bother with a second user.

This session already added one keyword to your dev database so batch 1
can demonstrate "difficult" (Mededeling-based) categorization, since that
table started out empty: `afschrift_cat_mededeling_keywords` now has
`"vakantiegeld" -> Vakantie`. It's real data in `data/boekhouding.db`, not
scratch — remove it later if you don't want it kept.

## Upload these in order, via `/upload`

| # | Bestand | Rekening | Verwacht resultaat |
|---|---|---|---|
| 1 | `01_batch_ok.csv` | NL01TEST0000000001 | **Geaccepteerd**, 6 rijen. Zie de rij-voor-rij tabel hieronder. |
| 2 | `02_batch_unregistered_account.csv` | NL01TEST0000000009 | **Afgewezen** — rekening nog niet geregistreerd. |
| 3 | `03_batch_unmapped_mutatiesoort.csv` | NL01TEST0000000001 | **Afgewezen** — onbekende mutatiesoort "Cryptobetaling". Beide rijen (ook de verder prima tweede rij) worden geweigerd — alles-of-niets. |
| 4 | `04_batch_wrong_user.csv` | NL01TEST0000000003 | **Afgewezen** — rekening niet aan jouw gebruiker gekoppeld. (Vereist setup-stap 4.) |
| 5 | `05_batch_balance_break.csv` | NL01TEST0000000001 | **Afgewezen** — saldoketen doorbroken. Upload dit ná batch 1 (hoeft verder nergens tussen). |
| 6 | `01_batch_ok.csv` nogmaals | NL01TEST0000000001 | **Afgewezen** — saldoketen doorbroken. Een exacte herimport breekt de keten vanzelf (zie `docs/ARCHITECTURE.md`) — dit is dus ook een (impliciete) dedup-controle in actie, niet alleen de saldoketen. |
| 7 | `06_batch_ambiguous.csv` | NL01TEST0000000001 | **Geaccepteerd**, 1 rij, `processed=2` (ambigu) — geïsoleerd, één enkele rij, geen afhankelijkheid van setup-stap 2. Upload dit ná batch 1 (bouwt voort op het saldo). |
| 8 | `07_batch_interne_overboeking.csv` | NL01TEST0000000001 | **Geaccepteerd**, 1 rij, `processed=1`, categorie Interne overboeking — geïsoleerd, één enkele rij, alleen deze match (geen Naam/Mededeling-keyword erbij). Vereist setup-stap 2. Upload dit ná batch 1 (en na batch 7 als je die ook doet — bouwt voort op het saldo). |

Batches 2–8 are independent of each other and can be uploaded in any
order relative to one another — batches 5, 7, and 8 just need to come
*after* batch 1 (they're built to continue its balance).

## What batch 1 exercises, row by row

| Rij | Naam | Signaal | Resultaat (mét setup-stap 2) |
|---|---|---|---|
| 1 | Jumbo boodschappen | Naam-keyword "Jumbo" | `processed=1`, Levensmiddelen |
| 2 | Overboeking naar spaarrekening | Tegenrekening = je eigen NL01TEST0000000002 | `processed=1`, Interne overboeking |
| 3 | Onbekende winkel ABC | geen enkel signaal | `processed=0`, onopgelost |
| 4 | Salaris werkgever | geen enkel signaal | `processed=0`, onopgelost |
| 5 | Onbekend bedrijf | Mededeling-keyword "vakantiegeld" (Naam zelf matcht niets) | `processed=1`, Vakantie — bewijst dat de Mededeling-route ook zelfstandig werkt |
| 6 | Jumbo overboeking | Naam-keyword "Jumbo" **en** Tegenrekening = eigen rekening | `processed=2`, ambigu (twee verschillende categorieën kwamen overeen) |

**Zonder setup-stap 2** (NL01TEST0000000002 nog niet gekoppeld op het
moment van uploaden): rijen 2 en 6 missen het interne-overboeking-signaal.
Rij 2 heeft dan geen enkel signaal meer over → `processed=0`. Rij 6 houdt
alleen de Naam-match "Jumbo" over → `processed=1`, Levensmiddelen (niet
meer ambigu). Dat is precies wat er gebeurt als je die stap oversloeg —
niets is stuk, het is gewoon minder signalen om mee te werken. Batches 7
en 8 hierboven zijn er om beide gevallen (ambigu, interne overboeking)
alsnog geïsoleerd te kunnen zien, onafhankelijk van of je terug wilt naar
batch 1.

`/review` toont alle rijen van je rekeningen, elke `processed`-status —
niet meer alleen onopgelost/ambigu.
