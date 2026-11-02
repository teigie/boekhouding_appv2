(function () {
  // Shared small chevron toggle (`.toc-toggle`) — used both by the
  // profile page's Inhoudsopgave (app/templates/user.html: a category's
  // toggle shows/hides its subcategories, a (sub)category's toggle
  // shows/hides its description text) and by the dashboard's category
  // filter (app/templates/index.html: a category's toggle shows/hides
  // its subcategory checkboxes). data-target names the element to
  // show/hide, data-expanded-display its display value when shown
  // ("flex" if omitted). aria-expanded drives the arrow's rotation via
  // CSS (app/static/css/style.css's .toc-toggle[aria-expanded="true"]).
  document.querySelectorAll(".toc-toggle").forEach(function (button) {
    var target = document.getElementById(button.dataset.target);
    if (!target) {
      return;
    }
    var expandedDisplay = button.dataset.expandedDisplay || "flex";
    button.addEventListener("click", function () {
      var expanded = button.getAttribute("aria-expanded") === "true";
      button.setAttribute("aria-expanded", String(!expanded));
      target.style.display = expanded ? "none" : expandedDisplay;
    });
  });

  // "Alles selecteren"/"Alles deselecteren" above a group of same-named
  // checkboxes (data-check-group is the checkbox `name`, so this works
  // for any checkbox group that gets such a button pair — the dashboard's
  // rekening/categorie/grafieklijn filters, the pensioenplanner's "Actief"
  // column, ...). Only sets the checkboxes themselves and fires a
  // "change" event on each (so a page-specific cascade handler, like the
  // dashboard's category -> subcategory one, still runs) — it never
  // submits anything itself.
  document.querySelectorAll(".checkbox-toggle-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var checked = btn.dataset.checkAction === "all";
      var selector = 'input[type="checkbox"][name="' + btn.dataset.checkGroup + '"]';
      document.querySelectorAll(selector).forEach(function (box) {
        box.checked = checked;
        box.dispatchEvent(new Event("change"));
      });
    });
  });

  // A whole row toggles a sibling detail row's visibility — the
  // dashboard's "Per categorie" table (a category row reveals its
  // subcategorieën, a subcategorie row its statements) and the
  // pensioenplanner's posten table (a hoofdcategorie row reveals its
  // individual posten) both use this: data-cat-target names the detail
  // row's id, tabindex/role="button" (set in the template) make it
  // keyboard-operable too.
  document.querySelectorAll(".category-row").forEach(function (row) {
    var target = document.getElementById(row.dataset.catTarget);
    if (!target) return;

    function toggle() {
      var expanded = row.getAttribute("aria-expanded") === "true";
      row.setAttribute("aria-expanded", String(!expanded));
      target.hidden = expanded;
    }

    row.addEventListener("click", toggle);
    row.addEventListener("keydown", function (evt) {
      if (evt.key === "Enter" || evt.key === " ") {
        evt.preventDefault();
        toggle();
      }
    });
  });
})();
