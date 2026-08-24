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

## [0.0.55] - 2026-08-24 — Levensmiddelen-omschrijving + nieuwe suggestie "Geld opnemen"

- **Nieuw**: onboarding-suggesties (`app/category_suggestions.py`)
  krijgen nu ook een optionele `description` per categorie — alleen
  "Levensmiddelen" heeft er voorlopig één: "Dagelijkse boodschappen,
  verzorgingsproducten bij drogist en schoonmaakmiddelen dagelijks
  gebruik." `app/routes/onboarding.py` geeft die description nu door
  bij het aanmaken (`cat.get("description")` in plaats van altijd
  `None`) — een gebruiker die deze suggestie vanaf nu accepteert krijgt
  hem er meteen bij.
- **Nieuw**: "Geld opnemen" toegevoegd aan de Uitgaven-suggesties, naast
  Bankkosten.
- **Correctie in de bestaande database**: elke al bestaande categorie
  "Levensmiddelen" (TestUser, TestReinald, test3 — alle drie hadden hem
  al, via eerdere onboarding-acceptatie of handmatig aangemaakt) heeft
  nu retroactief dezelfde omschrijving gekregen, via de bestaande route
  `POST /categories/{id}/description` (geen nieuw script — gewoon de
  route die de UI ook gebruikt). "Geld opnemen" is daarnaast ook
  meteen als echte categorie (Uitgaven) aangemaakt voor test3, via
  `POST /categories`.
- **Geverifieerd** op de live app (aparte poort, DB vooraf
  gebackupt): alle drie de Levensmiddelen-rijen dragen nu de
  omschrijving, test3 heeft "Geld opnemen" (Uitgaven, ID 81), profiel-
  pagina van test3 rendert beide correct (ToC-omschrijving, regels-
  sectie-textarea, nieuwe categoriekaart). Geen tracebacks.

## [0.0.54] - 2026-08-24 — Onboarding-suggesties: "Netflix" hernoemd naar "Streamingdienst"

- **Correctie**: de subcategorie "Netflix" onder "Abonnementen" in
  `app/category_suggestions.py` heette per ongeluk naar één specifieke
  dienst — hernoemd naar het generieke "Streamingdienst".

## [0.0.53] - 2026-08-24 — Onboarding: voorgestelde categorieën direct na het aanmaken van een nieuwe gebruiker

- **Nieuw**: een nieuwe gebruiker (`POST /login/new`, `app/routes/auth.py`)
  komt niet meer meteen op het (dan nog helemaal lege) dashboard uit,
  maar eerst op `/onboarding/suggesties` — een nieuwe pagina
  (`app/routes/onboarding.py`, `app/templates/onboarding_suggesties.html`)
  die een curated standaardset categorieën en subcategorieën toont,
  gesplitst in Inkomsten/Uitgaven (zelfde kleuren/kolom-indeling als
  elders in de app). Eén simpele keuze: "Ja, deze toevoegen" zet ze
  allemaal voor de gebruiker klaar; "Nee, overslaan" voegt niets toe —
  in beide gevallen ga je daarna gewoon naar het dashboard, zoals
  voorheen altijd al gebeurde.
- De voorgestelde lijst zelf staat vast in `app/category_suggestions.py`
  (Python-data, geen databasetabel — vergelijkbaar met maar los van de
  bestaande, platte `afschrift_categorie_suggesties`-tabel achter de
  losse suggestie-chips op /categories, die geen hiërarchie of Type
  kent). "Levensmiddelen" stond twee keer in de oorspronkelijke lijst
  (waarschijnlijk een kopieerfoutje) — hier maar één keer opgenomen.
- Deze pagina is niet exclusief voor het moment van aanmaken: elke
  ingelogde gebruiker kan hem via de URL opnieuw bezoeken (geen link in
  de navigatie) om ontbrekende voorgestelde (sub)categorieën alsnog toe
  te voegen. Een categorienaam die al bestaat wordt bij "Ja" gewoon
  overgeslagen (geen foutmelding, geen dubbele rij) — de bijbehorende
  subcategorieën van een overgeslagen categorie worden dan ook niet
  aangemaakt.
- **Geverifieerd** op de live app (aparte poort, echte tijdelijke
  testgebruikers, live database met vooraf backup): signup redirect
  naar de nieuwe pagina, pagina toont alle 22 categorieën met hun
  subcategorieën correct (incl. de Levensmiddelen-dedup), "Ja" zet ze
  allemaal met het juiste Type en de juiste subcategorie-koppeling in
  de database, nogmaals "Ja" klikken op dezelfde (nu gevulde) gebruiker
  crasht niet en voegt niets dubbel toe, "Nee" voegt niets toe. Test-
  gebruikers en hun rijen daarna weer volledig verwijderd, geen
  `foreign_key_check`-schendingen achtergebleven, bestaande gebruikers
  (TestUser/UserB/TestReinald) ongemoeid. Geen tracebacks.

## [0.0.52] - 2026-08-24 — Dashboard: vaste grafieklijnen heten voortaan "Inkomsten (totaal)"/"Uitgaven (totaal)"

- **Wijziging**: de twee vaste aggregaatlijnen "Inkomsten" en "Uitgaven"
  (`AGGREGATE_STYLES`, `app/dashboard_chart.py`) heten nu "Inkomsten
  (totaal)" en "Uitgaven (totaal)" — in de checkbox-lijst, de
  grafieklegenda én de tooltip. Voorkomt verwarring met een
  gelijknamige categorie (een gebruiker kan immers zelf een categorie
  "Inkomsten" aanmaken, zoals TestReinald al deed) die er verderop in
  dezelfde lijst ook los tussen kan staan. "Verschil" blijft ongewijzigd.
- **Geverifieerd** op de live app (aparte poort): nieuwe labels
  verschijnen correct in de checkbox-lijst, de `data-label`/`<title>`
  van elk grafiekpunt en de legenda; de samenvattingskaarten bovenaan
  (los, hardcoded "Inkomsten"/"Uitgaven"/"Saldo (verschil)") zijn
  bewust ongemoeid gelaten. Geen tracebacks.

## [0.0.51] - 2026-08-24 — Dashboard: "Lijnen in de grafiek" krijgt nu ook subcategorie-lijnen, zelfde structuur als "Categorieën meetellen"

- **Wijziging**: "Lijnen in de grafiek" was een platte checkbox-lijst
  (de 3 vaste lijnen + één regel per categorie, alleen voor categorieën
  die ook meetellen). Nu dezelfde opbouw als "Categorieën meetellen"
  erboven: de 3 vaste lijnen blijven los bovenaan, categorieën daarna
  gesplitst in Inkomsten/Uitgaven-kolommen, elk met hetzelfde kleine
  pijltje om haar subcategorie-lijnen uit-/in te klappen. "Zonder
  categorie"/"Zonder subcategorie" staan er los onder, precies als
  daar.
- **Nieuw**: een subcategorie kan nu voor het eerst zélf ook als eigen
  lijn in de grafiek gekozen worden (`subcat:<id>`, niet eerder
  mogelijk) — netto bedrag per maand, exact zoals een categorielijn dat
  al deed, alleen nu gegroepeerd op subcategorie-niveau
  (`app/routes/dashboard.py`, `monthly_totals_for_user.sql` groepeerde
  al op subcat_ID, dat lag alleen nog niet ontsloten). Een
  subcategorie-lijn krijgt de kleur van haar categorie (leesbaar als
  "hoort bij") maar altijd hetzelfde vaste streepjespatroon
  (`_SUBCATEGORY_DASH`, `app/dashboard_chart.py`) — nooit hetzelfde
  patroon als haar eigen categorielijn, wel gedeeld tussen subcategorieën
  van dezelfde categorie (hun labels in legenda/tooltip blijven ze
  onderscheiden).
- **Cascade**: (de)selecteren van een categorie-lijn (de)selecteert nu
  ook al haar subcategorie-lijnen (zelfde `.dash-cat-checkbox`-mechanisme
  als bij "Categorieën meetellen", nu ook toegepast op deze checkboxen
  — geen nieuwe JS nodig). Andersom niet: een subcategorie-lijn los
  uit-/aanvinken laat haar categorie-lijn met rust.
- **Geverifieerd** op de live app (aparte poort) met een echte headless
  Firefox-sessie: uit-/inklappen werkt, cascade werkt in beide
  richtingen en via de "Alles selecteren/deselecteren"-knoppen, en een
  geselecteerde subcategorie-lijn verschijnt daadwerkelijk in de
  grafiek (legenda + polyline) met haar categorie's kleur en het eigen
  vaste streepjespatroon (`3,2,1,2`, bevestigd in de gerenderde SVG).
  Geen tracebacks.

## [0.0.50] - 2026-08-24 — Dashboard: elk instelling-blok en de tabel zijn nu in-/uitklapbaar

- **Wijziging**: het filterformulier boven aan het dashboard (Periode,
  Rekeningen meetellen, Categorieën meetellen, Lijnen in de grafiek) en
  de "Per categorie"-tabel eronder stonden allemaal permanent volledig
  uitgeklapt — eenmaal ingesteld, blijft dat veel ruimte innemen. Elk
  van deze vijf is nu een eigen `<details>`/`<summary>` (zelfde
  patroon als "Nieuwe regel toevoegen" elders in de app): standaard nog
  steeds open (niets verandert zonder actie), maar nu individueel
  dicht te klappen zodra je hem niet meer hoeft te zien. De drie
  samenvattingskaarten (Inkomsten/Uitgaven/Saldo) en de "Verloop over
  tijd"-grafiek blijven altijd zichtbaar — dat is de hoofdinhoud, geen
  instelling.
- **Geverifieerd** op de live app (aparte poort) met een echte headless
  Firefox-sessie (via het snap-pakket's ingebouwde `geckodriver`/
  `firefox-bin`, rechtstreeks aangestuurd — de losse `firefox`-snap-
  wrapper werkt niet onder deze sandbox): elk blok klapt in/uit zoals
  verwacht, en een aangevinkte checkbox in een dichtgeklapt blok
  (bijv. een categorie) wordt bij "Filteren" nog steeds gewoon
  meegestuurd in de query-string — `display:none` op een input heeft
  geen invloed op formulier-submission. Geen tracebacks.

## [0.0.49] - 2026-08-24 — Dashboard: categorieën-filter gesplitst in Inkomsten/Uitgaven, uitklapbare subcategorieën

- **Wijziging**: het dashboard-filter had één platte lijst met alle
  categorieën, en daaronder een aparte platte lijst met alle
  subcategorieën van alle categorieën samen (elk voorafgegaan door hun
  categorienaam: "Inkomsten: Salaris"). Nu net als de profielpagina's
  Inhoudsopgave (zie 0.0.44 t/m 0.0.48): twee kolommen ("Inkomsten"
  links, "Uitgaven" rechts, op basis van elke categorie's `Type`), en
  een categorie met subcategorieën krijgt hetzelfde kleine pijltje
  (`.toc-toggle`) om haar eigen subcategorie-checkboxes uit-/in te
  klappen — dieper ingesprongen (`5.5rem`), net als daar. "Zonder
  categorie"/"Zonder subcategorie" staan nu samen los onder de twee
  kolommen.
- **Nieuw gedrag**: een categorie-checkbox (de)selecteert bij het
  aan/uitvinken meteen al haar eigen subcategorie-checkboxes mee
  (`.dash-cat-checkbox`, app/static/js/dashboard.js) — één richting
  (categorie → subcategorieën), een subcategorie apart aan-/uitvinken
  laat de categorie met rust. De "Alles selecteren"/"Alles deselecteren"
  boven de categorieën vuren nu ook een `change`-event op elke checkbox
  na het omzetten, zodat die cascade ook daarbij meteen meegaat — de
  losse "Alles selecteren/deselecteren" boven de (nu verdwenen) platte
  subcategorieën-lijst is dus niet meer nodig, dit ene knoppenpaar dekt
  alles.
- Het pijltje-gedrag zelf (`.toc-toggle`, tot nu toe alleen in
  `app/static/js/user.js`) is verhuisd naar een eigen, gedeeld bestand
  `app/static/js/toc_toggle.js`, dat zowel de profielpagina als het
  dashboard nu laden — voorkomt dat dezelfde handler straks op twee
  plekken uit elkaar loopt.
- **Geverifieerd** op de live app (aparte poort): rendering klopt
  (kolommen, insprong, pre-checked op basis van bestaande selectie),
  filtering op een losgevinkte categorie/subcategorie werkt nog steeds
  correct (bestaande backend-logica in app/routes/dashboard.py is
  onveranderd), alle betrokken static bestanden (`toc_toggle.js`,
  `dashboard.js`, `user.js`) correct uitgeleverd, profielpagina
  onaangetast, geen tracebacks.

## [0.0.48] - 2026-08-24 — Inhoudsopgave: subcategorieën nóg dieper ingesprongen

- **Wijziging** (vervolg op 0.0.47): `2.75rem` insprong was nog steeds
  weinig te onderscheiden van de categorie zelf. Verdubbeld naar
  `5.5rem`.
- **Geverifieerd** op de live app (aparte poort): rendert correct, geen
  tracebacks.

## [0.0.47] - 2026-08-24 — Inhoudsopgave: dieper ingesprongen subcategorieën, groter uitklap-knopje

- **Wijziging** (vervolg op 0.0.46): het uitklap-pijltje (`.toc-toggle`)
  was zo klein en tekstloos dat het nauwelijks als knop te herkennen was.
  Nu een duidelijke ronde knop (1.6rem, `border` + `background: var(--bg)`
  in plaats van kale tekst) — nog steeds een pijltje, maar zichtbaar
  klikbaar, met dezelfde hover-kleur als andere knoppen in de app.
- De subcategorie-chips in de Inhoudsopgave sprongen amper in ten
  opzichte van hun categorie (`margin-left` gelijk aan de oude, kleine
  knopbreedte). Nu duidelijk dieper ingesprongen (`2.75rem`); de
  omschrijvingstekst van een categorie zelf schuift mee naar `1.95rem`
  zodat hij nog steeds recht onder de naam-chip begint (na het bredere
  knopje).
- **Geverifieerd** op de live app (aparte poort): HTML/CSS renderen
  correct, bestaande (echte) omschrijvingen van categorie "Inkomsten" en
  subcategorie "Salaris" bleven ongemoeid — niets aangepast of gewist dit
  keer, alleen gelezen ter controle. Dashboard onaangetast.

## [0.0.46] - 2026-08-24 — Inhoudsopgave: klein pijltje + omschrijving, omschrijving bewerkbaar bij de regels

- **Wijziging** (vervolg op 0.0.45): het uitklap-knopje (`▸ subcategorieën`)
  was zelf een chip-brede knop met tekst — veel groter dan nodig. Nu is
  het één klein pijltje (`›`, `.toc-toggle`), zonder tekst/chip-styling,
  links vóór de naam-chip. Categorieën zonder subcategorieën krijgen een
  even brede lege plek (`.toc-toggle-spacer`) zodat alle naam-chips
  binnen een kolom uitlijnen.
- Rechts van de naam-chip staat nu, alléén als er een omschrijving is,
  hetzelfde kleine pijltje — klikken toont/verbergt de omschrijvingstekst
  eronder (`.toc-description`). Subcategorie-chips in de Inhoudsopgave
  krijgen dezelfde behandeling: elk op zijn eigen regel, met een eigen
  pijltje voor zijn omschrijving als die er is.
- `app/static/js/user.js`'s toggle-handler is veralgemeniseerd van
  `.toc-expand-btn` naar `.toc-toggle`: één handler voor zowel het
  subcategorieën-pijltje als het omschrijving-pijltje, met
  `data-expanded-display` om "flex" (subcategorieën-rij) versus "block"
  (omschrijvingstekst) te kiezen.
- **Nieuw**: bij elke categorie en subcategorie in de regels-sectie staat
  nu een klein formulier ("Omschrijving") met een textarea + "Opslaan",
  gekoppeld aan de al bestaande routes `POST /categories/{id}/description`
  en `POST /subcategories/{id}/description` (zie 0.0.40) — de eerste UI
  voor een veld dat tot nu toe alleen via die routes zelf te zetten was.
- **Geverifieerd** op de live app (aparte poort): omschrijving zetten via
  het formulier in de regels-sectie verschijnt zowel daar (pre-filled bij
  herladen) als in de Inhoudsopgave achter het pijltje, voor zowel een
  categorie als een subcategorie; lege waarde wist hem weer. Geen
  tracebacks, JS/CSS correct uitgeleverd, dashboard onaangetast.

## [0.0.45] - 2026-08-24 — Inhoudsopgave: apart uitklap-knopje per categorie

- **Wijziging** (vervolg op 0.0.44): een categorie met subcategorieën in
  de Inhoudsopgave had zijn naam-link zélf als uitklap-trigger
  (`<summary>` er omheen) — dat kon de indruk wekken dat uitklappen niet
  (meer) mogelijk was, en koppelde "ga naar deze categorie" en "toon haar
  subcategorieën" aan dezelfde klik. Nu is dat een apart knopje
  (`▸ subcategorieën`) naast de naam-chip: de naam-link navigeert alleen,
  het knopje toont/verbergt alleen de subcategorie-chips eronder.
- Klein stukje nieuwe JS in `app/static/js/user.js`
  (`.toc-expand-btn`-handlers, geen library) — toggelt `aria-expanded` en
  de zichtbaarheid van het bijbehorende blokje; de pijl draait via CSS op
  basis van `aria-expanded` (`app/static/css/style.css`). Standaard
  dichtgeklapt.
- **Geverifieerd** op de live app (aparte poort): HTML bevat de losse
  naam-chip + knop + verborgen subcategorie-blok (`display: none`) per
  categorie met subcategorieën, JS/CSS worden correct uitgeleverd,
  dashboard onaangetast.

## [0.0.44] - 2026-08-24 — Inhoudsopgave: Uitgaven naast Inkomsten, links als chips

- **Wijziging** (vervolg op 0.0.43): de Inhoudsopgave-secties Inkomsten
  en Uitgaven staan nu naast elkaar in twee kolommen (Uitgaven rechts van
  Inkomsten) in plaats van onder elkaar — `.table-actions`
  (`display: flex`, al bestaande klasse) met elke kolom op `flex: 1`.
  Valt terug op gestapeld op een smal scherm (`flex-wrap: wrap`, zelfde
  patroon als elders op de pagina).
- Elke categorie-/subcategorie-link is nu een `.chip` (dezelfde
  pil-vormige knop-stijl die al overal in de app gebruikt wordt, bijv.
  voor keyword-chips en suggestie-knoppen) in plaats van een kale
  tekstlink.
- **Geverifieerd** op de live app (aparte poort): Inkomsten-kolom
  rendert links, Uitgaven rechts (bevestigd in de ruwe HTML-volgorde
  binnen de flex-container), elke link is een chip, uit-/inklappen van
  een categorie met subcategorieën werkt nog steeds, dashboard
  onaangetast.

## [0.0.43] - 2026-08-24 — Profielpagina: Inhoudsopgave per Inkomsten/Uitgaven, regels genest onder subcategorie

- **Wijziging**: eerste UI-fase voor de nieuwe categorie-structuur
  (Type, subcategorieën) — de profielpagina zelf, verdere pagina's
  volgen later.
- De **Inhoudsopgave** is gesplitst in twee groepen, "Inkomsten" en
  "Uitgaven" (op basis van elke categorie's `Type`). Een categorie met
  subcategorieën is uitklapbaar (`<details>`) en toont die subcategorieën
  ingesprongen eronder; categorie én subcategorie blijven allebei een
  link naar hun eigen plek op de pagina — subcategorieën hebben daarvoor
  nu een eigen anker (`id="subcat-{ID}"`).
- Binnen een categoriekaart staan **regels nu gegroepeerd op
  subcategorie**: regels zonder subcategorie blijven direct onder de
  categorie (zoals nu), en elke subcategorie krijgt haar eigen genest
  blokje met alleen haar eigen regels. De vlakke "Subcategorieën"-chips
  zijn vervangen door deze geneste blokjes (mét het bestaande
  verwijderknopje) — subcategorie-informatie stond eerst op twee
  plekken op de pagina, dat is nu één plek.
- Een regel toevoegen **vanuit een subcategorie's eigen formulier** kent
  die subcategorie automatisch toe (verborgen `subcat_id`-veld, geen
  dropdown) — vanuit de categorie zelf kies je nog steeds optioneel een
  subcategorie via de dropdown, of laat je hem leeg. Geen backend-
  wijziging nodig: `add_regel`/`resolve_or_create_subcategory`
  valideerden al dat een opgegeven subcat_id bij de juiste categorie
  hoort (zie 0.0.39/0.0.41).
- Nieuwe gedeelde partial `app/templates/_regel_card.html` — één
  regelkaart-template voor beide plekken (geen subcategorie / onder een
  subcategorie) in plaats van gedupliceerde markup. Jinja's `loop`
  propageert niet vanzelf in een `{% include %}`, dus `loop.index` wordt
  eerst expliciet naar een `regel_nummer`-variabele gezet.
- `app/user_page.py::load_user_page_data` groepeert regels nu per
  (categorie, subcategorie) in Python in plaats van als platte lijst,
  en geeft elke subcategorie haar eigen `regels`-lijst mee.
- **Geverifieerd** op de live app (aparte poort): Inhoudsopgave toont de
  juiste twee groepen met werkende uit-/inklap en ankers, regels staan
  onder de juiste subcategorie, een regel toevoegen via een
  subcategorie-formulier kent hem automatisch toe (bevestigd in de
  database), foutpaden (dubbele categorienaam, ongeldig bedrag) renderen
  nog steeds correct met de nieuwe geneste datastructuur, dashboard/
  review/regel-bewerkpagina onaangetast. Testdata na de check
  opgeruimd.

## [0.0.42] - 2026-08-24 — "Interne overboeking" gesplitst in inkomend/uitgaand (TestReinald)

- **Eenmalige data-reorganisatie**, geen schemawijziging: de categorie
  "Interne overboeking" (gebruiker TestReinald) is op verzoek gesplitst
  in twee — "Interne overboeking - inkomend" (Type 'Inkomsten') en
  "Interne overboeking - uitgaand" (Type 'Uitgaven') — want een interne
  overboeking is feitelijk twee verschillende dingen afhankelijk van de
  richting, niet één. Richting komt van `Af_bij` ('Bij'/'Af') —
  `Bedrag_eur` zelf is altijd unsigned opgeslagen (zie `sql/schema.sql`),
  dus "positief"/"negatief" zoals gevraagd komt neer op `Af_bij` =
  'Bij'/'Af'.
- Elke regel onder de oude categorie is gekloond naar twee regels (één
  per nieuwe categorie), met dezelfde kolom-voorwaarden plus een nieuwe
  Af_bij-voorwaarde ('Bij' resp. 'Af') — zelfde EN-over-kolommen-model
  als elke andere regel. De 50 al gemigreerde `afschrift`-rijen zijn
  herwezen naar de bijpassende nieuwe categorie op basis van hun eigen
  Af_bij (17 → inkomend, 33 → uitgaand); de oude regels en categorie zijn
  daarna verwijderd.
- `scripts/split_interne_overboeking.py` (eenmalig, met automatische
  backup, `--user-id` verplicht) — weigert als de oude categorie al een
  eigen subcategorie of een regel met een eigen Af_bij-voorwaarde heeft,
  in plaats van te gokken hoe die moeten worden samengevoegd.
- **Geverifieerd** eerst op een geïsoleerde scratch-kopie: nieuwe
  regels bevatten precies de verwachte kolom/keyword-combinatie, de
  Af_bij van elke herwezen `afschrift`-rij komt overeen met de naam van
  zijn nieuwe categorie (0 mismatches), 0 FK violations, oude
  regels/categorie weg. Daarna hetzelfde resultaat bevestigd op de live
  database.

## [0.0.41] - 2026-08-24 — Categorie-superclassificatie Inkomsten/Uitgaven (backend only, nog geen UI)

- **Nieuw**: elke categorie krijgt een `Type`: 'Inkomsten' of 'Uitgaven'
  — een super-classificatie één niveau boven de categorie zelf, los van
  de bestaande Inkomsten/Uitgaven-totalen op het dashboard (die worden
  per transactie berekend uit Af_bij, dit is een keuze op de categorie
  zelf). Subcategorieën krijgen geen eigen waarde — ze erven die van hun
  categorie via cat_ID (zelfde "by extension"-redenering als de
  categorie-scoping in 0.0.39).
- Nieuwe kolom `afschrift_categorien.Type`, bewust **NOT NULL** (geen
  "nog niet ingedeeld"-status) met `default 'Uitgaven'` — er is nog geen
  UI om dit bij het aanmaken te kiezen, dus een nieuwe categorie via het
  huidige kale "Nieuwe categorie"-formulier krijgt stilzwijgend
  'Uitgaven' en wordt later handmatig gecorrigeerd waar nodig
  (`sql/schema.sql`).
- Nieuwe gedeelde module `app/category_types.py` (`CATEGORY_TYPES`,
  `DEFAULT_CATEGORY_TYPE`, `clean_category_type`) — gebruikt door zowel
  `app/routes/categories.py` als `app/routes/review.py`'s "+ nieuwe
  categorie…"-flow, zelfde rolverdeling als `app/subcategories.py` voor
  subcategorieën.
- Nieuwe route `POST /categories/{cat_id}/type`
  (`sql/queries/reference_data/set_category_type.sql`) zet een
  bestaande categorie's Type. Anders dan `description`: een ongeldige/
  lege waarde wordt hier **geweigerd** met een foutmelding in plaats van
  stilzwijgend op 'Uitgaven' gezet — dat zou per ongeluk een al-juiste
  indeling kunnen overschrijven.
- **Migratie**: `scripts/migrate_add_category_type.py` (eenmalig, met
  automatische backup) — pure `ALTER TABLE ADD COLUMN` met NOT NULL +
  DEFAULT, geen tabel-rebuild nodig. Print bij het draaien de volledige
  lijst categorieën (per gebruiker) zodat je weet wat je nog moet
  nalopen; alle 29 bestaande categorieën startten als 'Uitgaven'.
  Categorie "Inkomsten" (ID 29, gebruiker TestReinald) is meteen
  omgezet naar Type 'Inkomsten' — de enige voor de hand liggende.
- **Geverifieerd** op de live app (aparte poort): Type zetten, een
  ongeldige waarde geweigerd (bestaande waarde blijft ongemoeid), nieuwe
  categorie krijgt stilzwijgend 'Uitgaven', cross-user poging genegeerd,
  CHECK-constraint weigert een bogus waarde rechtstreeks op de database,
  profiel-/dashboard-/review-pagina's renderen foutloos. Testdata na de
  check weer opgeruimd.

## [0.0.40] - 2026-08-24 — Beschrijving bij categorie/subcategorie (backend only, nog geen UI)

- **Nieuw**: categorieën en subcategorieën kunnen nu een vrije,
  optionele `description` hebben — puur een tekstveld voor eigen
  aantekeningen, nergens gebruikt door matching/filtering. Nieuwe
  nullable kolom op `afschrift_categorien`/`afschrift_subcategorien`
  (`sql/schema.sql`).
- Backend/queries zijn klaar: `POST /categories` en
  `POST /categories/{cat_id}/subcategories` accepteren een optioneel
  `description`-formveld bij aanmaken; twee nieuwe routes,
  `POST /categories/{cat_id}/description` en
  `POST /subcategories/{subcat_id}/description`, zetten (of wissen, bij
  een leeg/whitespace-only veld) de beschrijving van een bestaande
  (sub)categorie. Alle vier scoped op user-ownership, zelfde patroon als
  de rest van `app/routes/categories.py`.
- **Nog geen UI** — op eigen verzoek even niet meegenomen, de
  frontend-kant volgt later.
- **Migratie**: `scripts/migrate_add_category_descriptions.py`
  (eenmalig, met automatische backup) — puur additief, een nullable
  kolom erbij, bestaande rijen worden allemaal `NULL` (geen migratie
  nodig, geen tabel-rebuild).
- **Bijvangst**: tijdens het testen van deze wijziging kwamen twee
  wees-rijen in `afschrift_cat_regel_kolommen` aan het licht (ID's 134,
  135) — restanten van testregels die in de vorige werksessie
  (0.0.39-migratie) handmatig via een raw sqlite3-`DELETE` zonder
  `PRAGMA foreign_keys = ON` waren opgeruimd, waardoor de
  `ON DELETE CASCADE` niet vuurde. Rechtgezet op de live database (met
  backup); `PRAGMA foreign_key_check` geeft nu weer 0 violations.
- **Geverifieerd** op de live app (aparte poort): categorie/subcategorie
  aanmaken met beschrijving, beschrijving van een bestaande
  (sub)categorie zetten en wissen (leeg + whitespace-only → NULL),
  cross-user poging genegeerd (geen wijziging, gewoon een redirect), en
  profiel-/dashboard-/review-pagina's renderen nog steeds foutloos met de
  nieuwe kolom erbij. Testdata na de check weer opgeruimd.

## [0.0.39] - 2026-08-24 — Subcategorieën horen nu bij één categorie

- **Wijziging**: subcategorieën waren tot nu toe één gedeelde lijst per
  gebruiker, kiesbaar onder elke categorie. Nu horen ze bij precies één
  categorie — dezelfde naam (bijv. "Overig") mag daardoor wel weer onder
  meerdere categorieën bestaan, één keer per categorie
  (`unique (cat_ID, Name)` i.p.v. `unique (user_ID, Name)` in
  `sql/schema.sql`). De losse "Subcategorieën"-sectie op de profielpagina
  is vervangen door een eigen subcategorie-blokje per categoriekaart
  (`app/templates/user.html`); aanmaken gaat nu via
  `POST /categories/{cat_id}/subcategories` i.p.v. het vlakke
  `POST /subcategories`.
- De subcategorie-dropdown van een regel toont nu alleen nog de subcategorieën
  van de categorie waar die regel al onder valt (`app/routes/categories.py`,
  `regel_edit.html`) — niet meer alle subcategorieën van de gebruiker.
- Op `/review` kiest elke rij nog steeds category én subcategorie apart
  in dezelfde rij; een nieuw `app/static/js/review.js` filtert de
  subcategorie-dropdown client-side op de categorie die in diezelfde rij
  gekozen is (via `data-cat-id` op elke optie), en zet de subcategorie
  terug op "— geen —" zodra de gekozen categorie verandert.
- Op het dashboard-filter (`app/templates/index.html`) staat elke
  subcategorie-checkbox nu met zijn categorienaam ervoor (bijv.
  "Auto: Overig"), zodat gelijknamige subcategorieën van verschillende
  categorieën uit elkaar te houden zijn.
- **Beveiliging**: een subcategorie-ID die niet bij de bedoelde categorie
  hoort (geraden, verlopen, of van een andere categorie van dezelfde
  gebruiker) wordt overal stilzwijgend genegeerd (resultaat: geen
  subcategorie) in plaats van foutief gekoppeld — zowel bij een regel
  (`sql/queries/reference_data/set_regel_subcategory.sql`,
  `app/subcategories.py::resolve_or_create_subcategory`) als bij een
  `/review`-rij (`sql/queries/temp_afschrift/set_category.sql`). Dit gold
  voor `resolve_or_create_subcategory`'s numerieke-ID-pad voorheen niet
  eens op user-niveau — nu wel, als bijvangst van deze wijziging.
- **Migratie**: bestaande subcategorieën zijn gedropt (met de gebruiker
  bevestigd) — er was geen betrouwbare manier om automatisch te raden bij
  welke categorie een bestaande (tot nu toe categorieloze) subcategorie
  zou moeten horen. `scripts/migrate_scope_subcategorien_to_category.py`
  (eenmalig, met automatische backup) zet alle `subcat_ID`/
  `Afschrift_subcat_ID`-verwijzingen naar `NULL` en herbouwt de tabel met
  de nieuwe kolom/constraint (SQLite kan geen NOT NULL-kolom of nieuwe
  UNIQUE-constraint op een bestaande tabel ALTERen).
- **Geverifieerd** op de live app (aparte poort): subcategorie "Overig"
  aangemaakt onder twee verschillende categorieën (blijft apart, dubbele
  naam binnen dezelfde categorie geweigerd), profielpagina/regel-editor
  tonen per categorie alleen haar eigen subcategorieën, een
  cross-categorie subcat_id wordt zowel bij een regel als op `/review`
  genegeerd i.p.v. verkeerd gekoppeld, in-gebruik-check blokkeert
  verwijderen zoals voorheen. Testdata na de check weer opgeruimd.

## [0.0.38] - 2026-08-24 — OF verwijderd: keywords binnen een regel-kolom zijn nu altijd EN

- **Wijziging**: de EN/OF-keuze (`combine_mode`) voor hoe de keywords
  binnen één kolom-voorwaarde van een regel combineren is verwijderd —
  zo'n kolom vereist nu altijd dat alle keywords tegelijk voorkomen (EN).
  "Één van deze" ("OF") is niet meer instelbaar; wil je dat gedrag, maak
  dan een aparte regel per keyword — een categorie matcht immers al
  zodra één van haar regels matcht (OF over de regels van een
  categorie, ongewijzigd). De "Combineren met"-dropdown is weg uit het
  "Nieuwe regel toevoegen"-formulier en de regel-bewerkpagina
  (`app/templates/user.html`, `regel_edit.html`); de kolom
  `afschrift_cat_regel_kolommen.combine_mode` is uit `sql/schema.sql`
  verwijderd en de matching-SQL (`match_custom_rules.sql`,
  `categorize_batch.sql`, `recategorize_temp_afschrift.sql`) is
  vereenvoudigd naar altijd-EN.
- **Migratie**: `scripts/migrate_remove_combine_mode.py` (eenmalig, met
  automatische backup) zet bestaande regels om. De 15 bestaande
  kolom-groepen die op OF stonden hadden allemaal maar 1 keyword — EN en
  OF zijn daar identiek, dus geen gedragswijziging. De ene groep met 2+
  keywords op OF (de "Interne overboeking"-regel, Tegenrekening met 2
  IBAN's) is automatisch gesplitst in 2 losse regels, één per IBAN, zodat
  het matchgedrag exact hetzelfde blijft (via de bestaande OF-over-regels
  van een categorie).
- **Geverifieerd** op een geïsoleerde scratch-kopie: matchgedrag vóór en
  na de migratie is identiek voor de gesplitste regel (beide IBAN's
  matchen nog steeds, een derde IBAN nog steeds niet). Op de live app
  (aparte poort): profielpagina en regel-bewerkpagina renderen correct
  zonder de oude dropdown, en een nieuwe regel met 2 keywords op één
  kolom wordt correct als EN opgeslagen.

## [0.0.37] - 2026-08-20 — Geldbedragen op scherm nu in Nederlands formaat

- **Nieuw**: elk geldbedrag dat op scherm getoond wordt (dashboard-
  totalen Inkomsten/Uitgaven/Verschil, de "Per categorie"-tabel en haar
  uitklap-statements, de grafiek-as en -tooltip, `/review`, en de
  "laatste boeking" op de profielpagina) staat nu in Nederlands formaat
  ('.' voor duizendtallen, ',' voor decimalen — bijv. "€ 56.124,64" in
  plaats van "€ 56124.64"). Eerder gebeurde dit alleen al bij de
  CSV-export (`app/formatting.py::format_amount_nl`); die functie is nu
  ook als Jinja-filter `bedrag_nl` geregistreerd
  (`app/templating.py`) en overal waar voorheen `"%.2f"|format(...)`
  stond ingezet. Nieuwe `bedrag_nl_whole`-variant (geen decimalen, wel
  duizendtal-punten) voor de grafiek's compacte as-labels.
- **Geverifieerd** op een geïsoleerde scratch-kopie (aparte poort, niet
  de live server): dashboard-totalen, de categorie-tabel, de grafiek-as
  en de profielpagina tonen allemaal het Nederlandse formaat.

## [0.0.36] - 2026-08-20 — Bugfix: dashboard-filter met alleen datum wijzigen toonde geen data

- **Bugfix**: `_resolve_selected_ids` (`app/routes/dashboard.py`) las een
  leeg/afwezig `subcat_ids` (of `cat_ids`/`rekening_ids`) bij een
  ingediend filter altijd als "selecteer niets" — maar de bijbehorende
  checkboxgroep wordt alleen getoond als die lijst niet leeg is (`{% if
  subcategorieen %}` etc. in `index.html`). Vrijwel iedereen heeft nu nog
  0 subcategorieën, dus die checkboxes bestaan simpelweg niet — het
  formulier kon dat veld dus nooit bewust meesturen. Gevolg: alleen de
  datum wijzigen en op "Filteren" klikken verstuurde `filtered=1` zonder
  één `subcat_ids`, wat als "niets geselecteerd" werd gelezen en alle
  rijen wegfilterde, óók rijen zonder subcategorie. Een dimensie telt nu
  pas als bewust gefilterd wanneer er voor die dimensie ook echt een
  checkboxgroep bestond (lijst niet leeg); anders blijft hij op "alles"
  staan, ongeacht of er elders gefilterd is.
- **Geverifieerd** op een geïsoleerde scratch-kopie (aparte poort, niet
  de live server): totalen vóór en na het indienen van alleen een
  datumfilter zijn nu identiek, bevestigd met 0 subcategorieën aanwezig
  (het scenario dat de bug veroorzaakte).

## [0.0.35] - 2026-08-20 — Subcategorieën

- **Nieuw**: naast categorieën kun je nu ook subcategorieën gebruiken om
  binnen een categorie nog verder te filteren — bijv. categorie
  "Boodschappen" met subcategorieën "Weekboodschappen"/"Slijterij". Eén
  gedeelde lijst per gebruiker (`afschrift_subcategorien`,
  `sql/schema.sql`), niet gebonden aan één categorie — dezelfde
  subcategorie is dus onder elke categorie te kiezen. Altijd optioneel:
  "geen subcategorie" is overal een normale, geldige staat.
- Bij het aanmaken/bewerken van een **regel**
  (`/categories/{cat_id}/regels`, `/categories/regels/{id}/edit`) kies je
  nu optioneel ook een subcategorie, met een "+ nieuwe subcategorie…"
  inline-optie — zelfde patroon als de bestaande "+ nieuwe categorie…" op
  `/review`. Nieuwe sectie "Subcategorieën" op de profielpagina om de
  gedeelde lijst te beheren (toevoegen/verwijderen), naast de bestaande
  categorieën-sectie.
- Op **`/review`** staat nu ook een subcategorie-dropdown per rij, naast
  de bestaande categorie-dropdown — zelfde kies-of-maak-nieuwe patroon,
  en een nieuwe "Subcategorie"-kolom in de tabel.
- **Categorisatie** (`sql/categorization/categorize_batch.sql`,
  `recategorize_temp_afschrift.sql`): matcht een rij twee of meer regels
  van dezelfde (gewonnen) categorie met een verschillende subcategorie,
  dan blijft de subcategorie leeg in plaats van de rij als ambigu te
  markeren — subcategorie is altijd best-effort, nooit blokkerend; de
  categorie-toekenning/`processed`-status is hier volledig ongewijzigd
  door. Migratie naar `afschrift`
  (`sql/migration/insert_into_afschrift.sql`) neemt de subcategorie
  gewoon 1-op-1 mee.
- **Dashboard** (`/`): nieuwe checkbox-groep "Subcategorieën meetellen",
  zelfde aan/uit-patroon als categorieën — telt mee in de bestaande
  categorie-totalen (geen aparte subtotalen-rij of grafieklijn, dat was
  bewust niet de vraag). De uitklap-tabel per categorie en de CSV-export
  tonen er allebei een "Subcategorie"-kolom bij.
- Verwijderen: een subcategorie die nog in `temp_afschrift`/`afschrift`
  gebruikt wordt kan niet verwijderd worden (zelfde in-use-guard als
  categorieën, nieuwe `sql/queries/subcategorieen/count_usage_for_user.sql`)
  — een regel die de subcategorie alleen toewijst verliest bij verwijderen
  gewoon dat ene veld (`ON DELETE SET NULL`), de regel zelf en zijn
  categorie-toekenning blijven bestaan.
- Bestaande database bijgewerkt via nieuw eenmalig
  `scripts/migrate_add_subcategorien.py` (timestamped backup,
  `--dry-run`, idempotency-guard) — puur additief, geen bestaande rij
  verandert van vorm.
- **Geverifieerd** op een geïsoleerde scratch-kopie van de echte
  database: subcategorie aanmaken, regel met subcategorie toevoegen,
  synthetische rijen laten categoriseren (incl. het conflict-scenario:
  twee regels, zelfde categorie, verschillende subcategorie →
  subcategorie blijft leeg, categorie wordt gewoon 1x toegekend),
  handmatig corrigeren en opnieuw categoriseren op `/review` (bevestigd
  dat een al-opgeloste rij zijn handmatige subcategorie behoudt),
  migreren naar `afschrift`, filteren en CSV-exporteren op het dashboard,
  en verwijderen (geblokkeerd bij gebruik, `SET NULL` op een regel die
  hem alleen toewijst).

## [0.0.34] - 2026-08-19 — Profielpagina: laatste boeking per rekening

- Elke rekening op de profielpagina (`/user/{username}`) toont nu ook
  haar laatste boeking (datum, naam, bedrag), zodat in één oogopslag
  duidelijk is wat het meest recente is — inclusief nog niet gemigreerde
  `temp_afschrift`-rijen, herkenbaar aan een "nog niet gemigreerd"-label.
  Nieuwe query `sql/queries/rekeningen/latest_entry_for_user.sql`:
  bepaalt de "laatste" boeking op basis van welke tabel de rij in staat
  (`temp_afschrift` wint áltijd als de rekening daar nog wachtende rijen
  heeft), niet op basis van `Datum` — dat volgt direct uit migratie's
  alles-of-niets-regel (Fase 4): zolang er ook maar één rij wacht, is er
  nog niet gemigreerd, dus is de hele wachtrij per definitie recenter dan
  wat al in `afschrift` staat, ook al zou een losse datumvergelijking
  toevallig anders uitkomen. `app/user_page.py::load_user_page_data`
  voegt dit als `latest_entry` toe aan elke rekening (`None` = nog geen
  enkele statement).
- **Geverifieerd** op een geïsoleerde scratch-kopie met drie rekeningen:
  één zonder data (toont "nog geen statements geüpload"), één met alleen
  `afschrift`-rijen (toont terecht de nieuwste daarvan), en één met een
  `afschrift`-rij met een latere kalenderdatum náást een wachtende
  `temp_afschrift`-rij met een eerdere datum — bevestigd dat de wachtende
  rij toch als "laatste" getoond wordt (met het label), precies zoals
  bedoeld op basis van tabel-prioriteit in plaats van datum.

## [0.0.33] - 2026-08-19 — Updatemechanisme: versiebeheer + update-banner

- **Nieuw**: Ook de test met failure is goed gegaan.

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
