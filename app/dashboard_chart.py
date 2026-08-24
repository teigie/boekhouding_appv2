"""Month-range math and the dashboard's linegraph, kept out of
app/routes/dashboard.py because both are sizeable on their own.

Design notes (see docs/ARCHITECTURE.md, "Dashboard" for the full picture):

- The dashboard filters by whole calendar months ("aug 2025 t/m dec
  2025"), not arbitrary dates — `parse_month`/`month_range` are the only
  place month arithmetic happens.
- Rekening/categorie selection is filtered and summed in *Python*, not
  SQL, deliberately: the app never builds SQL strings with a dynamic
  number of placeholders (see sql/queries/README.md) for an IN-list of
  checked IDs. `sql/queries/afschrift/monthly_totals_for_user.sql`
  fetches one small, fixed result set (rekeningen x categorieen x
  months for the whole range) and everything past that — which
  Rekeningen/categorieen count, which lines get drawn, the per-month
  sums — is plain Python over that list.
- Line colors/dash patterns are assigned by fixed ROLE (Inkomsten/
  Uitgaven/Verschil always get the same color) or, for a category line,
  by that category's own cat_id (`cat_id % len(CATEGORY_COLOR_VARS)`) —
  never by its position in the current selection. That's what keeps a
  line's color stable as the user checks/unchecks other categories (see
  the dataviz skill: "color follows the entity, never its rank"). The
  CSS custom properties referenced here (--series-*) are defined in
  style.css with light/dark pairs from the skill's validated
  categorical palette.
"""
import calendar
from datetime import date
from typing import Optional

# Fixed roles always get the same color + dash pattern, regardless of
# which categories are also selected.
AGGREGATE_STYLES = {
    "inkomsten": {"label": "Inkomsten (totaal)", "color_var": "--series-inkomsten", "dash": "none"},
    "uitgaven": {"label": "Uitgaven (totaal)", "color_var": "--series-uitgaven", "dash": "8,4"},
    "verschil": {"label": "Verschil", "color_var": "--series-verschil", "dash": "2,3"},
}
# Distinct from the three aggregate hues above — see style.css for the
# light/dark hex values behind each variable.
CATEGORY_COLOR_VARS = [
    "--series-cat-0", "--series-cat-1", "--series-cat-2", "--series-cat-3", "--series-cat-4",
]
# Cycled independently of color, so that even a coincidentally-similar
# hue (e.g. many categories selected at once) still reads as a distinct
# line — "identity is never color-alone".
_DASH_PATTERNS = ["none", "8,4", "2,3", "10,3,2,3"]
# A subcategory line always uses this one fixed dash (never one of
# _DASH_PATTERNS above, so it can never coincidentally match its own
# parent's dash) — see subcategory_style().
_SUBCATEGORY_DASH = "3,2,1,2"


def parse_month(value: Optional[str], fallback: date) -> date:
    """"YYYY-MM" -> date on the 1st of that month. Invalid/missing ->
    the 1st of fallback's month."""
    if value:
        try:
            year_str, month_str = value.split("-")
            return date(int(year_str), int(month_str), 1)
        except (ValueError, TypeError):
            pass
    return fallback.replace(day=1)


def month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def month_end(d: date) -> date:
    """Last calendar day of d's month."""
    last_day = calendar.monthrange(d.year, d.month)[1]
    return d.replace(day=last_day)


def add_months(d: date, n: int) -> date:
    month_index = d.month - 1 + n
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def month_range(start: date, end: date) -> list[str]:
    """Every "YYYY-MM" from start's month through end's month, inclusive.
    Caller (dashboard.py) is responsible for start <= end."""
    months = []
    cur = start.replace(day=1)
    last = end.replace(day=1)
    while cur <= last:
        months.append(month_key(cur))
        cur = add_months(cur, 1)
    return months


def category_style(cat_id, category_name: str) -> dict:
    """cat_id is None for the "Zonder categorie" pseudo-category — hashed
    in alongside real IDs (using -1) so it still gets a stable color *and*
    dash pattern, both keyed by cat_id rather than the category's position
    in the current selection (same reasoning as the module docstring:
    unchecking one category must not repaint/re-dash another)."""
    key = cat_id if cat_id is not None else -1
    return {
        "label": category_name,
        "color_var": CATEGORY_COLOR_VARS[key % len(CATEGORY_COLOR_VARS)],
        "dash": _DASH_PATTERNS[key % len(_DASH_PATTERNS)],
    }


def subcategory_style(cat_id, subcategory_name: str) -> dict:
    """A subcategory's line inherits its parent category's color
    (cat_id, same rule as category_style — stable by ID, "Zonder
    categorie"'s subcategories pass None here same as their parent
    would) so it visually groups with that category, but always gets
    this module's one fixed _SUBCATEGORY_DASH rather than a dash cycled
    by its own subcat_id — that guarantees a subcategory's line can
    never coincidentally render identical (same color AND dash) to its
    own parent's line. Siblings under the same category do share this
    look (color + dash both fixed to the parent), which is an accepted
    trade-off — their legend/tooltip labels still disambiguate them."""
    return {
        "label": subcategory_name,
        "color_var": category_style(cat_id, "")["color_var"],
        "dash": _SUBCATEGORY_DASH,
    }


def build_series(months: list[str], line_defs: list[dict], monthly_values: dict) -> list[dict]:
    """line_defs: [{"key": "inkomsten"|"uitgaven"|"verschil"|"cat:<id|none>",
    "label": ..., "color_var": ..., "dash": ...}] — every entry already
    carries a stable "dash" (from AGGREGATE_STYLES or category_style(),
    never assigned by list position — see module docstring).
    monthly_values: {(month, key): float}. Returns each line with one
    point per month (0.0 for months with no matching rows, so the line
    doesn't skip gaps)."""
    series = []
    for line in line_defs:
        points = [
            {"month": m, "value": monthly_values.get((m, line["key"]), 0.0)}
            for m in months
        ]
        series.append({**line, "points": points})
    return series


def build_chart(months: list[str], series: list[dict]) -> Optional[dict]:
    """Scales `series` (as built by build_series) into SVG pixel
    coordinates. Returns None if there's nothing to plot (no months or no
    lines selected) so the template can show an empty state instead of a
    degenerate chart."""
    if not months or not series:
        return None

    width, height = 760, 320
    margin = {"top": 16, "right": 16, "bottom": 36, "left": 64}
    plot_x0, plot_x1 = margin["left"], width - margin["right"]
    plot_y0, plot_y1 = margin["top"], height - margin["bottom"]

    all_values = [p["value"] for s in series for p in s["points"]]
    v_min, v_max = min(all_values + [0.0]), max(all_values + [0.0])
    if v_min == v_max:
        v_min, v_max = v_min - 1, v_max + 1
    # A little headroom so the highest/lowest point isn't glued to the edge.
    padding = (v_max - v_min) * 0.08
    v_min -= padding
    v_max += padding

    def scale_y(value: float) -> float:
        fraction = (value - v_min) / (v_max - v_min)
        return plot_y1 - fraction * (plot_y1 - plot_y0)

    def scale_x(index: int) -> float:
        if len(months) == 1:
            return (plot_x0 + plot_x1) / 2
        return plot_x0 + (index / (len(months) - 1)) * (plot_x1 - plot_x0)

    scaled_series = []
    for s in series:
        points = [
            {"x": round(scale_x(i), 1), "y": round(scale_y(p["value"]), 1), "value": p["value"], "month": p["month"]}
            for i, p in enumerate(s["points"])
        ]
        scaled_series.append({**s, "points": points})

    # Thin x-axis labels so they don't overlap when many months are shown.
    max_labels = 12
    step = max(1, -(-len(months) // max_labels))  # ceil division
    x_ticks = [
        {"x": round(scale_x(i), 1), "label": m}
        for i, m in enumerate(months)
        if i % step == 0 or i == len(months) - 1
    ]

    y_tick_count = 4
    y_ticks = []
    for i in range(y_tick_count + 1):
        value = v_min + (v_max - v_min) * i / y_tick_count
        y_ticks.append({"y": round(scale_y(value), 1), "value": value})

    zero_y = round(scale_y(0.0), 1) if v_min < 0 < v_max else None

    return {
        "width": width,
        "height": height,
        "plot": {"x0": plot_x0, "x1": plot_x1, "y0": plot_y0, "y1": plot_y1},
        "zero_y": zero_y,
        "x_ticks": x_ticks,
        "y_ticks": y_ticks,
        "series": scaled_series,
    }
