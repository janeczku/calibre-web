/* global $, calibre, EPUBJS, ePubReader */

var reader;

(function() {
    "use strict";

    EPUBJS.filePath = calibre.filePath;
    EPUBJS.cssPath = calibre.cssPath;

    reader = ePubReader(calibre.bookUrl, {
        restore: true,
        bookmarks: calibre.bookmark ? [calibre.bookmark] : []
    });

    Object.keys(window.themes).forEach(function(theme) {
        reader.rendition.themes.register(theme, window.themes[theme].css_path);
    });

    if (calibre.useBookmarks) {
        reader.on("reader:bookmarked", updateBookmark.bind(reader, "add"));
        reader.on("reader:unbookmarked", updateBookmark.bind(reader, "remove"));
    } else {
        $("#bookmark, #show-Bookmarks").remove();
    }

    // Swipe support
    let touchStart = 0;
    let touchEnd = 0;

    reader.rendition.on('touchstart', function(event) {
        touchStart = event.changedTouches[0].screenX;
    });
    reader.rendition.on('touchend', function(event) {
        touchEnd = event.changedTouches[0].screenX;
        if (touchStart < touchEnd) {
            if (reader.book.package.metadata.direction === "rtl") {
                reader.rendition.next();
            } else {
                reader.rendition.prev();
            }
        } else if (touchStart > touchEnd) {
            if (reader.book.package.metadata.direction === "rtl") {
                reader.rendition.prev();
            } else {
                reader.rendition.next();
            }
        }
    });

    function updateBookmark(action, location) {
        if (action === "add") {
            this.settings.bookmarks.filter(bm => bm && bm !== location).forEach(bm => {
                this.removeBookmark(bm);
            });
        }

        const csrftoken = $("input[name='csrf_token']").val();

        $.ajax(calibre.bookmarkUrl, {
            method: "POST",
            data: { bookmark: location || "" },
            headers: { "X-CSRFToken": csrftoken }
        }).fail((xhr, status, error) => {
            alert(error);
        });
    }

    function sendProgress(location) {
        if (!location || !location.end || !location.end.cfi) return;

        const cfi = location.end.cfi;
        const percent = Math.round(reader.book.locations.percentageFromCfi(cfi) * 100);
        const csrfToken = document.querySelector("input[name='csrf_token']").value;
        const progressDiv = document.getElementById("progress");

        if (progressDiv) {
            progressDiv.textContent = percent + "%";
        }

        fetch("/api/epub-progress", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken
            },
            body: JSON.stringify({
                book: parseInt(calibre.bookId || 0),
                cfi: cfi,
                percent: percent,
                total: 100
            })
        }).catch(err => console.error("Progress sync failed:", err));
    }

    // Load default theme
    const savedTheme = localStorage.getItem("calibre.reader.theme") || "lightTheme";
    selectTheme(savedTheme);

    reader.book.ready.then(() => {
        reader.book.locations.generate().then(() => {
            sendProgress(reader.rendition.currentLocation());
        });

        reader.rendition.on("relocated", location => {
            sendProgress(location);
        });
    });

})();

window.reader = reader; // expose globally so epub-progress.js can access it

