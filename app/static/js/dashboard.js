(function () {
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
  // grafieklijnen-checkboxes (data-check-group is de checkbox-naam, dus
  // dit werkt voor elke checkbox-groep die zo'n knoppenpaar krijgt) — zet
  // alleen de checkboxen zelf om, submit niets: de gebruiker klikt zelf
  // nog op "Filteren" zodra de selectie klopt. Een "change"-event erna
  // laat de cascade-handler hieronder meteen ook de bijbehorende
  // subcategorieën meenemen wanneer dit de cat_ids-groep is (op andere
  // groepen, zoals graph_lines, luistert niets naar dat event — die doen
  // dus gewoon niets extra).
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

  // "Per categorie": elke categorierij is klikbaar (en met Enter/Spatie
  // bedienbaar, vandaar tabindex + role="button" in index.html) en
  // toont/verbergt de bijbehorende detailrij met onderliggende
  // statements — beide rijen zijn al server-side gerenderd, dit
  // schakelt alleen het `hidden`-attribuut om. Losstaand van de
  // grafiekcode hieronder, die stopt (return) als er geen grafiek is.
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
