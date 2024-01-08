/* global $, calibre, EPUBJS, ePubReader */

let reader;

(function () {
    "use strict";

    EPUBJS.filePath = calibre.filePath;
    EPUBJS.cssPath = calibre.cssPath;

    reader = ePubReader(calibre.bookUrl, {
        restore: true,
        bookmarks: calibre.bookmark ? [calibre.bookmark] : [],
    });

    Object.keys(window.themes).forEach(function (theme) {
        reader.rendition.themes.register(theme, window.themes[theme].css_path);
    });

    if (calibre.useBookmarks) {
        reader.on("reader:bookmarked", updateBookmark.bind(reader, "add"));
        reader.on("reader:unbookmarked", updateBookmark.bind(reader, "remove"));
    } else {
        $("#bookmark, #show-Bookmarks").remove();
    }

    // Enable swipe support
    // I have no idea why swiperRight/swiperLeft from plugins is not working, events just don't get fired
    let touchStart = 0;
    let touchEnd = 0;

    reader.rendition.on("touchstart", function (event) {
        touchStart = event.changedTouches[0].screenX;
    });
    reader.rendition.on("touchend", function (event) {
        touchEnd = event.changedTouches[0].screenX;
        if (touchStart < touchEnd) {
            if (reader.book.package.metadata.direction === "rtl") {
                reader.rendition.next();
            } else {
                reader.rendition.prev();
            }
            // Swiped Right
        }
        if (touchStart > touchEnd) {
            if (reader.book.package.metadata.direction === "rtl") {
                reader.rendition.prev();
            } else {
                reader.rendition.next();
            }
            // Swiped Left
        }
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

        const csrftoken = $("input[name='csrf_token']").val();

        // Save to database
        $.ajax(calibre.bookmarkUrl, {
            method: "post",
            data: { bookmark: location || "" },
            headers: { "X-CSRFToken": csrftoken },
        }).fail(function (xhr, status, error) {
            alert(error);
        });
    }

    // default settings load
    const theme = localStorage.getItem("calibre.reader.theme") ?? "lightTheme";
    selectTheme(theme);
    const font = localStorage.getItem("calibre.reader.font") ?? "Roboto";
    selectFont(font);

    // enabling script content
    // reader.rendition.settings.allowScriptedContent = true;
})();
