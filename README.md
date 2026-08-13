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
bankafschrift (met per-rekening saldoketen- en dubbele-rij-controles,
alles-of-niets) werken allemaal end-to-end. Verrijking/categorisering,
handmatige controle, migratie naar het permanente grootboek, en
bekijken/rapporteren zijn nog niet gebouwd. Zie
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) voor het volledige ontwerp
en [CHANGELOG.md](CHANGELOG.md) voor wat er tot nu toe daadwerkelijk
gebouwd is.

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
  upload.py              Uploadpijplijn: parsen -> invoegen -> controles -> commit/rollback
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
  templates/              Jinja2 HTML-templates
  static/                 CSS/JS, ongewijzigd geserveerd

sql/                    Elke SQL-instructie die de app uitvoert, als bijgehouden bestanden
  schema.sql              CREATE TABLE-instructies
  seed_data.sql           Verplichte referentiedata (categorieën, mutatiesoorten)
  optional/               Optionele/voorbeelddata (bijv. de categorie-keywords van één persoon)
  upload/                 Controleert een ruwe upload per rekening (saldoketen + dedup)
  enrichment/             Ruwe upload -> opgeloste, gecategoriseerde rijen (nog niet gebouwd)
  migration/              Opgeloste rijen -> permanent grootboek (nog niet gebouwd)
  queries/                App-gerichte selects + herbruikbare schrijf-templates
    users/                  login/aanmeld-queries
    rekeningen/              rekening-queries
    categorieen/             categorie-queries
    reference_data/          categorieën & keywords toevoegen/verwijderen na installatie

data/                   Gegenereerde SQLite-database + sessiegeheim (gitignored)
logs/                   Gegenereerde runtime-logs (gitignored)
docs/                   Architectuur-/ontwerpdocumentatie
run.py                   Start de lokale server
```

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
