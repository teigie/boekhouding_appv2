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

Uitgavencategorieën (`afschrift_categorien`) en hun keywords
(`afschrift_cat_keywords`/`afschrift_cat_mededeling_keywords`) zijn op
dezelfde manier per gebruiker: elke gebruiker bouwt en beheert zijn eigen
lijst, ook op de profielpagina, via `POST /categories/...`
(`app/routes/categories.py`), volledig los van wat andere gebruikers
hebben. Een nieuwe gebruiker start met een lege lijst; de 14 namen die
vroeger de vaste globale set waren (Auto, Wonen, Interne overboeking, …)
staan nog wel klaar als eenmalig aan te klikken suggesties, in de
losstaande, niet-gebruikersgebonden tabel `afschrift_categorie_suggesties`
(gevuld door `sql/seed_data.sql`) — puur een hulplijstje voor de UI, nooit
gebruikt bij het categoriseren zelf.

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
gebruiker op `/upload`) en voegt het rij voor rij, onveranderd, toe in
exact de volgorde waarin het in het bestand staat. `Rekening` en
`Mutatiesoort` blijven platte tekst — er gebeurt nog geen FK-resolutie,
dat is de taak van categorisering (fase 2).

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
categorie-match, uit drie onafhankelijke signalen, elk gescopet op de
`user_ID` van de categoriserende gebruiker (categorieën en keywords zijn
per gebruiker, zie "Identiteit & rekeningen" hierboven):

- **Simpele categorisering** — `Naam` (de tegenpartij-/bedrijfsnaam)
  doorzocht op elke `afschrift_cat_keywords.keyword`-substring van de
  gebruiker zelf (bijv. "Lidl" → Levensmiddelen).
- **Moeilijke categorisering** — `Mededeling` (de vrije-tekst
  transactieomschrijving) doorzocht op elke
  `afschrift_cat_mededeling_keywords.keyword`-substring/frase van de
  gebruiker zelf, voor gevallen waar `Naam` alleen niet genoeg zegt. Elke
  rij kan optioneel gekoppeld worden aan een `naam_keyword` dat dan ook in
  `Naam` moet voorkomen wil de rij matchen (bijv. Mededeling
  "Vakantiegeld" gekoppeld aan Naam "vakantie" — samen precies genoeg,
  terwijl geen van beide op zichzelf dat zou zijn). Zonder koppeling
  (`NULL`) is Mededeling alleen voldoende, zoals voorheen.
- **Interne overboeking** — structureel anders dan de andere twee, geen
  keyword-match: `Tegenrekening` die zelf een `Rekening` is die aan
  dezelfde gebruiker gekoppeld is, wordt automatisch de categorie "Interne
  overboeking" (`sql/categorization/match_internal_transfer.sql`). Steunt
  op het bestaan van precies die categorienaam *voor die gebruiker* — er
  is geen apart schemaveld dat een categorie als "de interne-
  overboeking-categorie" markeert. Een nieuwe gebruiker heeft die
  categorie nog niet (iedereen start leeg), dus dit signaal matcht simpelweg
  niets totdat de gebruiker hem zelf toevoegt (staat klaar als suggestie
  op de profielpagina, `/user/{username}`).

Huidige strategie (nog niet definitief, kan nog wijzigen): alle drie
signalen worden voor elke rij altijd gecontroleerd, en de gematchte
categorieën uit alle bronnen worden samengevoegd tot één verzameling per
rij:

| Waarde | Betekenis |
|---|---|
| `0` | Geen van de drie signalen kwam overeen. Vereist handmatige categorie-keuze. |
| `1` | Precies één categorie kwam overeen. Klaar voor migratie. |
| `2` | Ambigu — meer dan één categorie kwam overeen. Vereist een handmatige keuze daartussen. |

Draait automatisch, meteen na een geaccepteerde upload (zie fase 1) — er
is geen aparte trigger of UI-stap voor. Zie `sql/categorization/README.md`
voor de SQL-bestanden en `app/categorization.py` voor de orchestratie.

### Fase 3 — handmatige controle

Rijen met `processed = 0` of `2` blijven in `temp_afschrift` staan totdat
de gebruiker ze handmatig oplost (een categorie toewijzen, een rekening
corrigeren, kiezen tussen ambigue matches). Eenmaal opgelost, worden ze
opnieuw gemarkeerd als `processed = 1`.

`/review` (`app/routes/review.py`, `sql/queries/temp_afschrift/
list_all_for_user.sql`) toont **alle** `temp_afschrift`-rijen van de
ingelogde gebruiker — niet alleen onopgelost/ambigu, ook al opgeloste
rijen — gegroepeerd in één tabel per Rekening (op naam, niet op ID), elk
met een eigen opgelost/onopgelost/ambigu-telling, plus een totaaltelling
bovenaan de pagina.

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
Rekening corrigeren en kiezen tussen ambigue matches zijn nog niet
gebouwd.

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

Filterbaar op periode (`?start=...&end=...`, ISO-datums), met de huidige
kalendermaand als standaard wanneer geen (of een ongeldige) periode is
opgegeven, plus een paar snelkeuzes (deze/vorige maand, dit jaar, alles —
"alles" is intern gewoon een zeer brede datumrange, geen aparte
NULL-behandeling). Één query
(`sql/queries/afschrift/totals_per_category_for_user.sql`) sommeert
inkomsten (`Af_bij = 'Bij'`) en uitgaven (`Af_bij = 'Af'`) per categorie
voor de opgegeven periode, gescopet op de rekeningen van de ingelogde
gebruiker; de paginatotalen (inkomsten/uitgaven/verschil bovenaan) zijn
simpelweg de som van diezelfde rijen in Python — geen aparte totaalquery.
Filteren op rekening, of aggregeren per rekening/langere periode dan een
jaar, is nog niet gebouwd.

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
