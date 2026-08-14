# Boekhouding

Een persoonlijke boekhoudapp: upload bankafschriften, categoriseer
uitgaven (Auto, Kleding, Levensmiddelen, …), en bekijk/analyseer ze over
tijd.

- **Backend:** Python (FastAPI)
- **Database:** SQLite, volledig aangestuurd door bijgehouden `.sql`-bestanden onder `sql/`
- **Frontend:** server-side gerenderde HTML (Jinja2-templates) + platte CSS/JS
- **Uitvoeringsmodus:** lokale webserver, geopend in een browser

Huidige status: inloggen/aanmelden (geen wachtwoorden — je kiest gewoon
wie je bent), rekeningen koppelen, en het uploaden van een ING NL-
bankafschrift werken end-to-end, inclusief automatische categorisering
erna (per-rekening saldoketen-, dubbele-rij- en mutatiesoort-controles,
alles-of-niets, gevolgd door automatische categorie-toewijzing zodra een
batch geaccepteerd is). Op `/review` staat, per rekening in een eigen
tabel, elke `temp_afschrift`-rij (opgelost én niet) met een dropdown om
de categorie te corrigeren of een nieuwe toe te voegen — één opslaan-knop
per tabel verwerkt alle rijen van die rekening ineens, en checkt meteen
of de rekening klaar is voor migratie (zonder daadwerkelijk te
migreren). Een rekening corrigeren, kiezen tussen ambigue matches,
migratie naar het permanente grootboek, en bekijken/rapporteren zijn nog
niet gebouwd. Zie
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) voor het volledige ontwerp en
[CHANGELOG.md](CHANGELOG.md) voor wat er tot nu toe daadwerkelijk gebouwd
is.

## Installatie (elke machine)

Vereist Python 3.10+.

```bash
git clone <this repo>
cd boekhouding_appv2

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt
python run.py
```

Open daarna http://127.0.0.1:8000 in een browser. Bij de eerste run wordt
de SQLite-database automatisch aangemaakt op `data/boekhouding.db` vanuit
`sql/schema.sql` + `sql/seed_data.sql` — niets om handmatig te
configureren.

Het databasebestand en de logs zijn gitignored (zie `data/`, `logs/`) —
ze worden lokaal gegenereerd en nooit gecommit, zodat elke kloon start
vanuit dezelfde bijgehouden bron.

## Projectstructuur

```
app/                    FastAPI-applicatie
  config.py              Paden (relatief, overdraagbaar tussen machines)
  db.py                  SQLite-verbinding + eenmalige schema/seed-initialisatie
  session.py             Login/sessie-helpers (geen wachtwoorden — zie ARCHITECTURE.md)
  templating.py          Gedeelde Jinja2Templates-instantie
  logging_config.py      Logging-opzet (technische log + audit-log van datawijzigingen)
  upload.py              Uploadpijplijn: parsen -> invoegen -> controles -> commit/rollback -> categorisering
  categorization.py      Categoriseert een rekening's temp_afschrift2-achterstand naar temp_afschrift
  main.py                Startpunt van de app: middleware, routers
  importers/             Één BaseImporter-subklasse per bank/exportformaat
    base.py               Gedeelde interface
    ing_nl.py              ING NL CSV
    registry.py            format_id -> importer, voor de dropdown op het uploadformulier
  routes/                 HTTP-routes, één bestand per scherm
    auth.py                /login, /login/new, /logout
    accounts.py            /accounts (bekijken + een Rekening koppelen)
    dashboard.py            /
    upload.py               /upload
    review.py                /review (overzicht per rekening + categorie corrigeren/toevoegen)
  templates/              Jinja2 HTML-templates
  static/                 CSS/JS, ongewijzigd geserveerd

sql/                    Elke SQL-instructie die de app uitvoert, als bijgehouden bestanden
  schema.sql              CREATE TABLE-instructies
  seed_data.sql           Verplichte referentiedata (categorieën, mutatiesoorten)
  optional/               Optionele/voorbeelddata (bijv. de categorie-keywords van één persoon)
  upload/                 Post-insert continuïteitscontroles per rekening (saldoketen + dedup)
  categorization/         Ruwe upload -> opgeloste, gecategoriseerde rijen
  migration/              Opgeloste rijen -> permanent grootboek (nog niet gebouwd)
  queries/                App-gerichte selects + herbruikbare schrijf-templates
    users/                  login/aanmeld-queries
    rekeningen/              rekening-queries
    mutatiesoorten/          mutatiesoort-queries (pre-insert upload-gate + categorisering)
    categorieen/             categorie-queries
    temp_afschrift/          /review: alle-rijen-query + categorie zetten/corrigeren
    reference_data/          categorieën & keywords toevoegen/verwijderen na installatie

data/                   Gegenereerde SQLite-database + sessiegeheim (gitignored)
logs/                   Gegenereerde runtime-logs (gitignored)
docs/                   Architectuur-/ontwerpdocumentatie
testdata/               Hand-doorlopen testscenario's voor de upload-/categoriseringspijplijn
run.py                   Start de lokale server
```

## Testen

`testdata/README.md` bevat een stap-voor-stap doorloop van de hele
pijplijn (upload -> beide soorten controles -> categorisering ->
`/review`) met kant-en-klare CSV-bestanden in `testdata/upload/`, elk met
een vooraf geverifieerd verwacht resultaat.

## Logs

- `logs/app.log` — technische/runtime-log (opstarten, requests, fouten),
  wordt tijdens het draaien van `run.py` ook naar de console geschreven.
- `logs/audit.log` — een overzicht van datawijzigende events: uploads
  geaccepteerd of afgewezen (en waarom — ketenbreuk, duplicaat,
  ongeregistreerde/verkeerde-gebruiker-rekening), één regel per rekening
  per uploadpoging. Gemigreerde rijen etc. sluiten hier later bij aan
  zodra die functionaliteit bestaat. Bewust gescheiden van `app.log`,
  omdat dit bedoeld is als blijvend overzicht, niet als debug-stream.

Beide roteren automatisch en zijn gitignored.
