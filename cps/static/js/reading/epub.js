/* global $, calibre, EPUBJS, ePubReader */

var reader;
var fontSize = 100;

(function() {
    "use strict";

    EPUBJS.filePath = calibre.filePath;
    EPUBJS.cssPath = calibre.cssPath;

    reader = ePubReader(calibre.bookUrl, {
        restore: true,
        bookmarks: calibre.bookmark ? [calibre.bookmark] : [],
        renderOptions: {
            ignoreClass: "annotator-hl",
            width: "100%",
            height: "100%",
            spread: "none"
        }
    });

    reader.rendition.themes.default({
        h1: {
            "font-size": "32px",
            "color": "#000000",
        },
        p: {
            "font-family": "Merriweather",
            "font-size": "16px",
            "margin": "20px !important",
            "line-height": "26px !important",
            "word-wrap": "break-word !important",
            "overflow-wrap": "break-word"
        },
    });

    reader.adjustFontSize = function(e) {
        var interval = 1;
        var PLUS = 187;
        var MINUS = 189;
        var ZERO = 48;
        var MOD = (e.ctrlKey || e.metaKey || e.shiftKey );
    
        if(e.keyCode == PLUS && MOD) {
            e.preventDefault();
            var newFontSize = fontSize + interval;
            this.rendition.themes.fontSize(newFontSize + "%");
            fontSize = newFontSize;
        }
    
        if(e.keyCode == MINUS && MOD){
            e.preventDefault();
            var newFontSize = fontSize - interval;
            this.rendition.themes.fontSize(newFontSize + "%");
            fontSize = newFontSize;
        }
    
        if(e.keyCode == ZERO && MOD){
            e.preventDefault();
            this.rendition.themes.fontSize("100%");
            fontSize = 100;
        }
    };

    if (calibre.useBookmarks) {
        reader.on("reader:bookmarked", updateBookmark.bind(reader, "add"));
        reader.on("reader:unbookmarked", updateBookmark.bind(reader, "remove"));
    } else {
        $("#bookmark, #show-Bookmarks").remove();
    }

    /**
     * @param {string} action - Add or remove bookmark
     * @param {string|int} location - Location or zero
     */
    function updateBookmark(action, location) {
        // Remove other bookmarks (there can only be one)
        if (action === "add") {
            this.settings.bookmarks.filter(function (bookmark) {
                return bookmark && bookmark !== location;
            }).map(function (bookmark) {
                this.removeBookmark(bookmark);
            }.bind(this));
        }

        // Save to database
        $.ajax(calibre.bookmarkUrl, {
            method: "post",
            data: { bookmark: location || "" }
        }).fail(function (xhr, status, error) {
            alert(error);
        });
    }
})();
