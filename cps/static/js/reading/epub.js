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

    function fetchServerProgress() {
        if (!calibre.readingProgressUrl) return Promise.resolve(null);
        return fetch(calibre.readingProgressUrl, { credentials: "same-origin" })
            .then(function (resp) {
                return resp.ok ? resp.json() : null;
            })
            .catch(function () { return null; });
    }

    // Extract the nearest Kobo span ID (e.g. "kobo.2.1") from a CFI string.
    // EPUB.js encodes element IDs in CFI step assertions, so we can usually parse
    // the ID directly from the CFI without touching the DOM.  Falls back to DOM
    // traversal for cases where no kobo step assertion is present.
    // Returns a Promise resolving to the span ID, or null for plain EPUBs.
    function extractKoboSpanFromCfi(cfi) {
        try {
            var stepPattern = /\[([^\]]+)\]/g;
            var match, lastKoboId = null;
            var localPath = cfi.indexOf("!") !== -1 ? cfi.slice(cfi.indexOf("!")) : cfi;
            while ((match = stepPattern.exec(localPath)) !== null) {
                if (match[1].startsWith("kobo.")) lastKoboId = match[1];
            }
            if (lastKoboId) return Promise.resolve(lastKoboId);
        } catch (e) {}

        try {
            var rangeResult = reader.rendition.getRange(cfi);
            var p = (rangeResult && typeof rangeResult.then === "function")
                ? rangeResult
                : Promise.resolve(rangeResult);
            return p.then(function (range) {
                if (!range) return null;
                var node = range.startContainer;
                var el = (node.nodeType === Node.TEXT_NODE) ? node.parentElement : node;
                while (el) {
                    if (el.id && el.id.startsWith("kobo.")) return el.id;
                    el = el.parentElement;
                }
                var doc = node.ownerDocument;
                if (!doc) return null;
                var walker = doc.createTreeWalker(doc.body, NodeFilter.SHOW_ELEMENT, {
                    acceptNode: function (n) {
                        return (n.id && n.id.startsWith("kobo."))
                            ? NodeFilter.FILTER_ACCEPT
                            : NodeFilter.FILTER_SKIP;
                    }
                }, false);
                var startEl = (node.nodeType === Node.TEXT_NODE) ? node.parentElement : node;
                var lastSpan = null, n;
                while ((n = walker.nextNode())) {
                    if (startEl.compareDocumentPosition(n) & Node.DOCUMENT_POSITION_FOLLOWING) break;
                    lastSpan = n;
                }
                return lastSpan ? lastSpan.id : null;
            }).catch(function () { return null; });
        } catch (e) {
            return Promise.resolve(null);
        }
    }

    // Debounced sync of the current position to the server.
    // For KEPUBs a kobo span ID is sent (type "KoboSpan"); for plain EPUBs a CFI
    // string is sent (type "CFI").  Fires 3 s after the last page turn.
    var _syncTimer = null;
    function syncProgressToServer(cfi, percentage, chapterHref, inChapterPct, position_key, koboSpanId) {
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
                    location: koboSpanId ? {
                        value: "#" + koboSpanId,
                        type: "KoboSpan",
                        source: chapterHref
                    } : {
                        value: cfi,
                        type: "CFI",
                        source: chapterHref
                    }
                })
            })
            .then(function (resp) { return resp.ok ? resp.json() : null; })
            .then(function (data) {
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

        var serverProgress = await fetchServerProgress();
        var navigated = false;

        if (serverProgress && serverProgress.last_modified) {
            var serverTime = new Date(serverProgress.last_modified).getTime();
            var localServerTime = 0;
            try {
                var savedPos = localStorage.getItem(position_key);
                if (savedPos) {
                    var savedPosObj = JSON.parse(savedPos);
                    localServerTime = savedPosObj.serverTimestamp || 0;
                }
            } catch (e) {}

            // Use the server position if it is newer than the last browser sync
            if (serverTime > localServerTime) {
                var loc = serverProgress.location;
                try {
                    if (loc && loc.type === "CFI" && loc.value) {
                        reader.rendition.display(loc.value);
                        navigated = true;
                    } else if (loc && loc.type === "KoboSpan" && loc.value && loc.source) {
                        // Extract the fragment ID from the span value, which may be a
                        // bare "#kobo.N.M" (stored by the browser) or a full Kobo device
                        // URI ending in "#kobo.N.M"
                        var hashIdx = loc.value.lastIndexOf("#");
                        var fragmentId = hashIdx !== -1 ? loc.value.slice(hashIdx + 1) : null;
                        var spanSource = loc.source;
                        if (!spanSource && hashIdx !== -1) {
                            var excl = loc.value.indexOf("!");
                            if (excl !== -1) spanSource = loc.value.slice(excl + 1, hashIdx);
                        }
                        if (fragmentId && spanSource) {
                            reader.rendition.display(spanSource + "#" + fragmentId);
                            navigated = true;
                        } else if (serverProgress.progress_percent != null) {
                            var targetCfi = reader.book.locations.cfiFromPercentage(
                                serverProgress.progress_percent / 100
                            );
                            if (targetCfi) { reader.rendition.display(targetCfi); navigated = true; }
                        }
                    } else if (serverProgress.progress_percent != null) {
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
            // Fall back to localStorage position
            try {
                var localPos = localStorage.getItem(position_key);
                if (localPos) {
                    try {
                        var localPosObj = JSON.parse(localPos);
                        if (localPosObj && localPosObj.cfi) {
                            try {
                                reader.rendition.display(localPosObj.cfi);
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

            // Persist last position to localStorage
            try {
                var posStr = localStorage.getItem(position_key);
                var posObj = posStr ? JSON.parse(posStr) : {};
                posObj.cfi = location.start.cfi;
                posObj.percentage = location.start.percentage;
                localStorage.setItem(position_key, JSON.stringify(posObj));
            } catch (e) {}

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
            extractKoboSpanFromCfi(location.start.cfi).then(function (koboSpanId) {
                syncProgressToServer(
                    location.start.cfi,
                    Math.round(location.start.percentage * 100),
                    chapterHref,
                    inChapterPct,
                    position_key,
                    koboSpanId
                );
            });
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