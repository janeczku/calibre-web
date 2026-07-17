/* Calibre-Web offline download manager.
 *
 * Stores book files, their reader pages and covers in the Cache Storage used
 * by the service worker (sw.js), plus a metadata index in localStorage so the
 * offline library page can list downloaded books without a network
 * connection. */

/* exported CWOffline */

var CWOffline = (function () {
    "use strict";

    var BOOKS_CACHE = "calibre-web-books-v1";
    var META_KEY = "calibre.offline.books";

    function supported() {
        return typeof window !== "undefined" && "caches" in window && "serviceWorker" in navigator;
    }

    function loadMeta() {
        try {
            return JSON.parse(localStorage.getItem(META_KEY)) || {};
        } catch (e) {
            return {};
        }
    }

    function saveMeta(meta) {
        localStorage.setItem(META_KEY, JSON.stringify(meta));
    }

    function bookKey(id, format) {
        return String(id) + "." + String(format).toLowerCase();
    }

    function fetchOk(url) {
        return fetch(url, { credentials: "same-origin" }).then(function (response) {
            if (!response.ok || response.redirected) {
                // A redirect means the session expired and we got the login
                // page instead of the requested resource.
                throw new Error("Could not fetch " + url + " (" + response.status + ")");
            }
            return response;
        });
    }

    // info: {id, format, title, authors, readUrl, bookUrl, coverUrl}
    function download(info) {
        var size = 0;
        return caches.open(BOOKS_CACHE).then(function (cache) {
            return fetchOk(info.bookUrl).then(function (response) {
                return response.blob().then(function (blob) {
                    size = blob.size;
                    var headers = new Headers();
                    var contentType = response.headers.get("Content-Type");
                    if (contentType) {
                        headers.set("Content-Type", contentType);
                    }
                    return cache.put(info.bookUrl, new Response(blob, { status: 200, headers: headers }));
                });
            }).then(function () {
                return fetchOk(info.readUrl).then(function (response) {
                    return cache.put(info.readUrl, response);
                });
            }).then(function () {
                // The cover is nice to have but not required for reading
                return fetchOk(info.coverUrl).then(function (response) {
                    return cache.put(info.coverUrl, response);
                }).catch(function () {});
            });
        }).then(function () {
            var meta = loadMeta();
            meta[bookKey(info.id, info.format)] = {
                id: info.id,
                format: String(info.format).toLowerCase(),
                title: info.title,
                authors: info.authors,
                readUrl: info.readUrl,
                bookUrl: info.bookUrl,
                coverUrl: info.coverUrl,
                size: size,
                addedAt: Date.now()
            };
            saveMeta(meta);
        });
    }

    function remove(id, format) {
        var meta = loadMeta();
        var key = bookKey(id, format);
        var entry = meta[key];
        if (!entry) {
            return Promise.resolve();
        }
        return caches.open(BOOKS_CACHE).then(function (cache) {
            return Promise.all([
                cache.delete(entry.bookUrl),
                cache.delete(entry.readUrl),
                entry.coverUrl ? cache.delete(entry.coverUrl) : Promise.resolve()
            ]);
        }).then(function () {
            delete meta[key];
            saveMeta(meta);
        });
    }

    function list() {
        var meta = loadMeta();
        return Object.keys(meta).map(function (key) {
            return meta[key];
        }).sort(function (a, b) {
            return (b.addedAt || 0) - (a.addedAt || 0);
        });
    }

    function has(id, format) {
        return Object.prototype.hasOwnProperty.call(loadMeta(), bookKey(id, format));
    }

    // ------------- "Make Available Offline" button wiring -------------

    function setButtonState(button, state) {
        var label = button.querySelector(".offline-btn-label");
        button.classList.remove("btn-primary", "btn-success", "btn-danger");
        if (state === "downloaded") {
            button.classList.add("btn-success");
            if (label) label.textContent = button.getAttribute("data-label-downloaded");
        } else if (state === "downloading") {
            button.classList.add("btn-primary");
            button.disabled = true;
            if (label) label.textContent = button.getAttribute("data-label-downloading");
            return;
        } else if (state === "failed") {
            button.classList.add("btn-danger");
            if (label) label.textContent = button.getAttribute("data-label-failed");
        } else {
            button.classList.add("btn-primary");
            if (label) label.textContent = button.getAttribute("data-label-download");
        }
        button.disabled = false;
    }

    function refreshButtons(root) {
        (root || document).querySelectorAll(".offline-download-btn").forEach(function (button) {
            if (!supported()) {
                // Cache Storage needs a secure context (HTTPS or localhost)
                button.style.display = "none";
                return;
            }
            setButtonState(button,
                has(button.getAttribute("data-book-id"), button.getAttribute("data-book-format"))
                    ? "downloaded" : "default");
        });
    }

    function onButtonClick(button) {
        var id = button.getAttribute("data-book-id");
        var format = button.getAttribute("data-book-format");
        if (has(id, format)) {
            remove(id, format).then(function () {
                setButtonState(button, "default");
            });
            return;
        }
        setButtonState(button, "downloading");
        download({
            id: id,
            format: format,
            title: button.getAttribute("data-book-title"),
            authors: button.getAttribute("data-book-authors"),
            readUrl: button.getAttribute("data-read-url"),
            bookUrl: button.getAttribute("data-book-url"),
            coverUrl: button.getAttribute("data-cover-url")
        }).then(function () {
            setButtonState(button, "downloaded");
        }).catch(function (error) {
            console.error("Offline download failed", error);
            setButtonState(button, "failed");
        });
    }

    if (typeof document !== "undefined") {
        document.addEventListener("click", function (event) {
            var button = event.target.closest ? event.target.closest(".offline-download-btn") : null;
            if (button && supported()) {
                onButtonClick(button);
            }
        });
        document.addEventListener("DOMContentLoaded", function () {
            refreshButtons();
            // Book details can also be loaded into a bootstrap modal
            if (window.jQuery) {
                window.jQuery(document).on("shown.bs.modal", function () {
                    refreshButtons();
                });
            }
        });
    }

    return {
        supported: supported,
        download: download,
        remove: remove,
        list: list,
        has: has,
        refreshButtons: refreshButtons
    };
})();
