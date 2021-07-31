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
/* global _, i18nMsg, tinymce, getPath */

$(function () {
    var msg = i18nMsg;

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
        if(book.cover !== null){
            $(".cover img").attr("src", book.cover);
            $("#cover_url").val(book.cover);
        }
        $("#pubdate").val(book.publishedDate);
        $("#publisher").val(book.publisher);
        if (typeof book.series !== "undefined") {
            $("#series").val(book.series);
        }
    }

    function doSearch (keyword) {
        if (keyword) {
            $("#meta-info").text(msg.loading);
            $.ajax({
                url: getPath() + "/metadata/search",
                type: "POST",
                data: {"query": keyword},
                dataType: "json",
                success: function success(data) {
                    // console.log(data);
                    $("#meta-info").html("<ul id=\"book-list\" class=\"media-list\"></ul>");
                    data.forEach(function(book) {
                        var $book = $(templates.bookResult(book));
                        $book.find("img").on("click", function () {
                            populateForm(book);
                        });
                        $("#book-list").append($book);
                    });
                },
                error: function error() {
                    $("#meta-info").html("<p class=\"text-danger\">" + msg.search_error + "!</p>" + $("#meta-info")[0].innerHTML);
                },
            });
        }
    }

    function populate_provider() {
        $("#metadata_provider").empty();
        $.ajax({
            url: getPath() + "/metadata/provider",
            type: "get",
            dataType: "json",
            success: function success(data) {
                // console.log(data);
                data.forEach(function(provider) {
                    //$("#metadata_provider").html("<ul id=\"book-list\" class=\"media-list\"></ul>");
                    var checked = "";
                    if (provider.active) {
                        checked = "checked";
                    }
                    var $provider_button = '<input type="checkbox" id="show-' + provider.name + '" class="pill" data-control="' + provider.id + '" ' + checked + '><label for="show-' + provider.name + '">' + provider.name + ' <span class="glyphicon glyphicon-ok"></span></label>'
                    $("#metadata_provider").append($provider_button);
                });
            },
        });
    }


    $("#meta-search").on("submit", function (e) {
        e.preventDefault();
        var keyword = $("#keyword").val();
        doSearch(keyword);
    });

    $("#get_meta").click(function () {
        populate_provider();
        var bookTitle = $("#book_title").val();
        $("#keyword").val(bookTitle);
        doSearch(bookTitle);
    });
    $("#metaModal").on("show.bs.modal", function(e) {
        $(e.relatedTarget).one('focus', function (e) {
            $(this).blur();
        });
    });
});
