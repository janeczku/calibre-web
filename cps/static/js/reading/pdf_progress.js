(function () {
    "use strict";

    function debugLog(label, data) {
        console.log("[PDF Sync] " + label, data);
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

    function isProgressEnabled() {
        return (
            window.calibre &&
            (window.calibre.useProgress === true ||
                window.calibre.useProgress === "true")
        );
    }

    debugLog("Initializing", { calibre: window.calibre, enabled: isProgressEnabled() });

    if (!isProgressEnabled() || !window.calibre || !window.calibre.progressUrl) {
        debugLog("Progress sync disabled or no URL, exiting");
        return;
    }

    var progressUrl = window.calibre.progressUrl;
    debugLog("Progress URL", progressUrl);

    function getCsrfToken() {
        var el = document.querySelector("input[name='csrf_token']");
        return el ? el.value : null;
    }

    function parseRemoteTimestamp(remote) {
        try {
            return Date.parse(remote && remote.last_modified ? remote.last_modified : "") || 0;
        } catch (e) {
            return 0;
        }
    }

    function getLocalStorageKey() {
        try {
            var match = String(progressUrl).match(/\/ajax\/reading-progress\/(\d+)\//i);
            var bookId = match ? match[1] : "unknown";
            return "calibre.reader.position.pdf." + bookId;
        } catch (e) {
            return "calibre.reader.position.pdf";
        }
    }

    var localStorageKey = getLocalStorageKey();

    function loadLocalPosition() {
        try {
            var raw = localStorage.getItem(localStorageKey);
            if (!raw) {
                return null;
            }
            return JSON.parse(raw);
        } catch (e) {
            return null;
        }
    }

    function saveLocalPosition(pageNumber) {
        try {
            localStorage.setItem(
                localStorageKey,
                JSON.stringify({ page: pageNumber, ts: Date.now() })
            );
        } catch (e) {}
    }

    async function fetchRemoteProgress() {
        try {
            var resp = await fetch(progressUrl, {
                method: "GET",
                credentials: "same-origin",
            });
            if (resp.status === 204) {
                return null;
            }
            if (!resp.ok) {
                return null;
            }
            return await resp.json();
        } catch (e) {
            return null;
        }
    }

    async function postProgress(pageNumber, pagesCount) {
        var csrf = getCsrfToken();
        if (!csrf) {
            return;
        }

        var percent = null;
        if (pagesCount && pagesCount > 0) {
            percent = Math.round((pageNumber / pagesCount) * 100);
        }

        var payload = {
            location_type: "pdf-page",
            location: String(pageNumber),
            progress_percent: percent,
            data: {
                page: pageNumber,
                pages: pagesCount || null,
            },
        };

        try {
            await fetch(progressUrl, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrf,
                },
                body: JSON.stringify(payload),
            });
        } catch (e) {}
    }

    var lastSyncedPage = null;
    var progressSyncTimeout = null;
    var restoring = false;
    var documentLoaded = false;
    var desiredPage = null;

    async function setup() {
        debugLog("Setup starting");
        
        if (
            !window.PDFViewerApplication ||
            !window.PDFViewerApplication.initializedPromise
        ) {
            debugLog("PDFViewerApplication not available yet, waiting...");
            // Wait for webviewerloaded event if PDFViewerApplication isn't ready
            await new Promise(function(resolve) {
                if (window.PDFViewerApplication && window.PDFViewerApplication.initializedPromise) {
                    resolve();
                } else {
                    window.addEventListener("webviewerloaded", resolve, { once: true });
                }
            });
        }

        debugLog("Waiting for PDFViewerApplication.initializedPromise");
        await window.PDFViewerApplication.initializedPromise;
        debugLog("PDFViewerApplication initialized");

        var app = window.PDFViewerApplication;
        if (!app.eventBus) {
            debugLog("No eventBus available, exiting");
            return;
        }

        function doRestore() {
            var pagesCount = app.pagesCount || 0;
            if (desiredPage == null || pagesCount <= 0 || desiredPage < 1 || desiredPage > pagesCount) {
                debugLog("doRestore: invalid page", { desiredPage: desiredPage, pagesCount: pagesCount });
                return;
            }

            var currentPage = app.pdfViewer ? app.pdfViewer.currentPageNumber : null;
            if (currentPage === desiredPage) {
                debugLog("Already on desired page", desiredPage);
                return;
            }

            debugLog("Navigating to page", desiredPage);
            restoring = true;
            try {
                // Use page setter which is more reliable
                app.page = desiredPage;
            } catch (e) {
                debugLog("Error during restore", e);
            }
        }

        // Wait for documentinit event which fires after PDF.js sets initial view
        // This ensures we navigate AFTER PDF.js does its own initialization
        var restored = false;
        
        app.eventBus.on("documentinit", function () {
            debugLog("documentinit event fired");
            if (!restored && desiredPage != null) {
                restored = true;
                // Small delay to let PDF.js finish its initial page set
                setTimeout(function() {
                    doRestore();
                }, 100);
            }
        });

        // Fallback: also listen for pagesloaded in case documentinit doesn't fire
        app.eventBus.on("pagesloaded", function () {
            debugLog("pagesloaded event fired");
            documentLoaded = true;
            if (!restored && desiredPage != null) {
                restored = true;
                setTimeout(function() {
                    doRestore();
                }, 100);
            }
        });
        
        documentLoaded = !!app.pdfDocument;
        debugLog("Initial documentLoaded state", documentLoaded);

        var localPos = loadLocalPosition();
        var localTs =
            localPos && typeof localPos.ts === "number" ? localPos.ts : 0;
        debugLog("Local position", { localPos: localPos, localTs: localTs });

        var remote = await fetchRemoteProgress();
        debugLog("Remote progress response", remote);
        
        var remotePage = null;
        var remoteTs = 0;

        if (remote && remote.location) {
            remoteTs = parseRemoteTimestamp(remote);
            var lt = String(remote.location_type || "").toLowerCase();
            debugLog("Remote location type", lt);
            if (lt === "pdf-page" || lt === "pdf") {
                var p = parseInt(remote.location, 10);
                if (Number.isInteger(p) && p > 0) {
                    remotePage = p;
                }
            }
        }

        debugLog("Timestamp comparison", {
            remotePage: remotePage,
            remoteTs: remoteTs,
            localTs: localTs,
            remoteNewer: remoteTs > localTs
        });

        var syncSource = null;
        if (remotePage != null && (localTs === 0 || remoteTs > localTs)) {
            desiredPage = remotePage;
            syncSource = "server";
            debugLog("Using remote page", desiredPage);
        } else if (localPos && localPos.page) {
            desiredPage = localPos.page;
            syncSource = "local";
            debugLog("Using local page", desiredPage);
        }

        if (desiredPage != null && syncSource) {
            showSyncToast("Restored from " + syncSource + ": page " + desiredPage, syncSource === "server" ? "success" : "info");
        }

        // If document is already loaded, trigger restore now (with delay)
        if (documentLoaded && desiredPage != null && !restored) {
            restored = true;
            setTimeout(function() {
                doRestore();
            }, 100);
        }

        app.eventBus.on("pagechanging", function (evt) {
            var pageNumber = evt && evt.pageNumber ? evt.pageNumber : null;
            if (!Number.isInteger(pageNumber) || pageNumber <= 0) {
                return;
            }

            saveLocalPosition(pageNumber);

            if (restoring) {
                restoring = false;
                lastSyncedPage = pageNumber;
                return;
            }

            if (!isProgressEnabled() || !progressUrl) {
                return;
            }

            var pagesCount = app.pagesCount || 0;
            if (pagesCount > 0 && (pageNumber < 1 || pageNumber > pagesCount)) {
                return;
            }

            if (progressSyncTimeout) {
                clearTimeout(progressSyncTimeout);
            }

            progressSyncTimeout = setTimeout(function () {
                if (pageNumber === lastSyncedPage) {
                    return;
                }
                lastSyncedPage = pageNumber;
                postProgress(pageNumber, pagesCount);
            }, 1500);
        });
    }

    setup();
})();
