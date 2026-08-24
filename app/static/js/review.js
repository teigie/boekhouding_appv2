(function () {
  // Subcategories are scoped to exactly one category (see sql/schema.sql),
  // but each /review row picks its category AND subcategory independently
  // in the same row (app/routes/review.py::save_categories) — so the
  // subcategory <select> ships with every one of the user's subcategories
  // as <option>s, each tagged data-cat-id (sql/queries/subcategorieen/
  // list_for_user.sql), and this filters which of them are actually
  // choosable based on that row's own category <select>, client-side, with
  // no server round-trip needed to change what's offered.
  //
  // An option with no data-cat-id ("— geen —" and "+ nieuwe subcategorie…")
  // is always shown, regardless of category.
  function filterSubcategoryOptions(row) {
    var categorySelect = row.querySelector(".category-select");
    var subcategorySelect = row.querySelector(".subcategory-select");
    if (!categorySelect || !subcategorySelect) {
      return;
    }
    var selectedCatId = categorySelect.value;
    var previousValue = subcategorySelect.value;
    var stillValid = false;

    Array.prototype.forEach.call(subcategorySelect.options, function (option) {
      var optionCatId = option.dataset.catId;
      var matches = !optionCatId || optionCatId === selectedCatId;
      option.hidden = !matches;
      option.disabled = !matches;
      if (matches && option.value === previousValue) {
        stillValid = true;
      }
    });

    // The previously chosen subcategory no longer belongs to the now-
    // selected category (or the category itself just changed, e.g. to
    // "+ nieuwe categorie…", which has no subcategories of its own yet) —
    // fall back to "— geen —" rather than silently keeping a mismatched
    // choice that save_categories would just drop anyway (see
    // app/subcategories.py::resolve_or_create_subcategory).
    if (!stillValid) {
      subcategorySelect.value = "";
      subcategorySelect.dispatchEvent(new Event("change"));
    }
  }

  document.querySelectorAll(".category-select").forEach(function (categorySelect) {
    var row = categorySelect.closest("tr");
    if (!row) {
      return;
    }
    filterSubcategoryOptions(row);
    categorySelect.addEventListener("change", function () {
      filterSubcategoryOptions(row);
    });
  });
})();
