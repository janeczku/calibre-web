/* This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
 *    Copyright (C) 2018  idalin<dalin.lin@gmail.com>
 *
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program. If not, see <http://www.gnu.org/licenses/>.
 */
/*
 * Get Metadata from Douban Books api and Google Books api and ComicVine
 * Google Books api document: https://developers.google.com/books/docs/v1/using
 * Douban Books api document: https://developers.douban.com/wiki/?title=book_v2 (Chinese Only)
 * ComicVine api document: https://comicvine.gamespot.com/api/documentation
*/
/* global _, i18nMsg, tinymce */
var dbResults = [];
var ggResults = [];
var cvResults = [];

$(function () {
    var msg = i18nMsg;
    var douban = "https://api.douban.com";
    var dbSearch = "/v2/book/search";
    var dbDone = 0;

    var google = "https://www.googleapis.com";
    var ggSearch = "/books/v1/volumes";
    var ggDone = 0;

    var comicvine = "https://comicvine.gamespot.com";
    var cvSearch = "/api/search/";
    var cvDone = 0;

    var showFlag = 0;

    var templates = {
        bookResult: _.template(
            $("#template-book-result").html()
        )
    };

    function populateForm (book) {
        tinymce.get("description").setContent(book.description);
        var uniqueTags = [];
        $.each(book.tags, function(i, el) {
            if ($.inArray(el, uniqueTags) === -1) uniqueTags.push(el);
        });

        var ampSeparatedAuthors = (book.authors || []).join(" & ");
        $("#bookAuthor").val(ampSeparatedAuthors);
        $("#book_title").val(book.title);
        $("#tags").val(uniqueTags.join(","));
        $("#rating").data("rating").setValue(Math.round(book.rating));
        $(".cover img").attr("src", book.cover);
        $("#cover_url").val(book.cover);
        $("#pubdate").val(book.publishedDate);
        $("#publisher").val(book.publisher);
        if (typeof book.series !== "undefined") {
            $("#series").val(book.series);
        }
    }

    function showResult () {
        showFlag++;
        if (showFlag === 1) {
            $("#meta-info").html("<ul id=\"book-list\" class=\"media-list\"></ul>");
        }
        if ((ggDone === 3 || (ggDone === 1 && ggResults.length === 0)) &&
            (dbDone === 3 || (ggDone === 1 && dbResults.length === 0)) &&
            (cvDone === 3 || (ggDone === 1 && cvResults.length === 0))) {
            $("#meta-info").html("<p class=\"text-danger\">" + msg.no_result + "</p>");
            return;
        }
        function formatDate (date) {
            var d = new Date(date),
                month = "" + (d.getMonth() + 1),
                day = "" + d.getDate(),
                year = d.getFullYear();

            if (month.length < 2) {
                month = "0" + month;
            }
            if (day.length < 2) {
                day = "0" + day;
            }

            return [year, month, day].join("-");
        }

        if (ggResults.length > 0) {
            if (ggDone < 2) {
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
                            result.volumeInfo.imageLinks.thumbnail : "/static/generic_cover.jpg",
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
                ggDone = 2;
            } else {
                ggDone = 3;
            }
        }

        if (dbResults.length > 0) {
            if (dbDone < 2) {
                dbResults.forEach(function(result) {
                    var seriesTitle = "";
                    if (result.series) {
                        seriesTitle = result.series.title;
                    }
                    var dateFomers = result.pubdate.split("-");
                    var publishedYear = parseInt(dateFomers[0]);
                    var publishedMonth = parseInt(dateFomers[1]);
                    var publishedDate = new Date(publishedYear, publishedMonth - 1, 1);

                    publishedDate = formatDate(publishedDate);

                    var book = {
                        id: result.id,
                        title: result.title,
                        authors: result.author || [],
                        description: result.summary,
                        publisher: result.publisher || "",
                        publishedDate: publishedDate || "",
                        tags: result.tags.map(function(tag) {
                            return tag.title.toLowerCase().replace(/,/g, "_");
                        }),
                        rating: result.rating.average || 0,
                        series: seriesTitle || "",
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
                dbDone = 2;
            } else {
                dbDone = 3;
            }
        }
        if (cvResults.length > 0) {
            if (cvDone < 2) {
                cvResults.forEach(function(result) {
                    var seriesTitle = "";
                    if (result.volume.name) {
                        seriesTitle = result.volume.name;
                    }
                    var dateFomers = "";
                    if (result.store_date) {
                        dateFomers = result.store_date.split("-");
                    } else {
                        dateFomers = result.date_added.split("-");
                    }
                    var publishedYear = parseInt(dateFomers[0]);
                    var publishedMonth = parseInt(dateFomers[1]);
                    var publishedDate = new Date(publishedYear, publishedMonth - 1, 1);

                    publishedDate = formatDate(publishedDate);

                    var book = {
                        id: result.id,
                        title: seriesTitle + " #" + ("00" + result.issue_number).slice(-3) + " - " + result.name,
                        authors: result.author || [],
                        description: result.description,
                        publisher: "",
                        publishedDate: publishedDate || "",
                        tags: ["Comics", seriesTitle],
                        rating: 0,
                        series: seriesTitle || "",
                        cover: result.image.original_url,
                        url: result.site_detail_url,
                        source: {
                            id: "comicvine",
                            description: "ComicVine Books",
                            url: "https://comicvine.gamespot.com/"
                        }
                    };

                    var $book = $(templates.bookResult(book));
                    $book.find("img").on("click", function () {
                        populateForm(book);
                    });

                    $("#book-list").append($book);
                });
                cvDone = 2;
            } else {
                cvDone = 3;
            }
        }
    }

    function ggSearchBook (title) {
        $.ajax({
            url: google + ggSearch + "?q=" + title.replace(/\s+/gm, "+"),
            type: "GET",
            dataType: "jsonp",
            jsonp: "callback",
            success: function success(data) {
                if ("items" in data) {
                    ggResults = data.items;
                }
            },
            complete: function complete() {
                ggDone = 1;
                showResult();
                $("#show-google").trigger("change");
            }
        });
    }

    function dbSearchBook (title) {
        var apikey = "0df993c66c0c636e29ecbb5344252a4a";
        $.ajax({
            url: douban + dbSearch + "?apikey=" + apikey + "&q=" + title + "&fields=all&count=10",
            type: "GET",
            dataType: "jsonp",
            jsonp: "callback",
            success: function success(data) {
                dbResults = data.books;
            },
            error: function error() {
                $("#meta-info").html("<p class=\"text-danger\">" + msg.search_error + "!</p>" + $("#meta-info")[0].innerHTML);
            },
            complete: function complete() {
                dbDone = 1;
                showResult();
                $("#show-douban").trigger("change");
            }
        });
    }

    function cvSearchBook (title) {
        var apikey = "57558043c53943d5d1e96a9ad425b0eb85532ee6";
        title = encodeURIComponent(title);
        $.ajax({
            url: comicvine + cvSearch + "?api_key=" + apikey + "&resources=issue&query=" + title + "&sort=name:desc&format=jsonp",
            type: "GET",
            dataType: "jsonp",
            jsonp: "json_callback",
            success: function success(data) {
                cvResults = data.results;
            },
            error: function error() {
                $("#meta-info").html("<p class=\"text-danger\">" + msg.search_error + "!</p>" + $("#meta-info")[0].innerHTML);
            },
            complete: function complete() {
                cvDone = 1;
                showResult();
                $("#show-comics").trigger("change");
            }
        });
    }

    function doSearch (keyword) {
        showFlag = 0;
        dbDone = ggDone = cvDone = 0;
        dbResults = [];
        ggResults = [];
        cvResults = [];
        $("#meta-info").text(msg.loading);
        if (keyword) {
            dbSearchBook(keyword);
            ggSearchBook(keyword);
            cvSearchBook(keyword);
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
