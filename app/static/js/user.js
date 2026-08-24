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
})();
