(function () {
  "use strict";

  function applyStandardAutoTheme() {
    var prefersDark = false;

    if (window.matchMedia) {
      prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    }

    document.body.classList.toggle("standard-dark", prefersDark);
  }

  function initStandardAutoTheme() {
    applyStandardAutoTheme();

    if (window.matchMedia) {
      var mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
      if (typeof mediaQuery.addEventListener === "function") {
        mediaQuery.addEventListener("change", applyStandardAutoTheme);
      } else if (typeof mediaQuery.addListener === "function") {
        mediaQuery.addListener(applyStandardAutoTheme);
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initStandardAutoTheme);
  } else {
    initStandardAutoTheme();
  }
})();
