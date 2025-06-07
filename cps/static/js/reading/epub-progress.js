(function() {
    "use strict";

    console.log("epub-progress.js loaded");

    // Wait until reader and rendition are ready
    function waitForReaderReady(callback) {
        const interval = setInterval(() => {
            if (window.reader?.rendition && window.reader.rendition.q?.running === undefined) {
                clearInterval(interval);
                console.log("Reader rendition ready");
                callback();
            }
        }, 300);
    }

    function getProgressPercent(epub, location) {
        if (!location || (!location.end && !location.start)) return 0;

        const cfi = location.end?.cfi || location.start?.cfi;
        if (!cfi || !epub?.locations) return 0;

        try {
            return Math.round(epub.locations.percentageFromCfi(cfi) * 100);
        } catch (err) {
            console.warn("Progress calc error:", err);
            return 0;
        }
    }

    waitForReaderReady(() => {
        const reader = window.reader;
        if (!reader) {
            console.error("Reader not found after wait!");
            return;
        }

        const epub = reader.book;
        const bookId = window.calibre?.bookId;
        const csrfToken = document.querySelector("input[name='csrf_token']")?.value;

        if (!bookId) {
            console.error("Book ID missing!");
            return;
        }

        reader.rendition.on("relocated", (location) => {
            if (!location || !location.start?.cfi) return;

            const cfi = location.start.cfi;
            const total = epub.locations.length();
            const percent = getProgressPercent(epub, location);

            console.log(`Sending progress: book=${bookId}, cfi=${cfi}, percent=${percent}, total=${total}`);

            fetch("/api/epub-progress", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken
                },
                body: JSON.stringify({
                    book: bookId,
                    cfi: cfi,
                    percent: percent,
                    total: total
                })
            }).catch(err => console.error("EPUB progress sync failed", err));
        });
    });
})();
