(function () {
    try {
        var storageKey = "srht.theme";
        var storedTheme = window.localStorage.getItem(storageKey);
        var theme = storedTheme === "dark" || storedTheme === "light"
            ? storedTheme
            : (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
        document.documentElement.setAttribute("data-theme", theme);
        document.documentElement.style.colorScheme = theme;
    } catch (error) {
        document.documentElement.setAttribute("data-theme", "light");
        document.documentElement.style.colorScheme = "light";
    }
})();
