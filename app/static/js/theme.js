// Licht/donker-knop. Het onthouden en meteen (zonder flits) toepassen van
// een eerder gekozen thema gebeurt in het inline scriptje in base.html
// <head> — dit bestand behandelt alleen de knop zelf, want het wordt pas
// na de rest van de pagina geladen (`defer`).
(function () {
  var STORAGE_KEY = "boekhouding-theme";
  var button = document.getElementById("theme-toggle");
  if (!button) return;

  function isSystemDark() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  // Het thema dat nu daadwerkelijk zichtbaar is: de expliciete keuze
  // (data-theme) als die er is, anders wat het systeem op dit moment wil.
  function effectiveTheme() {
    var explicit = document.documentElement.getAttribute("data-theme");
    if (explicit === "dark" || explicit === "light") return explicit;
    return isSystemDark() ? "dark" : "light";
  }

  function render() {
    var theme = effectiveTheme();
    // Toont het icoon van het thema waar de knop NAAR toe schakelt.
    button.textContent = theme === "dark" ? "☀️" : "🌙";
    button.setAttribute(
      "aria-label",
      theme === "dark" ? "Schakel naar licht thema" : "Schakel naar donker thema"
    );
  }

  button.addEventListener("click", function () {
    var next = effectiveTheme() === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem(STORAGE_KEY, next);
    render();
  });

  render();
})();
