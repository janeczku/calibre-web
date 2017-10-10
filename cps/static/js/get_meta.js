/*
 * Get Metadata from Douban Books api and Google Books api
 * Created by idalin<dalin.lin@gmail.com>
 * Google Books api document: https://developers.google.com/books/docs/v1/using
 * Douban Books api document: https://developers.douban.com/wiki/?title=book_v2 (Chinese Only)
*/
/* global _, i18nMsg, tinymce */
var dbResults = [];
var ggResults = [];

$(function () {
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

    var showFlag = 0;

    var templates = {
        bookResult: _.template(
            $("#template-book-result").html()
        )
    };

    function populateForm (book) {
        tinymce.get("description").setContent(book.description);
        $("#bookAuthor").val(book.authors);
        $("#book_title").val(book.title);
        $("#tags").val(book.tags.join(","));
        $("#rating").data("rating").setValue(Math.round(book.rating));
        $(".cover img").attr("src", book.cover);
        $("#cover_url").val(book.cover);
    }

    function showResult () {
        showFlag++;
        if (showFlag === 1) {
            $("#meta-info").html("<ul id=\"book-list\" class=\"media-list\"></ul>");
        }
        if (ggDone && dbDone) {
            if (!ggResults && !dbResults) {
                $("#meta-info").html("<p class=\"text-danger\">" + msg.no_result + "</p>");
                return;
            }
        }
        if (ggDone && ggResults.length > 0) {
            ggResults.forEach(function(result) {
                var book = {
                    id: result.id,
                    title: result.volumeInfo.title,
                    authors: result.volumeInfo.authors || [],
                    description: result.volumeInfo.description || "",
                    publisher: result.volumeInfo.publisher || "",
                    publishedDate: result.volumeInfo.publishedDate || "",
                    tags: result.volumeInfo.categories || [],
                    rating: result.volumeInfo.averageRating || 0,
                    cover: result.volumeInfo.imageLinks ?
                        result.volumeInfo.imageLinks.thumbnail :
                        "/static/generic_cover.jpg",
                    url: "https://books.google.com/books?id=" + result.id,
                    source: {
                        id: "google",
                        description: "Google Books",
                        url: "https://books.google.com/"
                    }
                };

                var $book = $(templates.bookResult(book));
                $book.find("img").on("click", function () {
                    populateForm(book);
                });

                $("#book-list").append($book);
            });
            ggDone = false;
        }
        if (dbDone && dbResults.length > 0) {
            dbResults.forEach(function(result) {
                var book = {
                    id: result.id,
                    title: result.title,
                    authors: result.author || [],
                    description: result.summary,
                    publisher: result.publisher || "",
                    publishedDate: result.pubdate || "",
                    tags: result.tags.map(function(tag) {
                        return tag.title;
                    }),
                    rating: result.rating.average || 0,
                    cover: result.image,
                    url: "https://book.douban.com/subject/" + result.id,
                    source: {
                        id: "douban",
                        description: "Douban Books",
                        url: "https://book.douban.com/"
                    }
                };

                if (book.rating > 0) {
                    book.rating /= 2;
                }

                var $book = $(templates.bookResult(book));
                $book.find("img").on("click", function () {
                    populateForm(book);
                });

                $("#book-list").append($book);
            });
            dbDone = false;
        }
    }

    function ggSearchBook (title) {
        $.ajax({
            url: google + ggSearch + "?q=" + title.replace(/\s+/gm, "+"),
            type: "GET",
            dataType: "jsonp",
            jsonp: "callback",
            success: function success(data) {
                ggResults = data.items;
            },
            complete: function complete() {
                ggDone = true;
                showResult();
                $("#show-google").trigger("change");
            }
        });
    }

    function dbSearchBook (title) {
        $.ajax({
            url: douban + dbSearch + "?q=" + title + "&fields=all&count=10",
            type: "GET",
            dataType: "jsonp",
            jsonp: "callback",
            success: function success(data) {
                dbResults = data.books;
            },
            error: function error() {
                $("#meta-info").html("<p class=\"text-danger\">" + msg.search_error + "!</p>");
            },
            complete: function complete() {
                dbDone = true;
                showResult();
                $("#show-douban").trigger("change");
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

    $("#meta-search").on("submit", function (e) {
        e.preventDefault();
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
