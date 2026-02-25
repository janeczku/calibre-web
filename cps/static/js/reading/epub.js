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

    reader.book.ready.then(() => {
        let locations_key = reader.book.key() + "-locations";
        // Key to persist last-read position for this book in localStorage
        let position_key = "calibre.reader.position." + reader.book.key();
        
        let progressSyncTimeout = null;
        let lastSyncedCfi = null;
        // Flag to suppress sync immediately after restore (prevents overwriting server with reflow-adjusted position)
        let justRestored = false;
        let justRestoredTimeout = null;
        // Track if locations are ready for page count display
        let locationsReady = false;

        function isProgressEnabled() {
            return calibre.useProgress === true || calibre.useProgress === "true";
        }

        function showSyncToast(message, type) {
            var toast = document.createElement("div");
            toast.className = "sync-toast sync-toast-" + (type || "info");
            toast.textContent = message;
            toast.style.cssText = "position:fixed;top:10px;left:50%;transform:translateX(-50%);padding:8px 16px;border-radius:4px;z-index:9999;font-size:14px;opacity:0.95;transition:opacity 0.3s;";
            if (type === "success") {
                toast.style.background = "#4CAF50";
                toast.style.color = "white";
            } else if (type === "info") {
                toast.style.background = "#2196F3";
                toast.style.color = "white";
            } else {
                toast.style.background = "#333";
                toast.style.color = "white";
            }
            document.body.appendChild(toast);
            setTimeout(function() {
                toast.style.opacity = "0";
                setTimeout(function() { toast.remove(); }, 300);
            }, 3000);
        }

        function debugLog(label, data) {
            console.log("[EPUB Sync] " + label, data);
        }

        // Start loading/generating locations in the background (for page count display)
        let stored_locations = localStorage.getItem(locations_key);
        let locationsPromise;
        if (stored_locations) {
            locationsPromise = Promise.resolve(reader.book.locations.load(stored_locations));
        } else {
            locationsPromise = reader.book.locations.generate().then(() => {
                localStorage.setItem(locations_key, reader.book.locations.save());
            });
        }
        locationsPromise.then(() => {
            locationsReady = true;
            debugLog("Locations ready");
        });

        // Restore position IMMEDIATELY - don't wait for locations
        function restorePosition() {
            return new Promise((resolve) => {
                let localPos = null;
                try {
                    var _savedPos = localStorage.getItem(position_key);
                    if (_savedPos) {
                        localPos = JSON.parse(_savedPos);
                    }
                } catch (e) {}

                debugLog("Local position", localPos);

                function displayCfi(cfi) {
                    if (!cfi) return false;
                    try {
                        debugLog("Displaying CFI", cfi);
                        let p = reader.rendition.display(cfi);
                        if (p && typeof p.catch === "function") {
                            p.catch(function () {});
                        }
                        return true;
                    } catch (e) {
                        debugLog("CFI display failed", e);
                        return false;
                    }
                }

                function displayLocal() {
                    if (localPos && localPos.cfi) {
                        displayCfi(localPos.cfi);
                    }
                }

                if (!isProgressEnabled() || !calibre.progressUrl) {
                    debugLog("Progress sync disabled or no URL", { useProgress: calibre.useProgress, progressUrl: calibre.progressUrl });
                    displayLocal();
                    resolve();
                    return;
                }

                debugLog("Fetching remote progress from", calibre.progressUrl);
                $.ajax(calibre.progressUrl, { method: "get" })
                    .done(function (remote) {
                        debugLog("Remote progress response", remote);
                        let usedRemote = false;
                        if (
                            remote &&
                            remote.location_type === "epub-cfi" &&
                            remote.location
                        ) {
                            let remoteTs = 0;
                            try {
                                remoteTs = Date.parse(remote.last_modified || "") || 0;
                            } catch (e) {
                                remoteTs = 0;
                            }
                            let localTs = localPos && localPos.ts ? localPos.ts : 0;

                            debugLog("Timestamp comparison", {
                                remoteTs: remoteTs,
                                remoteTsDate: new Date(remoteTs).toISOString(),
                                localTs: localTs,
                                localTsDate: localTs ? new Date(localTs).toISOString() : null,
                                remoteNewer: remoteTs > localTs
                            });

                            if (!localPos || !localPos.cfi || remoteTs > localTs) {
                                let remotePercentage =
                                    remote.data && remote.data.percentage != null
                                        ? remote.data.percentage
                                        : localPos && localPos.percentage != null
                                        ? localPos.percentage
                                        : null;
                                debugLog("Using REMOTE position", {
                                    cfi: remote.location,
                                    percentage: remotePercentage,
                                    progressPercent: remote.progress_percent
                                });
                                showSyncToast("Restored from server: " + (remote.progress_percent || Math.round((remotePercentage || 0) * 100)) + "%", "success");
                                
                                // Set flag to prevent immediate re-sync after restore
                                justRestored = true;
                                if (justRestoredTimeout) clearTimeout(justRestoredTimeout);
                                justRestoredTimeout = setTimeout(function() {
                                    justRestored = false;
                                    debugLog("Restore cooldown ended, sync enabled");
                                }, 5000);
                                
                                displayCfi(remote.location);
                                usedRemote = true;
                                try {
                                    localStorage.setItem(
                                        position_key,
                                        JSON.stringify({
                                            cfi: remote.location,
                                            percentage: remotePercentage,
                                            ts: remoteTs || Date.now(),
                                        })
                                    );
                                } catch (e) {}
                            } else {
                                debugLog("Using LOCAL position (local is newer)", {
                                    localCfi: localPos.cfi,
                                    localPercentage: localPos.percentage
                                });
                                showSyncToast("Using local position: " + Math.round((localPos.percentage || 0) * 100) + "%", "info");
                            }
                        } else {
                            debugLog("No valid remote position, using local", remote);
                        }

                        if (!usedRemote) {
                            displayLocal();
                        }
                        resolve();
                    })
                    .fail(function (xhr, status, error) {
                        debugLog("Failed to fetch remote progress", { status: status, error: error, xhr: xhr.status });
                        displayLocal();
                        resolve();
                    });
            });
        }

        // Restore position immediately (don't wait for locations)
        restorePosition().then(() => {
            reader.rendition.on("relocated", (location) => {
                let percentage = Math.round(location.end.percentage * 100);
                progressDiv.textContent = percentage + "%";

                // Pages based on generated EPUB locations (only show if locations are ready)
                const cfi = location.start.cfi;
                if (locationsReady) {
                    const current = reader.book.locations.locationFromCfi(cfi) || 0;
                    const total = reader.book.locations.length() || 0;
                    if (total > 0) {
                        pagesDiv.textContent = current + "/" + total;
                        pagesDiv.style.visibility = "visible";
                    }
                }

                // Skip saving if we just restored from server
                if (justRestored) {
                    debugLog("Skipping save (just restored from server)", { cfi: cfi, percentage: percentage });
                    return;
                }

                // Persist last position to localStorage
                try {
                    var posObj = {
                        cfi: location.start.cfi,
                        percentage: location.start.percentage,
                        ts: Date.now(),
                    };
                    localStorage.setItem(position_key, JSON.stringify(posObj));
                } catch (e) {}

                if (isProgressEnabled() && calibre.progressUrl && cfi) {
                    if (progressSyncTimeout) {
                        clearTimeout(progressSyncTimeout);
                    }
                    progressSyncTimeout = setTimeout(() => {
                        if (cfi === lastSyncedCfi) {
                            return;
                        }
                        lastSyncedCfi = cfi;

                        debugLog("Syncing position to server", { cfi: cfi, percentage: percentage });

                        var csrftoken = $("input[name='csrf_token']").val();
                        $.ajax(calibre.progressUrl, {
                            method: "post",
                            data: {
                                location_type: "epub-cfi",
                                location: cfi,
                                progress_percent: percentage,
                                data: JSON.stringify({
                                    percentage: location.start.percentage,
                                }),
                            },
                            headers: { "X-CSRFToken": csrftoken },
                        }).done(function() {
                            debugLog("Position synced successfully", { cfi: cfi });
                        }).fail(function (xhr, status, error) {
                            console.error("[EPUB Sync] Failed to sync:", error);
                        });
                    }, 2000);
                }
            });
            reader.rendition.reportLocation();
            progressDiv.style.visibility = "visible";
        });
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
