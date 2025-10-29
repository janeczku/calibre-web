/* global $, calibre, EPUBJS, ePubReader */

var reader;

(function () {
    "use strict";

    EPUBJS.filePath = calibre.filePath;
    EPUBJS.cssPath = calibre.cssPath;

    reader = ePubReader(calibre.bookUrl, {
        restore: true,
        bookmarks: calibre.bookmark ? [calibre.bookmark] : [],
    });

    Object.keys(themes).forEach(function (theme) {
        reader.rendition.themes.register(theme, themes[theme].css_path);
    });

    if (calibre.useBookmarks) {
        reader.on("reader:bookmarked", updateBookmark.bind(reader, "add"));
        reader.on("reader:unbookmarked", updateBookmark.bind(reader, "remove"));
    } else {
        $("#bookmark, #show-Bookmarks").remove();
    }

    // Navigation mode: 'sides' or 'gestures'
    var hammerManagers = [];

    function hasActiveSelection(win) {
        try {
            var sel = win.getSelection && win.getSelection();
            return sel && sel.type === "Range" && sel.toString().length > 0;
        } catch (e) {
            return false;
        }
    }

    function bindHammer(target, isIframeDoc) {
        if (typeof Hammer === "undefined") {
            return;
        }
        var mc = new Hammer(target);
        mc.get("swipe").set({
            direction: Hammer.DIRECTION_HORIZONTAL,
            threshold: 25,
            velocity: 0.3,
        });
        mc.on("swipeleft swiperight", function (ev) {
            if (!window.cwGesturesEnabled) return;
            if (ev.pointers && ev.pointers.length > 1) return; // ignore multi-touch
            var win = isIframeDoc ? target.defaultView : window;
            if (hasActiveSelection(win)) return; // do not navigate when selecting text
            // Mapping per requirement: L->R = PREV, R->L = NEXT (independent of RTL)
            if (ev.type === "swipeleft") reader.rendition.next();
            else reader.rendition.prev();
        });
        hammerManagers.push(mc);
    }

    function destroyHammers() {
        while (hammerManagers.length) {
            var mc = hammerManagers.pop();
            try {
                mc.destroy();
            } catch (e) {}
        }
    }

    function enableSideClicks() {
        var prevBtn = document.getElementById("prev");
        var nextBtn = document.getElementById("next");
        if (prevBtn) {
            prevBtn.style.display = "";
            prevBtn.onclick = function () {
                reader.rendition.prev();
            };
        }
        if (nextBtn) {
            nextBtn.style.display = "";
            nextBtn.onclick = function () {
                reader.rendition.next();
            };
        }
    }

    function disableSideClicks() {
        var prevBtn = document.getElementById("prev");
        var nextBtn = document.getElementById("next");
        if (prevBtn) {
            prevBtn.onclick = null;
            prevBtn.style.display = "none";
        }
        if (nextBtn) {
            nextBtn.onclick = null;
            nextBtn.style.display = "none";
        }
    }

    function enableGestures() {
        // Bind to outer container
        if (reader && reader.rendition && reader.rendition.container) {
            bindHammer(reader.rendition.container, false);
        }
        // Bind swipe on sidebar to close/open main
        try {
            var sidebarEl = document.getElementById("tocView");
            if (sidebarEl && typeof Hammer !== "undefined") {
                var sidebarMc = new Hammer(sidebarEl);
                sidebarMc.get("swipe").set({
                    direction: Hammer.DIRECTION_HORIZONTAL,
                    threshold: 25,
                    velocity: 0.3,
                });
                sidebarMc.on("swipeleft swiperight", function (ev) {
                    if ($("#sidebar").hasClass("open")) {
                        $("#slider").click();
                    }
                });
                hammerManagers.push(sidebarMc);
            }
        } catch (e) {}
        // Bind to inner iframes when rendered
        reader.rendition.on("rendered", function (section, contents) {
            var docEl = contents.document;
            if (docEl && docEl.documentElement && docEl.documentElement.style) {
                docEl.documentElement.style.touchAction = "pan-y";
            }
            bindHammer(docEl, true);
        });
    }

    window.applyNavigationMode = function (mode) {
        if (!window.cwInitialized) {
            destroyHammers();
            enableGestures();
            window.cwInitialized = true;
        }

        if (mode === "sides") {
            enableSideClicks();
            window.cwGesturesEnabled = false;
        } else {
            disableSideClicks();
            window.cwGesturesEnabled = true;
        }
    };

    // Apply saved or default mode on load
    var savedMode = localStorage.getItem("calibre.reader.navMode") || "sizes";
    window.applyNavigationMode(savedMode);

    // Update progress percentage
    let progressDiv = document.getElementById("progress");
    // Pages counter (virtual pages via EPUB locations)
    let pagesDiv = document.getElementById("pages-count");
    // Honor saved visibility preference for pages counter
    (function () {
        try {
            var pref = localStorage.getItem("calibre.reader.showPages");
            var show = pref === null ? true : pref === "true";
            if (pagesDiv)
                pagesDiv.style.visibility = show ? "visible" : "hidden";
        } catch (e) {}
    })();

    reader.book.ready.then(() => {
        let locations_key = reader.book.key() + "-locations";
        let stored_locations = localStorage.getItem(locations_key);
        let make_locations, save_locations;
        if (stored_locations) {
            make_locations = Promise.resolve(
                reader.book.locations.load(stored_locations)
            );
            // No-op because locations are already saved
            save_locations = () => {};
        } else {
            make_locations = reader.book.locations.generate();
            save_locations = () => {
                localStorage.setItem(
                    locations_key,
                    reader.book.locations.save()
                );
            };
        }
        make_locations
            .then(() => {
                reader.rendition.on("relocated", (location) => {
                    let percentage = Math.round(location.end.percentage * 100);
                    progressDiv.textContent = percentage + "%";

                    // Pages based on generated EPUB locations (CFI positions)
                    const cfi = location.start.cfi;
                    const current =
                        reader.book.locations.locationFromCfi(cfi) || 0; // 1-based index typically
                    const total = reader.book.locations.length() || 0;
                    const remaining = Math.max(total - current, 0);

                    if (total > 0) {
                        pagesDiv.textContent = current + "/" + total;
                        pagesDiv.style.visibility = "visible";
                    } else {
                        pagesDiv.textContent = "";
                        pagesDiv.style.visibility = "hidden";
                    }
                });
                reader.rendition.reportLocation();
                progressDiv.style.visibility = "visible";
            })
            .then(save_locations);
    });

    /**
     * @param {string} action - Add or remove bookmark
     * @param {string|int} location - Location or zero
     */
    function updateBookmark(action, location) {
        // Remove other bookmarks (there can only be one)
        if (action === "add") {
            this.settings.bookmarks
                .filter(function (bookmark) {
                    return bookmark && bookmark !== location;
                })
                .map(
                    function (bookmark) {
                        this.removeBookmark(bookmark);
                    }.bind(this)
                );
        }

        var csrftoken = $("input[name='csrf_token']").val();

        // Save to database
        $.ajax(calibre.bookmarkUrl, {
            method: "post",
            data: { bookmark: location || "" },
            headers: { "X-CSRFToken": csrftoken },
        }).fail(function (xhr, status, error) {
            alert(error);
        });
    }

    // Default settings load
    const theme = localStorage.getItem("calibre.reader.theme") ?? "lightTheme";
    selectTheme(theme);

    // Restore saved font and font size after reader is ready
    reader.book.ready.then(() => {
        const savedFontSize = localStorage.getItem("calibre.reader.fontSize");
        if (savedFontSize) {
            reader.rendition.themes.fontSize(`${savedFontSize}%`);
        }

        const savedFont = localStorage.getItem("calibre.reader.font");
        if (savedFont && window.selectFont) {
            window.selectFont(savedFont);
        }
    });
})();
