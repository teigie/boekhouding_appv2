(function () {
  // Van/Tot en met: een kalender-popover (jaarpijltjes + maandraster)
  // per veld, in plaats van <input type="month"> — Firefox rendert die
  // niet als kalender, enkel als los te typen cijfers. Elke
  // .month-picker beheert zijn eigen verborgen input (wat het formulier
  // echt submit, zelfde "YYYY-MM"-vorm als voorheen, dus de
  // preset-knoppen hieronder en de backend hoeven hier niets van af te
  // weten) en knop-label; er staat er maar één tegelijk open.
  var MONTH_NAMES_NL = [
    "januari", "februari", "maart", "april", "mei", "juni",
    "juli", "augustus", "september", "oktober", "november", "december",
  ];
  // Gangbare Nederlandse 3-letterafkortingen — niet simpelweg de eerste
  // drie letters van de volledige naam, want dat geeft voor maart "maa"
  // in plaats van het gebruikelijke "mrt".
  var MONTH_ABBR_NL = [
    "jan", "feb", "mrt", "apr", "mei", "jun",
    "jul", "aug", "sep", "okt", "nov", "dec",
  ];
  var openPicker = null;

  function closeOpenPicker() {
    if (!openPicker) return;
    openPicker.popover.hidden = true;
    openPicker.trigger.setAttribute("aria-expanded", "false");
    openPicker = null;
  }

  document.querySelectorAll(".month-picker").forEach(function (picker) {
    var hidden = picker.querySelector('input[type="hidden"]');
    var trigger = picker.querySelector(".month-picker-trigger");
    var popover = picker.querySelector(".month-picker-popover");
    var yearLabel = popover.querySelector(".month-picker-year");
    var grid = popover.querySelector(".month-picker-grid");
    var displayYear;

    function current() {
      var bits = hidden.value.split("-");
      return { year: parseInt(bits[0], 10), month: parseInt(bits[1], 10) };
    }

    function updateTriggerLabel() {
      // Zelfde afgekorte "okt 2026"-vorm als de rest van het dashboard
      // (app/formatting.py::format_month_nl, de grafiek-as hieronder) —
      // en dus ook identiek aan de server-gerenderde knoptekst bij het
      // laden van de pagina, zodat er geen zichtbare sprong is zodra dit
      // script draait.
      var c = current();
      trigger.textContent = MONTH_ABBR_NL[c.month - 1] + " " + c.year;
    }

    function renderGrid() {
      yearLabel.textContent = displayYear;
      grid.textContent = "";
      var selected = current();
      MONTH_NAMES_NL.forEach(function (name, index) {
        var month = index + 1;
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "month-picker-month";
        if (selected.year === displayYear && selected.month === month) {
          btn.classList.add("is-selected");
        }
        btn.textContent = MONTH_ABBR_NL[index];
        btn.title = name;
        btn.addEventListener("click", function () {
          hidden.value = displayYear + "-" + (month < 10 ? "0" + month : month);
          updateTriggerLabel();
          closeOpenPicker();
        });
        grid.appendChild(btn);
      });
    }

    trigger.addEventListener("click", function (evt) {
      evt.stopPropagation();
      var wasOpen = openPicker && openPicker.popover === popover;
      closeOpenPicker();
      if (wasOpen) return;
      displayYear = current().year;
      renderGrid();
      popover.hidden = false;
      trigger.setAttribute("aria-expanded", "true");
      openPicker = { popover: popover, trigger: trigger };
    });

    popover.querySelectorAll(".month-picker-nav").forEach(function (nav) {
      nav.addEventListener("click", function (evt) {
        evt.stopPropagation();
        displayYear += parseInt(nav.dataset.nav, 10);
        renderGrid();
      });
    });

    updateTriggerLabel();
  });

  document.addEventListener("click", function (evt) {
    if (openPicker && !openPicker.popover.contains(evt.target)) closeOpenPicker();
  });
  document.addEventListener("keydown", function (evt) {
    if (evt.key === "Escape") closeOpenPicker();
  });

  // Preset-knoppen: vullen de maand-inputs en submitten hetzelfde
  // formulier, zodat de al aangevinkte rekeningen/categorieën/lijnen
  // behouden blijven (in tegenstelling tot een kant-en-klare <a href>
  // die de rest van het filter zou resetten).
  var form = document.getElementById("dashboard-filter");
  if (form) {
    var startInput = document.getElementById("start_month");
    var endInput = document.getElementById("end_month");
    document.querySelectorAll(".preset-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        startInput.value = btn.dataset.start;
        endInput.value = btn.dataset.end;
        form.requestSubmit();
      });
    });
  }

  // "Alles selecteren"/"Alles deselecteren" boven de categorieën- en
  // grafieklijnen-checkboxes: generic handler, now in toc_toggle.js
  // (always loaded alongside this file) since the pensioenplanner needs
  // the exact same behavior for its "Actief"-kolom. A "change" event
  // fired there is what the cascade handler right below listens for, so
  // checking/unchecking "cat_ids" in bulk still takes the subcategorieën
  // along with it.

  // Een categorie-checkbox met eigen subcategorieën (.dash-cat-checkbox,
  // data-subcat-group wijst naar het bijbehorende blokje, zie
  // app/templates/index.html) selecteert/deselecteert bij het
  // aan/uitvinken meteen al haar subcategorie-checkboxes mee — een
  // subcategorie is toch niet relevant zodra haar categorie zelf niet
  // meetelt. Werkt in één richting (categorie → subcategorieën); een
  // subcategorie apart uit-/aanvinken laat de categorie-checkbox met
  // rust.
  document.querySelectorAll(".dash-cat-checkbox").forEach(function (box) {
    var group = document.getElementById(box.dataset.subcatGroup);
    if (!group) return;
    box.addEventListener("change", function () {
      group.querySelectorAll('input[type="checkbox"]').forEach(function (sub) {
        sub.checked = box.checked;
      });
    });
  });

  // "Per categorie": elke categorie- én subcategorierij is klikbaar en
  // toont/verbergt de bijbehorende detailrij — generic handler, nu in
  // toc_toggle.js (always loaded alongside this file) sinds de
  // pensioenplanner dezelfde rij-toggle nodig heeft voor haar
  // hoofdcategorie-groepen.

  // Lijngrafiek: crosshair + één tooltip die alle zichtbare lijnen voor
  // de dichtstbijzijnde maand toont (zie de dataviz-richtlijnen: één
  // tooltip voor alle series, nooit per lijn).
  var svg = document.querySelector(".dashboard-chart");
  if (!svg) return;

  var wrap = svg.closest(".chart-wrap");
  var tooltip = wrap.querySelector(".chart-tooltip");
  var crosshair = svg.querySelector(".chart-crosshair");
  var points = Array.prototype.slice.call(svg.querySelectorAll(".chart-point"));
  var months = JSON.parse(svg.dataset.months || "[]");
  var plotX0 = parseFloat(svg.dataset.plotX0);
  var plotX1 = parseFloat(svg.dataset.plotX1);

  function svgPointFromEvent(evt) {
    var pt = svg.createSVGPoint();
    pt.x = evt.clientX;
    pt.y = evt.clientY;
    return pt.matrixTransform(svg.getScreenCTM().inverse());
  }

  function monthIndexForX(svgX) {
    if (months.length <= 1) return 0;
    var fraction = (svgX - plotX0) / (plotX1 - plotX0);
    var index = Math.round(fraction * (months.length - 1));
    return Math.max(0, Math.min(months.length - 1, index));
  }

  function xForIndex(index) {
    if (months.length <= 1) return (plotX0 + plotX1) / 2;
    return plotX0 + (index / (months.length - 1)) * (plotX1 - plotX0);
  }

  function showTooltip(index, clientX, clientY) {
    var month = months[index];
    var rows = points.filter(function (p) { return p.dataset.month === month; });
    if (!rows.length) return;

    tooltip.textContent = "";

    var monthLine = document.createElement("div");
    monthLine.className = "chart-tooltip__month";
    monthLine.textContent = month;
    tooltip.appendChild(monthLine);

    rows.forEach(function (p) {
      var row = document.createElement("div");
      row.className = "chart-tooltip__row";

      var key = document.createElement("span");
      key.className = "chart-tooltip__key";
      key.style.background = "var(" + p.dataset.colorVar + ")";

      var value = document.createElement("span");
      value.className = "chart-tooltip__value";
      value.textContent = "€ " + p.dataset.value;

      var label = document.createElement("span");
      label.className = "chart-tooltip__label";
      label.textContent = p.dataset.label;

      row.appendChild(key);
      row.appendChild(value);
      row.appendChild(label);
      tooltip.appendChild(row);
    });

    tooltip.hidden = false;
    var wrapRect = wrap.getBoundingClientRect();
    var left = clientX - wrapRect.left + 12;
    var top = clientY - wrapRect.top + 12;
    // Houd de tooltip binnen de kaart in plaats van over de rand te hangen.
    var maxLeft = wrapRect.width - tooltip.offsetWidth - 8;
    if (left > maxLeft) left = Math.max(8, clientX - wrapRect.left - tooltip.offsetWidth - 12);
    tooltip.style.left = left + "px";
    tooltip.style.top = top + "px";
  }

  function hideTooltip() {
    tooltip.hidden = true;
    crosshair.classList.remove("is-visible");
  }

  svg.addEventListener("mousemove", function (evt) {
    if (!months.length) return;
    var svgPoint = svgPointFromEvent(evt);
    var index = monthIndexForX(svgPoint.x);
    var x = xForIndex(index);
    crosshair.setAttribute("x1", x);
    crosshair.setAttribute("x2", x);
    crosshair.classList.add("is-visible");
    showTooltip(index, evt.clientX, evt.clientY);
  });

  svg.addEventListener("mouseleave", hideTooltip);
})();
