(function () {
  // "Rekening verwijderen" heeft geen bevestigingspagina — dit is de
  // enige rem tussen een klik en het permanent kwijtraken van alle
  // bijbehorende temp_afschrift/afschrift-geschiedenis (zie
  // app/routes/accounts.py::delete_account). data-count komt uit
  // sql/queries/rekeningen/count_data_for_user.sql (app/user_page.py),
  // dus de melding noemt altijd het actuele, exacte aantal rijen.
  document.querySelectorAll(".js-confirm-delete-rekening").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      var name = form.dataset.rekeningName;
      var count = Number(form.dataset.count || "0");
      var message = "Rekening '" + name + "' verwijderen?";
      if (count > 0) {
        message += " Dit verwijdert ook " + count + " bijbehorende bankafschriftregel(en) " +
          "permanent — dit kan niet ongedaan gemaakt worden.";
      } else {
        message += " Dit kan niet ongedaan gemaakt worden.";
      }
      if (!window.confirm(message)) {
        event.preventDefault();
      }
    });
  });

  // Inhoudsopgave: each category with subcategories gets its own
  // dedicated expand/collapse button, separate from the category's own
  // navigation chip — clicking the category name just jumps to it,
  // clicking this button only reveals/hides its subcategory chips right
  // there in the Inhoudsopgave (see app/templates/user.html). aria-
  // expanded drives the arrow's rotation via CSS (app/static/css/
  // style.css's .toc-expand-btn[aria-expanded="true"]).
  document.querySelectorAll(".toc-expand-btn").forEach(function (button) {
    var target = document.getElementById(button.dataset.target);
    if (!target) {
      return;
    }
    button.addEventListener("click", function () {
      var expanded = button.getAttribute("aria-expanded") === "true";
      button.setAttribute("aria-expanded", String(!expanded));
      target.style.display = expanded ? "none" : "flex";
    });
  });
})();
