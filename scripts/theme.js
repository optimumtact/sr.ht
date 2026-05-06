(function () {
  var STORAGE_KEY = "srht.theme";
  var TOGGLE_SELECTOR = "[data-theme-toggle]";
  var prefersDark = window.matchMedia("(prefers-color-scheme: dark)");
  var ICON_MOON = '<svg aria-hidden="true" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>';
  var ICON_SUN = '<svg aria-hidden="true" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"></circle><line x1="12" y1="2" x2="12" y2="4"></line><line x1="12" y1="20" x2="12" y2="22"></line><line x1="4.93" y1="4.93" x2="6.34" y2="6.34"></line><line x1="17.66" y1="17.66" x2="19.07" y2="19.07"></line><line x1="2" y1="12" x2="4" y2="12"></line><line x1="20" y1="12" x2="22" y2="12"></line><line x1="4.93" y1="19.07" x2="6.34" y2="17.66"></line><line x1="17.66" y1="6.34" x2="19.07" y2="4.93"></line></svg>';

  function getStoredTheme() {
    var stored = window.localStorage.getItem(STORAGE_KEY);
    return stored === "dark" || stored === "light" ? stored : null;
  }

  function getSystemTheme() {
    return prefersDark.matches ? "dark" : "light";
  }

  function getResolvedTheme() {
    return getStoredTheme() || getSystemTheme();
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    document.documentElement.style.colorScheme = theme;
    updateThemeToggle(theme);
  }

  function updateThemeToggle(theme) {
    var nextTheme = theme === "dark" ? "light" : "dark";
    var buttons = document.querySelectorAll(TOGGLE_SELECTOR);

    buttons.forEach(function (button) {
      button.innerHTML = nextTheme === "dark" ? ICON_MOON : ICON_SUN;
      button.setAttribute("aria-label", "Switch to " + nextTheme + " mode");
      button.setAttribute("title", "Switch to " + nextTheme + " mode");
      button.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
    });
  }

  function bindThemeToggles(root) {
    var scope = root && root.querySelectorAll ? root : document;
    var buttons = scope.querySelectorAll(TOGGLE_SELECTOR);

    buttons.forEach(function (button) {
      if (button.dataset.bound === "1") {
        return;
      }

      button.addEventListener("click", function () {
        var currentTheme = getResolvedTheme();
        var nextTheme = currentTheme === "dark" ? "light" : "dark";
        window.localStorage.setItem(STORAGE_KEY, nextTheme);
        applyTheme(nextTheme);
      });

      button.dataset.bound = "1";
    });

    updateThemeToggle(getResolvedTheme());
  }

  function handleSystemThemeChange() {
    if (!getStoredTheme()) {
      applyTheme(getSystemTheme());
    }
  }

  if (typeof prefersDark.addEventListener === "function") {
    prefersDark.addEventListener("change", handleSystemThemeChange);
  } else if (typeof prefersDark.addListener === "function") {
    prefersDark.addListener(handleSystemThemeChange);
  }

  applyTheme(getResolvedTheme());

  document.addEventListener("DOMContentLoaded", function () {
    bindThemeToggles(document);
  });

  document.body.addEventListener("htmx:load", function (event) {
    bindThemeToggles(event.target || document);
  });
})();
