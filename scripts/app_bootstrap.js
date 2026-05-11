(function () {
    function initBootstrapValues() {
        var body = document.body;
        if (!body) {
            return false;
        }

        var apiKey = "";
        var root = "";

        if (body.dataset) {
            apiKey = body.dataset.apiKey || "";
            root = body.dataset.root || "";
        }

        if (!root) {
            root = window.location.origin;
        }

        window.api_key = apiKey;
        window.root = root;
        return true;
    }

    if (!initBootstrapValues()) {
        document.addEventListener("DOMContentLoaded", initBootstrapValues, { once: true });
    }
})();