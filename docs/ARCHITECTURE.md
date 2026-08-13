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
rekening koppelen op `/accounts` (`app/routes/accounts.py`); een rekening
kan maar bij één gebruiker horen.

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
     | verrijking (SQL)
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
dat is de taak van verrijking (fase 2).

**De rekening moet al geregistreerd en gekoppeld zijn aan de uploadende
gebruiker.** In tegenstelling tot categorisering (fase 2) wordt een
onbekende of niet-jouw-rekening hier direct afgewezen, niet vastgehouden
om later te koppelen — de gebruiker koppelt een rekening op `/accounts`
*voordat* hij een afschrift daarvoor uploadt
(`sql/queries/rekeningen/find_by_name.sql` herleidt de `Rekening`-tekst
uit het bestand naar een `Rekening.ID` + bijbehorende `user_ID`; komt één
van beide niet overeen → afgewezen, niets wordt ingevoegd).

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
op het feit dat verrijking altijd de *volledige* huidige achterstand van
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

**Per rekening lopen twee controles, ná het invoegen van de nieuwe batch
maar binnen dezelfde transactie** (`sql/upload/`, uitgevoerd door
`app/upload.py`) — beide slagen en de transactie wordt gecommit, of één
van beide faalt en de hele batch wordt teruggedraaid (alles-of-niets,
hetzelfde principe als migratie, alleen één fase eerder toegepast):

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
— nooit opgeslagen. Verrijking (fase 2) zet de ruwe `YYYYMMDD` om naar
ISO bij het kopiëren van een rij van `temp_afschrift2` naar
`temp_afschrift`.

### Fase 2 — verrijking (`temp_afschrift2` → `temp_afschrift`)

SQL herleidt de foreign keys van elke rij en kent een `processed`-status
toe:

- `Rekening` (tekst) → `Rekening.name` → `Rekening_ID`
- `Mutatiesoort` (tekst) → `mutatiesoort_mapping.Name` → `mutatiesoort_ID`
- `Naam`/`Mededeling` doorzocht op elke `afschrift_cat_keywords.keyword`-
  substring → `Afschrift_cat_ID`

`processed`-waarden:

| Waarde | Betekenis |
|---|---|
| `0` | Onopgelost — er ontbreekt iets (rekening, mutatiesoort, of geen enkel keyword kwam overeen). Vereist handmatige invoer. |
| `1` | Netjes opgelost — precies één categorie-match (of geen nodig) en alle FK's bekend. Klaar voor migratie. |
| `2` | Ambigu — meer dan één categorie-keyword kwam overeen. Vereist een handmatige keuze daartussen, anders dan "niets kwam overeen". |

*(Nog niet geïmplementeerd — zie `sql/enrichment/README.md`.)*

### Fase 3 — handmatige controle

Rijen met `processed = 0` of `2` blijven in `temp_afschrift` staan totdat
de gebruiker ze handmatig oplost in de UI (een categorie toewijzen, een
rekening corrigeren, kiezen tussen ambigue matches). Eenmaal opgelost,
worden ze opnieuw gemarkeerd als `processed = 1`.

### Fase 4 — migratie (`temp_afschrift` → `afschrift`)

Migratie is **alles-of-niets per rekening**: het draait alleen voor een
bepaalde `Rekening_ID` zodra *elke* wachtende rij voor die rekening —
inclusief rijen uit eerdere uploads die onopgelost bleven — `processed = 1`
is. Dit volgt direct uit het feit dat rijvolgorde dragend is: een
onopgeloste rij overslaan en later, buiten de volgorde, invoegen zou de
saldoketen van elke rij daarna corrumperen. Andere rekeningen worden
hierdoor niet beïnvloed — één rommelige rekening blokkeert de migratie
van een schone rekening niet.

Wanneer het draait: rijen worden in strikte oorspronkelijke volgorde
ingevoegd in `afschrift`, en daarna verwijderd uit `temp_afschrift`.

*(Nog niet geïmplementeerd — zie `sql/migration/README.md`.)*

### Fase 5 — het grootboek (`afschrift`)

Het permanente, volledig opgeloste overzicht. Gebruikt om uitgaven te
bekijken, sorteren, filteren en (later) te aggregeren per categorie/
rekening/periode.

## Logging

Twee gescheiden logs (`app/logging_config.py`), beide roterend en
gitignored:

- **`logs/app.log`** — technisch/runtime: opstarten, HTTP-requests,
  exceptions. Wordt tijdens development ook naar de console geschreven.
- **`logs/audit.log`** — een blijvend overzicht van datawijzigende
  events (ontvangen uploads, rijen afgewezen door dedup/continuïteit,
  verrijkingsresultaten, uitgevoerde migraties — welke rijen, welke
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
  installatie nodig heeft (categorieën, de mutatiesoort-vocabulaire van
  de bank). Persoonlijke categorie-keywords (bijv. "Esso" → Auto) staan
  los in `sql/optional/example_keywords.sql`, duidelijk gemarkeerd als
  het voorbeeld van één persoon in plaats van iets waar een verse
  installatie aan vastzit — zie dat bestand en
  `sql/queries/reference_data/` om je eigen lijst op te bouwen.
