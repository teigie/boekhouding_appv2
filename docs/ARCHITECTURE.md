# Architectuur

Hoe de app werkt, en waarom hij zo gebouwd is. Geschreven voor iedereen
die nieuw is bij het project — een toekomstige medewerker, of je
toekomstige zelf na een tijdje weg te zijn geweest.

## Wat dit is

Een persoonlijke boekhoudapp. Bankafschriften worden geüpload, doorlopen
een automatische categoriseringspijplijn, worden handmatig gecontroleerd
waar de automatisering er niet uitkomt, en komen terecht in een permanent
grootboek (`afschrift`) dat gebruikt wordt om uitgaven te bekijken,
sorteren en rapporteren.

Domeinbegrippen zijn Nederlands, passend bij de bron-bankexport:

| Term | Betekenis |
|---|---|
| `afschrift` | bankafschrift / grootboekregel |
| `Rekening` | rekening |
| `Mutatiesoort` | transactie-/mutatiesoort (iDEAL, Incasso, …) |
| `Af_bij` | debet/credit ("Af" = geld uit, "Bij" = geld in) |
| `Saldo_na_mutatie` | saldo na deze mutatie |
| `afschrift_categorien` | uitgavencategorieën (Auto, Kleding, …) |

## Identiteit & rekeningen

Er is nergens een wachtwoord. "Inloggen" (`app/session.py`,
`app/routes/auth.py`) betekent kiezen welke bestaande `Users`-rij je bent
uit een lijst op `/login`, of een nieuwe aanmaken — het aanmaken van een
nieuwe gebruiker vereist een `Name` *en* een `Rekening` (IBAN) in één
stap, omdat een gebruiker niets kan uploaden zonder minstens één
gekoppelde rekening. Die keuze wordt opgeslagen in een ondertekende
(signed) sessiecookie (ondertekend zodat hij niet zomaar in de browser
aangepast kan worden, bijvoorbeeld om een ander user_id te worden — niet
omdat er een echt geheim achter zit; zie `app/config.py`). Dit is een
persoonlijke/lokale app, geen multi-tenant systeem met echte
beveiligingsgrenzen.

Een `Rekening.name` (de IBAN) is `UNIQUE` in de hele database — hij kan
systeembreed maar bij één gebruiker horen. Gebruikers kunnen meer dan één
rekening koppelen; dat gebeurt op de profielpagina
(`/user/{username}`, zie hieronder), via `POST /accounts`
(`app/routes/accounts.py`).

Een rekening kan ook weer verwijderd worden (`POST /accounts/{rekening_id}/delete`,
`app/routes/accounts.py::delete_account`) — er is geen manier om één
bankafschriftregel los te koppelen van haar rekening, dus dit is
alles-of-niets: de `Rekening`-rij zelf, én al haar `temp_afschrift`- én
(al gemigreerde) `afschrift`-rijen, verdwijnen in dezelfde transactie.
`Rekening_ID` heeft bewust geen `ON DELETE CASCADE` op geen van beide
tabellen (zie "Waarom SQL-first" hieronder — bedrijfsregels moeten
zichtbaar staan als eigen `.sql`-bestanden, niet impliciet in het schema
zitten), dus alle drie de deletes staan expliciet in
`app/routes/accounts.py::delete_account`, kind-vóór-ouder om de foreign
keys niet te breken (`sql/queries/temp_afschrift/delete_for_rekening.sql`,
`sql/queries/afschrift/delete_for_rekening.sql`, dan pas
`sql/queries/rekeningen/delete_rekening.sql`). Vóórdat de POST ooit
verstuurd wordt, toont de profielpagina precies hoeveel rijen dat raakt
(`sql/queries/rekeningen/count_data_for_user.sql`) in een
JavaScript-bevestiging (`app/static/js/user.js`) — dat is de enige rem;
er is geen ongedaan-maken.

Uitgavencategorieën (`afschrift_categorien`) en hun categoriseringsregels
(`afschrift_cat_regels`, zie "Fase 2" hieronder) zijn op dezelfde manier
per gebruiker: elke gebruiker bouwt en beheert zijn eigen lijst, ook op de
profielpagina, via `POST /categories/...` (`app/routes/categories.py`),
volledig los van wat andere gebruikers hebben. Een nieuwe gebruiker start
met een lege lijst; de 14 namen die vroeger de vaste globale set waren
(Auto, Wonen, Interne overboeking, …) staan nog wel klaar als eenmalig aan
te klikken suggesties, in de losstaande, niet-gebruikersgebonden tabel
`afschrift_categorie_suggesties` (gevuld door `sql/seed_data.sql`) — puur
een hulplijstje voor de UI, nooit gebruikt bij het categoriseren zelf.

### De profielpagina (`/user/{username}`)

Rekeningen-beheer en categorieën/keywords-beheer stonden ooit op twee
losse pagina's (`/accounts`, `/categories`); die zijn samengevoegd tot één
profielpagina op `/user/{username}` (`app/routes/user.py`,
`app/user_page.py::load_user_page_data`, template `user.html`). De
schrijfacties zelf zijn niet verhuisd — `POST /accounts` en
`POST /categories/...` blijven in hun eigen routebestanden, ze redirecten
alleen niet meer naar hun eigen GET-pagina maar naar de profielpagina
(`app/user_page.py::user_page_url`), en renderen bij een fout ook
`user.html` in plaats van een losstaand template.

`{username}` in het pad is **cosmetisch, geen autorisatiegrens**:
`Users.Name` heeft geen `UNIQUE`-constraint (dit is een persoonlijke, geen
multi-tenant, app — zie hierboven) en de pagina toont altijd de data van
de ingelogde sessie zelf, ongeacht wat er in het pad staat. Komt het pad
niet overeen met `request.session["user_name"]`, dan redirect de route
naar de eigen canonieke URL in plaats van iemands data onder een
misleidend pad te tonen. De naam wordt percent-encoded
(`user_page_url`/Jinja's `urlencode`-filter) zodat een vrij getypte naam
met spaties of andere tekens de URL niet breekt.

Een categorie toont haar regels op deze pagina alleen **read-only**
(kolom + keywords per regel, geen inline bewerkknoppen meer) — echt
aanpassen gebeurt op een eigen pagina, `/categories/regels/{regel_id}/edit`
(`app/routes/categories.py::edit_regel_page`/`save_regel`, template
`regel_edit.html`), bereikbaar via de "Aanpassen"-knop op elke regelkaart.
Die pagina toont alle negen kolommen tegelijk (niet alleen de kolommen
die de regel al heeft), vooringevuld met de huidige keywords/combine_mode
waar van toepassing, en slaat op als **volledige vervanging**: alle
kolom-voorwaarden van de regel worden verwijderd en opnieuw aangemaakt
uit wat er is ingediend, in één transactie
(`remove_regel_kolommen_for_regel.sql` gevolgd door dezelfde
insert-queries als het aanmaken van een nieuwe regel) — pas nadat de
inzending gevalideerd is, dus een mislukte validatie raakt de bestaande
regel niet aan. Zo kan een kolom worden toegevoegd, gewijzigd (inclusief
de EN/OF-modus) of helemaal leeggemaakt (= verwijderd uit de regel) door
gewoon de tekst in dat kolomveld aan te passen — hetzelfde
multi-keyword-per-veld-gedrag als bij het aanmaken van een nieuwe regel
(zie Fase 2 hieronder).

## Waarom SQL-first

Categorisering en het verplaatsen van data gebeurt met handgeschreven
SQL, niet met Python-logica, om twee redenen: het is efficiënter voor
bewerkingen op hele verzamelingen rijen bij mogelijk grote imports, en het
houdt de eigenlijke bedrijfsregels controleerbaar als bijgehouden
`.sql`-bestanden (zie `sql/README.md`), los van de Python-code eromheen.
`app/db.py` weet alleen hoe een verbinding te openen en een
`.sql`-bestand uit te voeren — het bouwt nooit een query als Python-string.

## De uploadpijplijn

```
geüpload bestand
     |
     v
temp_afschrift2   <- ruwe rijen, exact zoals de bank ze exporteerde
     |             (Rekening/Mutatiesoort nog platte tekst, nog geen FK's)
     | categorisering (SQL)
     v
temp_afschrift    <- FK's opgelost + een `processed`-status per rij
     |
     | status 0/2: handmatige controle in de UI
     | status 1:   klaar voor migratie
     v
afschrift         <- permanent grootboek, één strikt geordende reeks per rekening
```

### Fase 1 — ruwe upload (`temp_afschrift2`)

`app/upload.py` verwerkt het geüploade bestand (via een `BaseImporter`
uit `app/importers/` — één per bank/exportformaat, gekozen door de
gebruiker op `/upload`) en voegt de rijen rij voor rij toe, in de
volgorde die de importer teruggeeft. `Rekening` en `Mutatiesoort` blijven
platte tekst — er gebeurt nog geen FK-resolutie, dat is de taak van
categorisering (fase 2).

**De importer garandeert chronologische volgorde (oudste eerst), niet per
se de eigen bestandsvolgorde van de bron.** `BaseImporter.parse()` moet
altijd oudste-eerst teruggeven, ongeacht hoe de bank het exporteert —
alles hieronder (inclusief de saldoketen-controle) vertrouwt daarop.
ING NL's eigen export zet juist de **nieuwste transactie bovenaan** en de
oudste onderaan; `app/importers/ing_nl.py::parse()` draait de rijen dus
zelf om vóór het teruggeven. Dit was eerder verkeerd aangenomen (bestand
onveranderd doorgeven, top = oudste) — dat leidde ertoe dat een echte
ING-export altijd als "saldoketen doorbroken" werd afgewezen, omdat de
rijen dan in omgekeerde (nieuw-naar-oud) volgorde werden ingevoegd.

**Twee foreign keys worden vóór het invoegen gecontroleerd, niet erna.**
Beide zijn "hoort dit bestand hier wel thuis"-controles, geen
saldo-/dedup-continuïteitsproblemen, dus ze draaien vóórdat er ook maar
één rij wordt ingevoegd — faalt een van beide, dan wordt niets ingevoegd:

- **Rekening** moet al geregistreerd en gekoppeld zijn aan de uploadende
  gebruiker. In tegenstelling tot de categorie-match in categorisering
  (fase 2) wordt een onbekende of niet-jouw-rekening hier direct
  afgewezen, niet vastgehouden om later te koppelen — de gebruiker koppelt
  een rekening op `/accounts` *voordat* hij een afschrift daarvoor uploadt
  (`sql/queries/rekeningen/find_by_name.sql` herleidt de `Rekening`-tekst
  uit het bestand naar een `Rekening.ID` + bijbehorende `user_ID`; komt één
  van beide niet overeen → afgewezen).
- **Mutatiesoort** moet voor elke rij in het bestand al voorkomen in
  `mutatiesoort_mapping` (`sql/queries/mutatiesoorten/find_by_name.sql`).
  Dit is structurele referentiedata (zie `sql/seed_data.sql`) — een
  onbekende mutatiesoort betekent dat de mapping-tabel niet compleet is,
  niet dat deze rij handmatige controle nodig heeft, dus het hele bestand
  wordt afgewezen in plaats van dat de rij als `processed = 0` in
  categorisering terechtkomt.

**Rijvolgorde is dragend, niet cosmetisch.** `Saldo_na_mutatie` is een
lopend saldo, dus de positie van een rij in de reeks maakt deel uit van
haar betekenis. Ordening werkt over `afschrift`/`temp_afschrift`/
`temp_afschrift2` heen, ook al heeft elke tabel zijn eigen onafhankelijke
autoincrement-`ID`: `afschrift.ID` is de permanente, systeembreed
betekenisvolle volgorde voor een rekening (het is het append-only
grootboek — een rij verplaatst nooit meer zodra hij daar staat); de eigen
`ID`'s van de tijdelijke tabellen zijn alleen relevant *binnen* die tabel
— om rijen binnen één batch te ordenen, en om meerdere opgestapelde
batches in diezelfde tabel te ordenen. Omdat rijen altijd strikt stromen
via `afschrift ← temp_afschrift ← temp_afschrift2`, herstelt "tabel, dan
die tabel's eigen ID" een geldige globale volgorde zonder dat de drie
ID-kolommen onderling iets met elkaar te maken hoeven hebben. Dit steunt
op het feit dat categorisering altijd de *volledige* huidige achterstand van
`temp_afschrift2` voor een rekening in één atomaire run leegmaakt, nooit
een deel ervan — zie `sql/upload/check_balance_chain.sql`.

**Dit is altijd per rekening.** `temp_afschrift2.ID` is één gedeelde
teller over álle rekeningen heen — afschriften van rekening A en
rekening B kunnen daar fysiek gewoon tussen elkaar in staan (bijv. eerst
een upload voor A, dan een voor B, dan weer een voor A). Dat is geen
probleem: elke controle hieronder filtert eerst op `Rekening_ID`/
`Rekening` vóórdat er iets geordend wordt (`WHERE Rekening_ID = :rekening_id`
op elke tak van de UNION in zowel `check_balance_chain.sql` als
`check_dedup.sql`), dus rijen van een andere rekening komen de reeks
nooit binnen — hun eigen saldoketen wordt volledig onafhankelijk
gecontroleerd. Rekening A's volgorde moet intact blijven; wat er
tussendoor met rekening B gebeurt (mag, zolang B's eigen keten maar
klopt) doet er niet toe.

**Per rekening lopen daarna nog twee continuïteitscontroles, ná het
invoegen van de nieuwe batch maar binnen dezelfde transactie**
(`sql/upload/`, uitgevoerd door `app/upload.py`) — beide slagen en de
transactie wordt gecommit, of één van beide faalt en de hele batch wordt
teruggedraaid (alles-of-niets, hetzelfde principe als migratie, alleen één
fase eerder toegepast). Dit zijn wél post-insert controles, in
tegenstelling tot de twee hierboven — ze hebben de net ingevoegde rijen
nodig om tegen de bestaande geschiedenis van de rekening te kunnen
vergelijken:

- **`check_balance_chain.sql`** — doorloopt de volledige reeks van de
  rekening (bevestigd `afschrift` + wachtend `temp_afschrift` + de nieuwe
  batch, geordend zoals hierboven) en controleert of het
  `Saldo_na_mutatie` van elke rij logisch volgt uit de vorige rij,
  aangepast met `Bedrag_eur`/`Af_bij`. Eén query vangt zowel een "sluit
  niet aan op bekende geschiedenis"-grensprobleem als een "intern
  inconsistent binnen het bestand zelf"-probleem — het zijn dezelfde
  controle, toegepast over een langere reeks, geen twee losse regels. Dit
  vangt ook de meeste exacte herimports van een al geïmporteerd bestand
  op, omdat het opnieuw toepassen van een transactie die al gebeurd is de
  keten doorbreekt.
- **`check_dedup.sql`** — signaleert expliciet dubbele rijen (op
  `Datum + Bedrag_eur + Saldo_na_mutatie + Naam`) over dezelfde drie
  bronnen, met een precieze melding "deze rij is al eerder geïmporteerd"
  in plaats van te vertrouwen op de ketencontrole die dit (meestal) ook
  toevallig opvangt. Vergelijkt de ruwe `Datum` (`YYYYMMDD`) van
  `temp_afschrift2` met de `YYYY-MM-DD` van de andere twee tabellen door
  deze inline te normaliseren — zie "Datums" hieronder.

Eén geüpload bestand kan in principe naar meer dan één rekening
verwijzen; de batch van elke rekening is zijn eigen onafhankelijke
transactie.

**Zodra een batch gecommit is, wordt de rekening's volledige
`temp_afschrift2`-achterstand meteen gecategoriseerd** (`app/upload.py`
roept `app/categorization.py` aan) — dat is fase 2, hieronder. Dit gebeurt
als een eigen atomaire stap op een eigen connectie: gaat dit onverwacht
mis, dan blijven de al gecommitte rijen gewoon in `temp_afschrift2` staan
voor een volgende poging, de upload zelf is niet aangetast. In de praktijk
zou categorisering hier niet moeten falen — `Rekening`/`Mutatiesoort` zijn
al gegarandeerd herleidbaar door de twee pre-insert-controles hierboven,
en elke rij krijgt hoe dan ook gewoon `processed` 0, 1 of 2.

### Datums

Drie verschillende datumnotaties, met opzet:

| Waar | Formaat | Waarom |
|---|---|---|
| `temp_afschrift2.Datum` | ruwe `YYYYMMDD` (8 tekens) | exact wat de ING-export bevat — de importer herformatteert dit niet |
| `temp_afschrift`/`afschrift.Datum` | `YYYY-MM-DD` (10 tekens, ISO) | sorteert correct als platte tekst en werkt met SQLite's `date()`/`strftime()` — nodig omdat het grootboek op datum gesorteerd/gefilterd wordt |
| UI-weergave | `DD-MM-YYYY` (Europees) | wat je daadwerkelijk op het scherm leest |

`DD-MM-YYYY` is niet lexicografisch sorteerbaar ("15-03-2026" komt als
platte tekst vóór "20-01-2026", ook al komt maart na januari), dus het is
puur een presentatieformaat, toegepast bij het renderen van een template
— nooit opgeslagen. Categorisering (fase 2) zet de ruwe `YYYYMMDD` om naar
ISO bij het kopiëren van een rij van `temp_afschrift2` naar
`temp_afschrift`.

### Fase 2 — categorisering (`temp_afschrift2` → `temp_afschrift`)

SQL herleidt de foreign keys van elke rij:

- `Rekening` (tekst) → `Rekening.name` → `Rekening_ID` — al gevalideerd bij
  upload (fase 1: de rekening moet geregistreerd en aan de gebruiker
  gekoppeld zijn), dus hier altijd herleidbaar.
- `Mutatiesoort` (tekst) → `mutatiesoort_mapping.Name` → `mutatiesoort_ID` —
  structurele referentiedata; wordt verondersteld altijd te matchen.

Beide gebeuren onafhankelijk van `processed` — dat gaat uitsluitend over de
categorie-match, via het **regel-systeem** hieronder, gescopet op de
`user_ID` van de categoriserende gebruiker (categorieën en regels zijn
per gebruiker, zie "Identiteit & rekeningen" hierboven).

#### Het regel-systeem

Een categorie matcht een rij zodra minstens één van haar **regels**
(`afschrift_cat_regels`) matcht (OF over de regels van een categorie). Een
regel is zelf een set voorwaarden over kolommen — `Naam`, `Tegenrekening`,
`Code`, `Af_bij`, `Bedrag_eur`, `Mutatiesoort`, `Mededeling`,
`Saldo_na_mutatie`, `Tag` (`afschrift_cat_regel_kolommen`, één rij per
kolom die de regel controleert). Een kolom die een regel niet heeft wordt
simpelweg niet gecontroleerd ("geen waarde = geen check"). Alle kolommen
die een regel wél heeft moeten matchen wil de regel zelf matchen (EN over
de kolommen van een regel).

Elke kolom-voorwaarde heeft één of meer keywords/waarden
(`afschrift_cat_regel_keywords`) plus een eigen `combine_mode`: `'OR'`
matcht als één van de keywords voorkomt, `'AND'` vereist dat ze allemaal
tegelijk voorkomen. Bijv. categorie "Inkomsten" met één regel — Naam
"Baan", Af/Bij "Bij", Mutatiesoort "Mutatieoverschrijving", Mededeling
"Salaris" — matcht alleen als alle vier tegelijk kloppen.

Matching hangt af van het kolomtype:

- **Naam, Tegenrekening, Mededeling, Tag, Mutatiesoort** — substring
  (`LIKE`), zelfde idee als de oude "simpele"/"moeilijke" keywords.
- **Code, Af_bij** — exacte tekstmatch. Af_bij wordt op app-niveau
  beperkt tot precies `'Af'`/`'Bij'` (`app/categorization_rules.py`).
- **Bedrag_eur, Saldo_na_mutatie** — exacte match als GETAL (`CAST(...
  AS REAL)`), niet als tekst — `'25'` en `'25.00'` zijn dezelfde waarde.
  Invoer is Nederlands genoteerd (`'.'` duizendtallen, `','` decimalen,
  bijv. `'1.234,56'`) en wordt vóór opslag omgezet naar deze canonieke
  vorm.

Er waren ooit drie losse signalen — "simpel" (Naam-substrings),
"moeilijk" (Mededeling-substrings, optioneel gekoppeld aan een
Naam-substring) en "Interne overboeking" (Tegenrekening die zelf een
`Rekening` van dezelfde gebruiker is, automatisch herkend, geen keyword).
Alle drie zijn nu uit te drukken als regels onder het ene algemene
mechanisme hierboven: een Naam-only regel, een Mededeling+Naam-regel
(twee kolommen, allebei verplicht — de EN-over-kolommen default), en een
Tegenrekening-regel met je eigen rekeningnummer(s) als keywords. Er is
geen aparte interne-overboeking-detectie meer — het is nu gewoon een
normale, door de gebruiker beheerde regel, die zich dus ook niet meer
automatisch aanpast zodra je een nieuwe rekening koppelt; voeg het IBAN
dan zelf toe als extra Tegenrekening-keyword.

`processed`:

| Waarde | Betekenis |
|---|---|
| `0` | Geen enkele regel kwam overeen. Vereist handmatige categorie-keuze. |
| `1` | Precies één categorie kwam overeen (via één of meer van haar regels). Klaar voor migratie. |
| `2` | Ambigu — meer dan één categorie kwam overeen. Vereist een handmatige keuze daartussen. |

Draait automatisch, meteen na een geaccepteerde upload (zie fase 1) — er
is geen aparte trigger of UI-stap voor. Zie `sql/categorization/README.md`
voor de SQL-bestanden en `app/categorization.py` voor de orchestratie, en
`app/categorization_rules.py` voor de validatie/normalisatie van een
regel's ingevoerde waarden vóór opslag.

**Opnieuw proberen zonder her-upload.** Voeg je een categorie/regel toe
*nadat* een bestand al is geüpload, dan blijft de destijds bepaalde
uitkomst gewoon in `temp_afschrift` staan — ook een inmiddels
achterhaalde `processed = 1` — tot iemand er iets aan doet. De knop
"Categorisatie opnieuw proberen" op `/review`
(`app/categorization.py::recategorize_pending`,
`sql/categorization/recategorize_temp_afschrift.sql`) evalueert dezelfde
regel-logica hierboven opnieuw, maar dan tegen `temp_afschrift` in plaats
van `temp_afschrift2`, over *alle* rekeningen en *alle* rijen van de
gebruiker tegelijk — inclusief al opgeloste rijen, niet alleen
`processed` 0/2.

Dat laatste is met opzet asymmetrisch: `processed = 1` betekent
"opgelost", zonder onderscheid tussen automatisch en handmatig gekozen
(zie `sql/queries/temp_afschrift/set_category.sql`) — er is geen apart
veld dat een handmatige keuze markeert. Een opgeloste rij wordt daarom
hier alleen ooit **gepromoveerd** naar ambigu (`processed = 2`), namelijk
zodra een nieuw toegevoegde regel er nu óók mee overeenkomt — dat conflict
moet zichtbaar worden, niet stilzwijgend onder de mat geveegd. Diezelfde
rij wordt nooit terugverlaagd naar onopgelost puur omdat er nu geen
enkele regel meer op matcht (de normale situatie voor iets dat met de
hand is gekozen) en de gekoppelde categorie wordt nooit stilzwijgend
verwisseld voor een andere, toevallig unieke match. Rijen die al
`processed` 0 of 2 waren mogen wel vrij naar elke nieuwe uitkomst bewegen.
Eén subtiliteit: `temp_afschrift` bewaart alleen `Mutatiesoort_ID`, niet
de originele ruwe tekst uit het bestand, dus een `Mutatiesoort`-voorwaarde
wordt hier gecontroleerd tegen elk ruw label in `mutatiesoort_mapping` dat
naar diezelfde ID herleidt — inhoudelijk gelijkwaardig, omdat die mapping
synonieme labels toch al tot één mutatiesoort samenvoegt.

### Fase 3 — handmatige controle

Rijen met `processed = 0` of `2` blijven in `temp_afschrift` staan totdat
de gebruiker ze handmatig oplost door een categorie te kiezen — dat werkt
voor beide gevallen identiek, er is geen apart mechanisme voor ambigue
rijen (zie hieronder). Eenmaal opgelost, worden ze opnieuw gemarkeerd als
`processed = 1`.

`/review` (`app/routes/review.py`, `sql/queries/temp_afschrift/
list_all_for_user.sql`) toont **alle** `temp_afschrift`-rijen van de
ingelogde gebruiker — niet alleen onopgelost/ambigu, ook al opgeloste
rijen — gegroepeerd in één tabel per Rekening (op naam, niet op ID), elk
met een eigen opgelost/onopgelost/ambigu-telling, plus een totaaltelling
bovenaan de pagina. Een statusfilter (checkboxes onopgelost/opgelost/
ambigu, `?status=&filtered=1`, zelfde "verborgen `filtered`-marker"-truc
als het dashboard) bepaalt alleen welke rijen **getoond** worden per
tabel (`group.display_rows`) — de telling, de "is deze rekening
klaar?"-check en dus migratie-geschiktheid gebruiken altijd de volledige,
ongefilterde rijenset van die rekening, nooit de gefilterde weergave. Zo
kan een rekening nooit per ongeluk "klaar" lijken (of dat verbergen)
puur omdat de onopgeloste/ambigue rijen toevallig uit beeld gefilterd
zijn.

Categorie toewijzen kan al vanaf dit scherm: elke rij heeft een dropdown
met alle bestaande categorieën plus een "+ nieuwe categorie…"-optie, maar
er is één opslaan-knop **per rekeningtabel**, niet per rij
(`POST /review/{rekening_id}/save`,
`sql/queries/temp_afschrift/set_category.sql`) — alle dropdown-keuzes in
die tabel worden in één keer verwerkt. Kiezen (of een nieuwe naam
intypen) zet `Afschrift_cat_ID` en markeert de rij meteen als
`processed = 1` — een mens heeft de knoop doorgehakt, ongeacht of de rij
daarvoor onopgelost, ambigu, of al ergens anders op stond. Een nieuwe
naam die (case-insensitive) al bestaat wordt hergebruikt in plaats van
een bijna-duplicaat aan te maken (`sql/queries/categorieen/
find_by_name.sql`). Zowel de rekening zelf
(`sql/queries/rekeningen/find_by_id_for_user.sql`) als elke individuele
rij-update zijn gescopet op de ingelogde gebruiker — geen route hoeft dit
los te verifiëren.

Na het opslaan wordt meteen dezelfde "is deze rekening klaar?"-check
uitgevoerd die migratie nodig heeft: zijn álle rijen van die rekening nu
`processed = 1`? Zo ja, toont de pagina naast de tabel een "Migreren naar
afschrift"-knop (`POST /review/{rekening_id}/migrate`, zie Fase 4
hieronder). Zo nee, blijft de tabel gewoon staan voor verdere correctie.
Een ambigue rij (`processed = 2`) wordt op precies dezelfde manier
opgelost als een onopgeloste: dezelfde dropdown, dezelfde
opslaan-knop — één categorie kiezen hakt de knoop meteen door, dus er is
geen apart "kies tussen deze matches"-scherm nodig. Een rekening
"corrigeren" (een rij naar een andere `Rekening_ID` verplaatsen, of een
gekoppeld IBAN achteraf wijzigen) is niet gebouwd en ook niet gepland —
in plaats daarvan kan een hele rekening verwijderd worden (zie
"Identiteit & rekeningen" hierboven) en zo nodig met het juiste IBAN
opnieuw gekoppeld worden.

### Fase 4 — migratie (`temp_afschrift` → `afschrift`)

Migratie is **alles-of-niets per rekening**: `app/migration.py::migrate_account`
draait alleen voor een bepaalde `Rekening_ID` zodra *elke* wachtende rij
voor die rekening — inclusief rijen uit eerdere uploads die onopgelost
bleven — `processed = 1` is (`sql/migration/count_unresolved.sql`). Dit
volgt direct uit het feit dat rijvolgorde dragend is: een onopgeloste rij
overslaan en later, buiten de volgorde, invoegen zou de saldoketen van
elke rij daarna corrumperen. Andere rekeningen worden hierdoor niet
beïnvloed — één rommelige rekening blokkeert de migratie van een schone
rekening niet.

Voldoet de rekening niet, dan wordt niets aangepast: `migrate_account`
gooit `NotFullyResolvedError` en `POST /review/{rekening_id}/migrate`
rendert `/review` opnieuw met een foutmelding (400). Voldoet de rekening
wel, dan draait in één transactie: rijen worden in strikte oorspronkelijke
volgorde ingevoegd in `afschrift` (`sql/migration/insert_into_afschrift.sql`,
`ORDER BY temp_afschrift.ID`), en daarna verwijderd uit `temp_afschrift`
(`sql/migration/delete_from_temp_afschrift.sql`) — zelfde
insert-dan-delete-in-één-transactie-vorm als Fase 2's
`categorize_batch.sql` + `clear_temp_afschrift2.sql`. Zowel de guard als
de insert/delete zijn gescopet op `user_ID` (via `Rekening`), net als
`set_category.sql` — een geraden `rekening_id` van een andere gebruiker
raakt nooit rijen aan.

De route zelf (`app/routes/review.py::migrate_to_afschrift`) verifieert
eerst dat `rekening_id` van de ingelogde gebruiker is
(`sql/queries/rekeningen/find_by_id_for_user.sql`), en vertrouwt daarna
niet op wat de pagina op dat moment toont — de "is deze rekening
klaar?"-conditie wordt in de database zelf herbevestigd door
`migrate_account`, niet aangenomen vanuit de eerder gerenderde pagina.

### Fase 5 — het grootboek (`afschrift`) en het dashboard

Het permanente, volledig opgeloste overzicht. Het dashboard (`/`,
`app/routes/dashboard.py`) is de eerste viewer erop: een filterbaar
rapport, niet meer de vroegere plek voor Rekeningen/categorieën-beheer
(dat is verhuisd naar de profielpagina, zie hierboven). Leest uitsluitend
`afschrift`, nooit `temp_afschrift` — nog niet gemigreerde rijen tellen
niet mee in de cijfers.

Filterbaar op hele kalendermaanden (`?start_month=...&end_month=...`,
"YYYY-MM" — nooit losse datums, zie `app/dashboard_chart.py`'s
`parse_month`/`month_range`), met de laatste 6 maanden als standaard
wanneer geen (of een ongeldige) periode is opgegeven — één maand als
standaard zou de lijngrafiek een enkel punt geven. Snelkeuzes: deze
maand, laatste 6 maanden, dit jaar, en "alles" (van/tot de eerste/laatste
maand met daadwerkelijk data voor deze gebruiker,
`sql/queries/afschrift/date_bounds_for_user.sql` — geen arbitraire
epoch-range meer, dat werkte niet meer met een `<input type="month">`).

Daarnaast kan de gebruiker precies kiezen welke Rekeningen en categorieën
meetellen voor Inkomsten/Uitgaven/Verschil (checkboxes, alles aangevinkt
als standaard bij een verse paginalading; een expliciet lege selectie na
filteren toont terecht nul). Een verborgen `filtered=1`-veld in het
formulier onderscheidt "net gefilterd, dus vertrouw exact wat is
aangevinkt" van "eerste paginalading, dus alles selecteren" — zonder dat
veld zou een bewust leeggemaakte selectie niet te onderscheiden zijn van
"nog geen filter gekozen". Rekening-/categorieselectie gebeurt in
Python, niet in SQL: één query
(`sql/queries/afschrift/monthly_totals_for_user.sql`) haalt sommen per
maand, per Rekening, per categorie op voor de hele periode (een kleine,
vaste resultaatset), en `app/routes/dashboard.py` filtert/sommeert die
rijen op basis van de aangevinkte ID's — bewust geen dynamische
SQL IN-lijst met een wisselend aantal placeholders (zie
sql/queries/README.md).

De lijngrafiek (server-gerenderde inline SVG, `app/dashboard_chart.py`)
toont per geselecteerde maand één punt, voor elke aangevinkte lijn:
Inkomsten/Uitgaven/Verschil totaal, en/of één lijn per — nog altijd
meetellende — categorie (netto bij−af per maand, dezelfde eenheid als
Verschil). Kleur én stippellijnstijl van een lijn zijn afgeleid van haar
eigen identiteit (vaste rol voor de drie totalen, `cat_id % n` voor een
categorie), nooit van haar positie in de huidige selectie — een categorie
aan/uitvinken laat andere lijnen dus nooit van kleur wisselen. Palet is
de gevalideerde categorische reeks uit de dataviz-skill (zie de
`--series-*`-variabelen in `style.css`, met eigen licht/donker-paren zoals
de rest van de theming). Hover toont een crosshair + tooltip met alle
zichtbare lijnen op die maand (`app/static/js/dashboard.js`); de
onderliggende cijfers staan ook gewoon in de categorietabel eronder.

## Logging

Twee gescheiden logs (`app/logging_config.py`), beide roterend en
gitignored:

- **`logs/app.log`** — technisch/runtime: opstarten, HTTP-requests,
  exceptions. Wordt tijdens development ook naar de console geschreven.
- **`logs/audit.log`** — een blijvend overzicht van datawijzigende
  events (ontvangen uploads, rijen afgewezen door dedup/continuïteit,
  categoriseringsresultaten, uitgevoerde migraties — welke rijen, welke
  rekening, wanneer). Bewust gescheiden van `app.log`: dit is bedoeld om
  te antwoorden op "wat is er met mijn data gebeurd en wanneer", niet om
  de server te debuggen.

## Portabiliteit

Het project is bedoeld om gekloond en gedraaid te worden op een andere
machine, of volledig aan iemand anders overgedragen te worden, zonder
aanpassingen:

- Alle paden worden relatief aan de code opgelost (`app/config.py`), nooit
  hardcoded absolute paden.
- De database wordt bij de eerste run gegenereerd uit `sql/schema.sql` +
  `sql/seed_data.sql` — nooit gecommit (zie `.gitignore`).
- `sql/seed_data.sql` bevat alleen structurele referentiedata die elke
  installatie nodig heeft: de mutatiesoort-vocabulaire van de bank, en de
  globale, niet-gebruikersgebonden lijst met categorie-suggesties
  (`afschrift_categorie_suggesties`). Echte categorieën en hun keywords
  (bijv. "Esso" → Auto) zijn persoonlijk per gebruiker en worden opgebouwd
  via de profielpagina (`/user/{username}`, `app/routes/categories.py`),
  niet via seed-data.
