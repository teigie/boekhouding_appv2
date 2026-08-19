(function () {
  // Showing/hiding on load already happens in the inline script right
  // after the banner markup in base.html (has to run before this
  // deferred file to avoid a flash) — this only handles the dismiss
  // click: remember the version so the banner stays hidden until a
  // *newer* one shows up, then vanish it immediately without a reload.
  var banner = document.getElementById("update-banner");
  if (!banner) return;

  var dismissBtn = document.getElementById("update-banner-dismiss");
  if (dismissBtn) {
    dismissBtn.addEventListener("click", function () {
      localStorage.setItem("boekhouding-dismissed-update", banner.dataset.version);
      banner.hidden = true;
    });
  }
})();
