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

    // Enable swipe support
    // I have no idea why swiperRight/swiperLeft from plugins is not working, events just don't get fired
    var touchStart = 0;
    var touchEnd = 0;

    reader.rendition.on('touchstart', function(event) {
        touchStart = event.changedTouches[0].screenX;
    });
    reader.rendition.on('touchend', function(event) {
      touchEnd = event.changedTouches[0].screenX;
        if (touchStart < touchEnd) {
            if(reader.book.package.metadata.direction === "rtl") {
    			reader.rendition.next();
    		} else {
    			reader.rendition.prev();
    		}
            // Swiped Right
        }
        if (touchStart > touchEnd) {
            if(reader.book.package.metadata.direction === "rtl") {
    			reader.rendition.prev();
    		} else {
                reader.rendition.next();
    		}
            // Swiped Left
        }
    });

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

    /**
     * Fetch reading progress from the server (Kobo sync API).
     * Returns null on failure or if the URL is not configured.
     * @returns {Promise<object|null>}
     */
    function fetchServerProgress() {
        if (!calibre.readingProgressUrl) return Promise.resolve(null);
        return fetch(calibre.readingProgressUrl, { credentials: "same-origin" })
            .then(function (resp) {
                return resp.ok ? resp.json() : null;
            })
            .catch(function () { return null; });
    }

    /**
     * Push the current reading position to the server so it can be picked up
     * by a Kobo device on the next sync.  The position is stored as a CFI with
     * type "CFI" so the web reader can also restore it directly on the next load.
     *
     * Calls are debounced — the server is only hit once the reader has been
     * idle for 3 seconds, avoiding a request on every single page turn.
     *
     * @param {string} cfi            - EPUB CFI of the current position
     * @param {number} percentage     - Whole-book progress percentage 0–100
     * @param {string} chapterHref    - Href of the current spine item (chapter)
     * @param {number} inChapterPct   - Progress percentage within the current chapter 0–100
     * @param {string} position_key   - localStorage key for storing the server timestamp
     */
    var _syncTimer = null;
    function syncProgressToServer(cfi, percentage, chapterHref, inChapterPct, position_key) {
        if (!calibre.readingProgressUrl) return;
        clearTimeout(_syncTimer);
        _syncTimer = setTimeout(function () {
            fetch(calibre.readingProgressUrl, {
                method: "PUT",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    status: "Reading",
                    progress_percent: percentage,
                    content_source_progress_percent: inChapterPct,
                    location: {
                        // Store the CFI so browser-to-browser restore is exact.
                        // Source (chapter href) lets the Kobo open the correct
                        // chapter when it can't interpret the CFI value directly.
                        value: cfi,
                        type: "CFI",
                        source: chapterHref
                    }
                })
            })
            .then(function (resp) { return resp.ok ? resp.json() : null; })
            .then(function (data) {
                // Record the server timestamp so we can compare freshness on the
                // next load and avoid overwriting a more-recent Kobo position with
                // a stale browser position.
                if (data && data.last_modified) {
                    try {
                        var posStr = localStorage.getItem(position_key);
                        var pos = posStr ? JSON.parse(posStr) : {};
                        pos.serverTimestamp = new Date(data.last_modified).getTime();
                        localStorage.setItem(position_key, JSON.stringify(pos));
                    } catch (e) {}
                }
            })
            .catch(function () {});
        }, 3000);
    }

    reader.book.ready.then(async () => {
        let locations_key = reader.book.key() + "-locations";
        // Key to persist last-read position for this book in localStorage
        let position_key = "calibre.reader.position." + reader.book.key();
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

        await make_locations;

        // --- Position restoration (server vs. localStorage) ---
        //
        // We prefer whichever source has the most recent update.  The localStorage
        // position object stores a `serverTimestamp` (ms since epoch) set after
        // each successful server sync so the two clocks can be compared.
        //
        // Priority rules:
        //   1. If the server has a position and its last_modified is newer than
        //      the last time the browser synced with the server → use server position.
        //   2. For server positions stored by this web reader (type "CFI"), navigate
        //      directly to the CFI.
        //   3. For server positions stored by a Kobo device (type "KoboSpan"), use
        //      progress_percent to seek to the approximate position since the web
        //      reader cannot interpret KoboSpan identifiers directly.
        //   4. Fall back to the CFI stored in localStorage (pre-existing behaviour).

        var serverProgress = await fetchServerProgress();
        var navigated = false;

        if (serverProgress && serverProgress.last_modified) {
            var serverTime = new Date(serverProgress.last_modified).getTime();
            var localServerTime = 0;
            try {
                var _savedPos = localStorage.getItem(position_key);
                if (_savedPos) {
                    var _p = JSON.parse(_savedPos);
                    localServerTime = _p.serverTimestamp || 0;
                }
            } catch (e) {}

            if (serverTime > localServerTime) {
                // Server has a position that is newer than what the browser last
                // synced — restore from server.
                var loc = serverProgress.location;
                try {
                    if (loc && loc.type === "CFI" && loc.value) {
                        // Exact CFI from a previous browser session.
                        reader.rendition.display(loc.value);
                        navigated = true;
                    } else if (serverProgress.progress_percent != null) {
                        // KoboSpan position or percentage-only update from a Kobo
                        // device: jump to the nearest CFI for that percentage.
                        var targetCfi = reader.book.locations.cfiFromPercentage(
                            serverProgress.progress_percent / 100
                        );
                        if (targetCfi) {
                            reader.rendition.display(targetCfi);
                            navigated = true;
                        }
                    }
                } catch (e) {}
            }
        }

        if (!navigated) {
            // Fall back to localStorage position (pre-existing behaviour).
            try {
                var _savedPos = localStorage.getItem(position_key);
                if (_savedPos) {
                    try {
                        var _posObj = JSON.parse(_savedPos);
                        if (_posObj && _posObj.cfi) {
                            try {
                                reader.rendition.display(_posObj.cfi);
                            } catch (e) {}
                        }
                    } catch (e) {}
                }
            } catch (e) {}
        }

        reader.rendition.on("relocated", (location) => {
            let percentage = Math.round(location.end.percentage * 100);
            progressDiv.textContent = percentage + "%";

            // Pages based on generated EPUB locations (CFI positions)
            const cfi = location.start.cfi;
            const current =
                reader.book.locations.locationFromCfi(cfi) || 0; // 1-based index typically
            const total = reader.book.locations.length() || 0;

            if (total > 0) {
                pagesDiv.textContent = current + "/" + total;
                pagesDiv.style.visibility = "visible";
            } else {
                pagesDiv.textContent = "";
                pagesDiv.style.visibility = "hidden";
            }

            // Persist last position (CFI + percentage) to localStorage so reader
            // can restore on next open even without a server round-trip.
            try {
                var posStr = localStorage.getItem(position_key);
                var posObj = posStr ? JSON.parse(posStr) : {};
                posObj.cfi = location.start.cfi;
                posObj.percentage = location.start.percentage;
                localStorage.setItem(position_key, JSON.stringify(posObj));
            } catch (e) {}

            // Sync to server (debounced) so the position is visible to the Kobo
            // device on its next sync.
            //
            // chapterHref: spine item href — lets the Kobo open the right chapter.
            // inChapterPct: position within the chapter — lets the Kobo seek within it.
            var chapterHref = (location.start && location.start.href) || "";
            if (!chapterHref) {
                try {
                    var _sec = reader.book.spine.get(location.start.cfi);
                    chapterHref = _sec ? (_sec.href || "") : "";
                } catch (e) {}
            }
            var inChapterPct = Math.round(location.start.percentage * 100); // fallback
            try {
                var disp = location.start.displayed;
                if (disp && disp.total > 0) {
                    inChapterPct = Math.round((disp.page / disp.total) * 100);
                }
            } catch (e) {}
            syncProgressToServer(
                location.start.cfi,
                Math.round(location.start.percentage * 100),
                chapterHref,
                inChapterPct,
                position_key
            );
        });
        reader.rendition.reportLocation();
        progressDiv.style.visibility = "visible";

        save_locations();
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