(function () {
  var STORAGE_KEY = "srht.uploads.filtersCollapsed";

  function applyFiltersPanelState() {
    var panel = document.getElementById("uploads-filters-panel");
    var toggle = document.getElementById("uploads-filters-toggle");
    if (!panel || !toggle) {
      return;
    }

    var collapsed = window.localStorage.getItem(STORAGE_KEY) === "1";
    panel.classList.toggle("hidden", collapsed);
    toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
    toggle.textContent = collapsed ? "Show filters" : "Hide filters";

    if (toggle.dataset.bound === "1") {
      return;
    }

    toggle.addEventListener("click", function () {
      var isCollapsed = panel.classList.toggle("hidden");
      toggle.setAttribute("aria-expanded", isCollapsed ? "false" : "true");
      toggle.textContent = isCollapsed ? "Show filters" : "Hide filters";
      window.localStorage.setItem(STORAGE_KEY, isCollapsed ? "1" : "0");
    });

    toggle.dataset.bound = "1";
  }

  document.addEventListener("DOMContentLoaded", applyFiltersPanelState);
  document.body.addEventListener("htmx:afterSwap", applyFiltersPanelState);
  document.body.addEventListener("htmx:load", applyFiltersPanelState);
})();
