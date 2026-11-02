"""Pensioenplanner: year-by-year projection of savings/investments given a
set of recurring/one-off income and expense "posten"
(app/routes/pensioenplanner.py). Pure calculation, no database access —
same split as app/dashboard_chart.py for the dashboard's own linegraph.

The projection's time axis is always calendar year, never age. A
household can track multiple people (fire_personen) with their own birth
year, each with their own AOW/pension starting at their own age — "age"
alone would be ambiguous as a shared axis the moment two tracked people
have a different age. Every fire_post's start_jaar/stop_jaar are therefore
always the authoritative, already-resolved calendar years by the time
they reach this module, regardless of whether they were entered in the
UI as an absolute year or as "age X of person Y" (that resolution happens
once, in app/routes/pensioenplanner.py, before a post is ever saved).
"""
from typing import Optional


def _effective_groei_pct(post, algemeen_groei_pct: float) -> float:
    return post["groei_pct"] if post["groei_pct"] is not None else algemeen_groei_pct


def _bedrag_voor_jaar(post, jaar: int, default_start: int, default_stop: int, algemeen_groei_pct: float) -> float:
    """One post's contribution in one projection year — 0 outside its
    [start_jaar, stop_jaar] window (each falling back to the projection's
    own start/eind_jaar when unset, i.e. "active for the whole
    projection"). An eenmalig post counts its full jaarbedrag exactly once,
    in its start year, with no compounding; every other post compounds by
    its own groei_pct (or the projection's algemeen_groei_pct, if it has
    none of its own) for every year since its start."""
    start = post["start_jaar"] if post["start_jaar"] is not None else default_start
    stop = post["stop_jaar"] if post["stop_jaar"] is not None else default_stop
    if jaar < start or jaar > stop:
        return 0.0
    if post["eenmalig"]:
        return float(post["jaarbedrag"]) if jaar == start else 0.0
    groei = _effective_groei_pct(post, algemeen_groei_pct)
    jaren_sinds_start = jaar - start
    return float(post["jaarbedrag"]) * ((1 + groei / 100) ** jaren_sinds_start)


def build_projection(instellingen, posten, personen) -> dict:
    """instellingen: a fire_instellingen row. posten: fire_posten rows
    (actief=0 rows are skipped entirely — excluded from the projection,
    not merely hidden). personen: fire_personen rows, used only to derive
    a per-year age column for display; the projection math itself never
    reads geboortejaar.

    Returns {"jaren": [...], "jaar_geld_op": int | None}. Each entry in
    "jaren" is {"jaar", "leeftijden" ({persoon_id: age}), "inkomsten",
    "uitgaven", "netto", "saldo_spaargeld", "saldo_beleggingen", "totaal"}.
    "jaar_geld_op" is the first year total vermogen (saldo_spaargeld +
    saldo_beleggingen) drops below zero, or None if that never happens
    within the projection horizon.
    """
    start_jaar = instellingen["start_jaar"]
    eind_jaar = instellingen["eind_jaar"]
    algemeen_groei_pct = instellingen["algemeen_groei_pct"]
    rendement_spaargeld = instellingen["rendement_spaargeld_pct"] / 100
    rendement_beleggingen = instellingen["rendement_beleggingen_pct"] / 100

    actieve_posten = [p for p in posten if p["actief"]]

    saldo_spaargeld = float(instellingen["saldo_spaargeld"])
    saldo_beleggingen = float(instellingen["saldo_beleggingen"])

    jaren = []
    jaar_geld_op: Optional[int] = None
    for jaar in range(start_jaar, eind_jaar + 1):
        inkomsten = 0.0
        uitgaven = 0.0
        for post in actieve_posten:
            bedrag = _bedrag_voor_jaar(post, jaar, start_jaar, eind_jaar, algemeen_groei_pct)
            if post["type"] == "Inkomsten":
                inkomsten += bedrag
            else:
                uitgaven += bedrag
        netto = inkomsten - uitgaven

        # Net cashflow lands in the savings pot; investments compound
        # independently (no automatic transfer between the two pots in
        # v1 — see docs/ARCHITECTURE.md's pensioenplanner section).
        saldo_spaargeld = saldo_spaargeld * (1 + rendement_spaargeld) + netto
        saldo_beleggingen = saldo_beleggingen * (1 + rendement_beleggingen)
        totaal = saldo_spaargeld + saldo_beleggingen

        if jaar_geld_op is None and totaal < 0:
            jaar_geld_op = jaar

        jaren.append({
            "jaar": jaar,
            "leeftijden": {p["ID"]: jaar - p["geboortejaar"] for p in personen},
            "inkomsten": inkomsten,
            "uitgaven": uitgaven,
            "netto": netto,
            "saldo_spaargeld": saldo_spaargeld,
            "saldo_beleggingen": saldo_beleggingen,
            "totaal": totaal,
        })

    return {"jaren": jaren, "jaar_geld_op": jaar_geld_op}
