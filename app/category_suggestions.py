"""Curated starter set of categories/subcategories offered on the
one-time onboarding page (app/routes/onboarding.py, app/templates/
onboarding_suggesties.html) right after a new user signs up
(app/routes/auth.py::create_user_and_login) — lets a brand-new user
start from a sensible, common Dutch personal-finance category tree
instead of a completely empty list. One all-or-nothing accept/skip
choice, not picked category-by-category.

Deliberately plain Python data, not a database table — unlike
afschrift_categorie_suggesties (the flat, name-only list of one-click
suggestion chips on /categories, see sql/queries/categorieen/
list_suggestions.sql), this one needs hierarchy (subcategorieën) and a
Type (Inkomsten/Uitgaven) per top-level category, and is meant to stay a
fixed, curated list rather than admin-editable data.

A category entry's "description" key is optional — omitted entirely for
most (see app/routes/onboarding.py's `cat.get("description")`, not
`cat["description"]`), present only where a suggested category benefits
from an explanatory note up front.
"""

CATEGORY_SUGGESTIONS = [
    {
        "type": "Inkomsten",
        "categories": [
            {"name": "Salaris", "subcategorieen": []},
            {"name": "Rente", "subcategorieen": []},
            {"name": "Toeslagen", "subcategorieen": ["Zorgtoeslag", "Huurtoeslag"]},
            {"name": "Terug storting derden", "subcategorieen": []},
            {"name": "Dividend / Aandelen", "subcategorieen": []},
            {"name": "Schenkingen", "subcategorieen": []},
            {"name": "Nalatenschap", "subcategorieen": []},
            {"name": "Interne Overboeking - inkomend", "subcategorieen": []},
        ],
    },
    {
        "type": "Uitgaven",
        "categories": [
            {"name": "Abonnementen", "subcategorieen": ["Streamingdienst", "TV / internet", "Mobiel"]},
            {"name": "Auto", "subcategorieen": ["Brandstof", "Verzekering", "Belasting", "Onderhoud auto"]},
            {"name": "OV", "subcategorieen": []},
            {
                "name": "Levensmiddelen",
                "description": (
                    "Dagelijkse boodschappen, verzorgingsproducten bij drogist en "
                    "schoonmaakmiddelen dagelijks gebruik."
                ),
                "subcategorieen": [],
            },
            {"name": "Bankkosten", "subcategorieen": []},
            {"name": "Geld opnemen", "subcategorieen": []},
            {"name": "Interne overboeking - uitgaand", "subcategorieen": []},
            {
                "name": "Wonen",
                "subcategorieen": [
                    "Huur / kostgeld", "Hypotheek", "Energie", "Water", "Onderhoud huis",
                    "Verzekering", "Gemeentelijke heffingen", "Waterschapsbelasting", "Inboedel",
                ],
            },
            {"name": "Zorg", "subcategorieen": ["Verzekering", "Tandarts", "Medicatie"]},
            {
                "name": "Vakantie / uitjes / uit eten",
                "subcategorieen": ["Reisverzekering", "Accomodatie", "Restauraunt"],
            },
            {"name": "Kleding / Schoenen", "subcategorieen": []},
            # "Levensmiddelen" was listed twice in the original request
            # (once here again, right after "Kleding / Schoenen") — kept
            # only once above, since a user can't have two categories
            # with the same name anyway (see sql/schema.sql's unique
            # (user_ID, Name)).
            {"name": "Hobbies", "subcategorieen": []},
            {"name": "Boetes", "subcategorieen": []},
            {"name": "Cadeaus", "subcategorieen": []},
            {"name": "Aandelen", "subcategorieen": []},
        ],
    },
]
