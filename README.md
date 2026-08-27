# Boekhouding

Een persoonlijke boekhoudapp: upload bankafschriften, categoriseer
uitgaven (Auto, Kleding, Levensmiddelen, …), en bekijk/analyseer ze over
tijd.

- **Backend:** Python (FastAPI)
- **Database:** SQLite, volledig aangestuurd door bijgehouden `.sql`-bestanden onder `sql/`
- **Frontend:** server-side gerenderde HTML (Jinja2-templates) + platte CSS/JS
- **Uitvoeringsmodus:** lokale webserver, geopend in een browser

Huidige status: inloggen/aanmelden (geen wachtwoorden — je kiest gewoon
wie je bent), rekeningen koppelen of weer verwijderen, en het uploaden
van een ING NL-bankafschrift werken end-to-end, inclusief automatische
categorisering erna (per-rekening saldoketen-, dubbele-rij- en
mutatiesoort-controles, alles-of-niets, gevolgd door automatische
categorie-toewijzing zodra een batch geaccepteerd is). Op `/review`
staat, per rekening in een eigen tabel, elke `temp_afschrift`-rij
(opgelost én niet, ook ambigue) met een dropdown om de categorie te
kiezen of corrigeren — één opslaan-knop per tabel verwerkt alle rijen van
die rekening ineens, en checkt meteen of de rekening klaar is voor
migratie naar het permanente grootboek (`afschrift`), wat vanaf diezelfde
pagina met één knop kan zodra alle rijen opgelost zijn. Het dashboard
(`/`) rapporteert over dat grootboek: filterbaar op maand, rekening en
categorie, met een lijngrafiek. Een rekening verwijderen
(profielpagina, `/user/{username}`) neemt haar volledige
`temp_afschrift`- én `afschrift`-geschiedenis in dezelfde
alles-of-niets-actie mee, met een voorafgaande waarschuwing die precies
telt hoeveel rijen dat raakt — er is geen manier om alleen de rekening
zelf te hernoemen of één rij naar een andere rekening te verplaatsen; wie
dat nodig heeft, verwijdert en koppelt opnieuw. Zie
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) voor het volledige ontwerp en
[CHANGELOG.md](CHANGELOG.md) voor wat er tot nu toe daadwerkelijk gebouwd
is.

## Installatie (elke machine)

Vereist Python 3.10+.

**Alleen op Debian/Ubuntu-gebaseerde Linux (bijv. Ubuntu, Mint):** de
systeem-Python daar bevat de `venv`-module niet standaard — die zit in
een apart pakket. Zonder dit pakket geeft `python -m venv .venv` hieronder
een foutmelding dat `ensurepip`/`venv` ontbreekt. Installeer het eenmalig:

```bash
sudo apt update
sudo apt install python3-venv
```

Op andere systemen (Windows, macOS, Fedora, Arch, …) zit `venv` al
ingebouwd in Python en is deze stap niet nodig.

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

### Snelkoppeling om te starten

Na de installatie hierboven kan de app ook met één klik gestart worden,
zonder terminal. Beide varianten doen hetzelfde: starten de server op de
achtergrond (of merken op dat hij al draait) en openen daarna automatisch
de browser op http://127.0.0.1:8000.

Gestart via deze snelkoppelingen sluit de server zichzelf ook weer af na
**30 minuten zonder verkeer** — handig omdat je hem niet handmatig hoeft
af te sluiten. (Reageren op "browsertabblad gesloten" kan niet
betrouwbaar: elke interne link in de app is óók een paginanavigatie, dus
er is geen manier om dat te onderscheiden van écht wegklikken — vandaar
inactiviteit als signaal.) Dit geldt niet voor gewoon `python run.py`
tijdens ontwikkelen — die blijft ongewijzigd draaien tot je hem zelf
stopt. Zelf instellen kan via een omgevingsvariabele vóór het starten van
de snelkoppeling, bijvoorbeeld 10 minuten, of `0` om uit te schakelen:

```bash
# Linux, vóór ./start_app.sh:
export BOEKHOUDING_IDLE_TIMEOUT_MINUTES=10

# Windows, in PowerShell vóór start_app.bat:
$env:BOEKHOUDING_IDLE_TIMEOUT_MINUTES = "10"
```

**Linux:**

```bash
./start_app.sh
```

Om er een echte snelkoppeling van te maken (bureaublad + toepassingenmenu):

```bash
cp boekhouding.desktop ~/Desktop/
cp boekhouding.desktop ~/.local/share/applications/
chmod +x ~/Desktop/boekhouding.desktop ~/.local/share/applications/boekhouding.desktop
```

`boekhouding.desktop` verwijst naar `start_app.sh` via een absoluut pad,
dus pas dat pad aan als de map ooit verplaatst wordt. Op het bureaublad
kan GNOME de eerste keer "Vertrouw je deze toepassing?" vragen — kies
"Toestaan" (of via rechtermuisknop op het icoon → Eigenschappen →
Toestaan als programma).

**Windows:**

Dubbelklik `start_app.bat` (dit roept `start_app.ps1` aan — vereist
PowerShell, standaard aanwezig op Windows 10/11). Verwacht dezelfde
`.venv`-map als bij de installatiestappen hierboven, dus met
`.venv\Scripts\python.exe` erin.

Om een snelkoppeling op het bureaublad te zetten: rechtermuisklik op
`start_app.bat` → **Verzenden naar** → **Bureaublad (snelkoppeling
maken)**. De snelkoppeling werkt zolang hij naar dit bestand blijft
wijzen, ook als je hem hernoemt of van icoon verandert (rechtermuisklik
→ Eigenschappen → Pictogram wijzigen).

Het databasebestand en de logs zijn gitignored (zie `data/`, `logs/`) —
ze worden lokaal gegenereerd en nooit gecommit, zodat elke kloon start
vanuit dezelfde bijgehouden bron.

### Bijwerken

De app controleert bij het opstarten zelf of er een nieuwere versie op
de git-remote staat, en toont bovenaan elke pagina een banner zodra dat
zo is — met daarin alles wat je gemist hebt, niet alleen de laatste
wijziging. Op "Nu bijwerken" klikken pullt de nieuwste versie en start de
server zelf opnieuw op; er verandert nooit iets zonder die klik. Zie
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) ("Bijwerken (updates)") voor
hoe dat precies werkt.

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
