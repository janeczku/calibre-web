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

    // Dark mode logic
    $("#colorMode").on( "click", function() {
      if ($("#colorMode").prop("checked")) {
        darkMode();
      } else {
        $("#main").css("background", "#fff");
        $("#titlebar").css("color", "#4f4f4f")
        $("iframe").contents().find("body").css('background-color', 'white');
        $("iframe").contents().find("body").css('color', 'black');
        $("iframe").contents().find("a:link").css('color', '#00f');
      }
    })

    function darkMode() {
      console.log("Dark mode activated");
      $("#main").css("background", "#343233");
      $("#titlebar").css("color", "#ccc")
      $("iframe").contents().find("body").css('background-color', '#4b4b4b');
      $("iframe").contents().find("body").css('color', '#ccc');
      $("iframe").contents().find("a:link").css('color', '#fe8019');
    }

    //Prevent dark mode from changing on page reload
    $(".arrow").on("click", function() {
      if ($("#colorMode").prop("checked") && $("iframe").contents().find("body").css('background-color') == 'rgb(255, 255, 255)') {
        darkMode();
      }
    })

})();
