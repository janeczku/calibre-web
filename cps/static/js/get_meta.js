/*
 * Get Metadata from Douban Books api and Google Books api
 * Created by idalin<dalin.lin@gmail.com>
 * Google Books api document: https://developers.google.com/books/docs/v1/using
 * Douban Books api document: https://developers.douban.com/wiki/?title=book_v2 (Chinese Only)
 */
 /* global i18nMsg */

$(document).ready(function () {
    var msg = i18nMsg;
    var douban = "https://api.douban.com";
    var dbSearch = "/v2/book/search";
    // var dbGetInfo = "/v2/book/";
    // var db_get_info_by_isbn = "/v2/book/isbn/ ";
    var dbDone = false;

    var google = "https://www.googleapis.com/";
    var ggSearch = "/books/v1/volumes";
    // var gg_get_info = "/books/v1/volumes/";
    var ggDone = false;

    var dbResults = [];
    var ggResults = [];
    var showFlag = 0;
    String.prototype.replaceAll = function (s1, s2) {
        return this.replace(new RegExp(s1, "gm"), s2);
    };

    function showResult () {
        var book;
        var i;
        var bookHtml;
        showFlag++;
        if (showFlag === 1) {
            $("#meta-info").html("<ul id=\"book-list\" class=\"media-list\"></ul>");
        }
        if (ggDone && dbDone) {
            if (!ggResults && !dbResults) {
                $("#meta-info").html("<p class=\"text-danger\">"+ msg.no_result +"</p>");
                return;
            }
        }
        if (ggDone && ggResults.length > 0) {
            for (i = 0; i < ggResults.length; i++) {
                book = ggResults[i];
                var bookCover;
                if (book.volumeInfo.imageLinks) {
                    bookCover = book.volumeInfo.imageLinks.thumbnail;
                } else {
                    bookCover = "/static/generic_cover.jpg";
                }
                bookHtml = "<li class=\"media\">" +
                    "<img class=\"pull-left img-responsive\" data-toggle=\"modal\" data-target=\"#metaModal\" src=\"" +
                    bookCover + "\" alt=\"Cover\" style=\"width:100px;height:150px\" onclick='javascript:getMeta(\"google\"," +
                    i + ")\\>\"" +
                    "<div class=\"media-body\">" +
                    "<h4 class=\"media-heading\"><a href=\"https://books.google.com/books?id=" +
                    book.id + "\"  target=\"_blank\">" + book.volumeInfo.title + "</a></h4>" +
                    "<p>"+ msg.author +"：" + book.volumeInfo.authors + "</p>" +
                    "<p>"+ msg.publisher + "：" + book.volumeInfo.publisher + "</p>" +
                    "<p>"+ msg.description + ":" + book.volumeInfo.description + "</p>" +
                    "<p>"+ msg.source + ":<a href=\"https://books.google.com\" target=\"_blank\">Google Books</a></p>" +
                    "</div>" +
                    "</li>";
                $("#book-list").append(bookHtml);
            }
            ggDone = false;
        }
        if (dbDone && dbResults.length > 0) {
            for (i = 0; i < dbResults.length; i++) {
                book = dbResults[i];
                bookHtml = "<li class=\"media\">" +
                    "<img class=\"pull-left img-responsive\" data-toggle=\"modal\" data-target=\"#metaModal\" src=\"" +
                    book.image + "\" alt=\"Cover\" style=\"width:100px;height: 150px\" onclick='javascript:getMeta(\"douban\"," +
                    i + ")\\'>" +
                    "<div class=\"media-body\">" +
                    "<h4 class=\"media-heading\"><a href=\"https://book.douban.com/subject/" +
                    book.id + "\"  target=\"_blank\">" + book.title + "</a></h4>" +
                    "<p>" + msg.author + "：" + book.author + "</p>" +
                    "<p>" + msg.publisher + "：" + book.publisher + "</p>" +
                    "<p>" + msg.description + ":" + book.summary + "</p>" +
                    "<p>" + msg.source + ":<a href=\"https://book.douban.com\" target=\"_blank\">Douban Books</a></p>" +
                    "</div>" +
                    "</li>";
                $("#book-list").append(bookHtml);
            }
            dbDone = false;
        }
    }

    function ggSearchBook (title) {
        title = title.replaceAll(/\s+/, "+");
        var url = google + ggSearch + "?q=" + title;
        $.ajax({
            url,
            type: "GET",
            dataType: "jsonp",
            jsonp: "callback",
            success (data) {
                ggResults = data.items;
            },
            complete () {
                ggDone = true;
                showResult();
            }
        });
    }

    function getMeta (source, id) {
        var meta;
        var tags;
        if (source === "google") {
            meta = ggResults[id];
            $("#description").val(meta.volumeInfo.description);
            $("#bookAuthor").val(meta.volumeInfo.authors.join(" & "));
            $("#book_title").val(meta.volumeInfo.title);
            if (meta.volumeInfo.categories) {
                tags = meta.volumeInfo.categories.join(",");
                $("#tags").val(tags);
            }
            if (meta.volumeInfo.averageRating) {
                $("#rating").val(Math.round(meta.volumeInfo.averageRating));
            }
            return;
        }
        if (source === "douban") {
            meta = dbResults[id];
            $("#description").val(meta.summary);
            $("#bookAuthor").val(meta.author.join(" & "));
            $("#book_title").val(meta.title);
            tags = "";
            for (var i = 0; i < meta.tags.length; i++) {
                tags = tags + meta.tags[i].title + ",";
            }
            $("#tags").val(tags);
            $("#rating").val(Math.round(meta.rating.average / 2));
            return;
        }
    }

    function dbSearchBook (title) {
        var url = douban + dbSearch + "?q=" + title + "&fields=all&count=10";
        $.ajax({
            url,
            type: "GET",
            dataType: "jsonp",
            jsonp: "callback",
            success (data) {
                dbResults = data.books;
            },
            error () {
                $("#meta-info").html("<p class=\"text-danger\">"+ msg.search_error+"!</p>");
            },
            complete () {
                dbDone = true;
                showResult();
            }
        });
    }

    function doSearch (keyword) {
        showFlag = 0;
        $("#meta-info").text(msg.loading);
        // var keyword = $("#keyword").val();
        if (keyword) {
            dbSearchBook(keyword);
            ggSearchBook(keyword);
        }
    }

    $("#do-search").click(function () {
        var keyword = $("#keyword").val();
        if (keyword) {
            doSearch(keyword);
        }
    });

    $("#get_meta").click(function () {
        var bookTitle = $("#book_title").val();
        if (bookTitle) {
            $("#keyword").val(bookTitle);
            doSearch(bookTitle);
        }
    });

});