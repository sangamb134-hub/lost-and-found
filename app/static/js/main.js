/* Campus Lost & Found — front-end interactions */
(function () {
    "use strict";

    // Auto-dismiss flash messages after 6 seconds
    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll(".alert-dismissible").forEach(function (alert) {
            setTimeout(function () {
                var bsAlert = bootstrap.Alert.getInstance(alert);
                if (bsAlert) {
                    bsAlert.close();
                }
            }, 6000);
        });
    });

    // Live stats refresh on home page (optional enhancement)
    var statsEndpoint = document.body.getAttribute("data-stats-endpoint");
    if (statsEndpoint) {
        fetch(statsEndpoint)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                var set = function (id, val) {
                    var el = document.getElementById(id);
                    if (el) { el.textContent = val; }
                };
                set("stat-lost", data.total_lost);
                set("stat-found", data.total_found);
                set("stat-returned", data.returned);
            })
            .catch(function () { /* silent fail — static values remain */ });
    }

    // Confirm any destructive action via data-confirm attribute
    document.addEventListener("click", function (e) {
        var el = e.target.closest("[data-confirm]");
        if (!el) { return; }
        if (!window.confirm(el.getAttribute("data-confirm"))) {
            e.preventDefault();
        }
    });
})();
