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
})();
