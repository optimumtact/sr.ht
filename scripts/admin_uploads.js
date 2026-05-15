(function () {
  var STORAGE_KEY = "srht.adminUploads.filtersCollapsed";

  function bindAdminUploadModals() {
    document.querySelectorAll("[data-modal-open]").forEach(function (button) {
      if (button.dataset.modalBound === "1") {
        return;
      }

      button.addEventListener("click", function () {
        var targetId = button.getAttribute("data-modal-open");
        if (!targetId) {
          return;
        }
        var dialog = document.getElementById(targetId);
        if (dialog && dialog.showModal) {
          dialog.showModal();
        }
      });

      button.dataset.modalBound = "1";
    });

    document.querySelectorAll("[data-modal-close]").forEach(function (button) {
      if (button.dataset.modalBound === "1") {
        return;
      }

      button.addEventListener("click", function () {
        var targetId = button.getAttribute("data-modal-close");
        if (!targetId) {
          return;
        }
        var dialog = document.getElementById(targetId);
        if (dialog && dialog.close) {
          dialog.close();
        }
      });

      button.dataset.modalBound = "1";
    });

    document.querySelectorAll("dialog[data-modal]").forEach(function (dialog) {
      if (dialog.dataset.modalBound === "1") {
        return;
      }

      dialog.addEventListener("click", function (event) {
        if (event.target === dialog && dialog.close) {
          dialog.close();
        }
      });

      dialog.dataset.modalBound = "1";
    });
  }

  function applyFiltersPanelState() {
    var panel = document.getElementById("admin-uploads-filters-panel");
    var toggle = document.getElementById("admin-uploads-filters-toggle");
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

  function initializeAdminUploadsUI() {
    applyFiltersPanelState();
    bindAdminUploadModals();
  }

  document.addEventListener("DOMContentLoaded", initializeAdminUploadsUI);
  document.body.addEventListener("htmx:afterSwap", initializeAdminUploadsUI);
  document.body.addEventListener("htmx:load", initializeAdminUploadsUI);
})();
