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

  // Inhoudsopgave: small chevron toggles, separate from the (sub)category's
  // own navigation chip — clicking the name just jumps to it, clicking a
  // toggle only reveals/hides something right there in the Inhoudsopgave:
  // a category's toggle (left of its name) shows/hides its subcategories,
  // a (sub)category's toggle (right of its name, only present when there's
  // a description) shows/hides that description text (see
  // app/templates/user.html). Both share this one handler — data-target
  // names the element to show/hide, data-expanded-display its display
  // value when shown ("flex" if omitted). aria-expanded drives the arrow's
  // rotation via CSS (app/static/css/style.css's
  // .toc-toggle[aria-expanded="true"]).
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
})();
