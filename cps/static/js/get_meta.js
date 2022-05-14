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
    var keyword = ""

    var templates = {
        bookResult: _.template(
            $("#template-book-result").html()
       )
    };

    function getUniqueValues(attribute_name, book){
        var presentArray = $.map($("#"+attribute_name).val().split(","), $.trim);
        if ( presentArray.length === 1 && presentArray[0] === "") {
            presentArray = [];
        }
        $.each(book[attribute_name], function(i, el) {
            if ($.inArray(el, presentArray) === -1) presentArray.push(el);
        });
        return presentArray
    }

    function populateForm (book) {
        tinymce.get("description").setContent(book.description);
        var uniqueTags = getUniqueValues('tags', book)
        var uniqueLanguages = getUniqueValues('languages', book)
        var ampSeparatedAuthors = (book.authors || []).join(" & ");
        $("#bookAuthor").val(ampSeparatedAuthors);
        $("#book_title").val(book.title);
        $("#tags").val(uniqueTags.join(", "));
        $("#languages").val(uniqueLanguages.join(", "));
        $("#rating").data("rating").setValue(Math.round(book.rating));
        if(book.cover && $("#cover_url").length){
            $(".cover img").attr("src", book.cover);
            $("#cover_url").val(book.cover);
        }
        $("#pubdate").val(book.publishedDate);
        $("#publisher").val(book.publisher);
        if (typeof book.series !== "undefined") {
            $("#series").val(book.series);
            $("#series_index").val(book.series_index);
        }
        if (typeof book.identifiers !== "undefined") {
            populateIdentifiers(book.identifiers)
        }
    }

    function populateIdentifiers(identifiers){
       for (const property in identifiers) {
          console.log(`${property}: ${identifiers[property]}`);
          if ($('input[name="identifier-type-'+property+'"]').length) {
              $('input[name="identifier-val-'+property+'"]').val(identifiers[property])
          }
          else {
              addIdentifier(property, identifiers[property])
          }
        }
    }

    function addIdentifier(name, value){
        var line = '<tr>';
        line += '<td><input type="text" class="form-control" name="identifier-type-'+ name +'" required="required" placeholder="' + _("Identifier Type") +'" value="'+ name +'"></td>';
        line += '<td><input type="text" class="form-control" name="identifier-val-'+ name +'" required="required" placeholder="' + _("Identifier Value") +'" value="'+ value +'"></td>';
        line += '<td><a class="btn btn-default" onclick="removeIdentifierLine(this)">'+_("Remove")+'</a></td>';
        line += '</tr>';
        $("#identifier-table").append(line);
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
                    if (data.length) {
                        $("#meta-info").html("<ul id=\"book-list\" class=\"media-list\"></ul>");
                        data.forEach(function(book) {
                            var $book = $(templates.bookResult(book));
                            $book.find("img").on("click", function () {
                                populateForm(book);
                            });
                            $("#book-list").append($book);
                        });
                    }
                    else {
                        $("#meta-info").html("<p class=\"text-danger\">" + msg.no_result + "!</p>" + $("#meta-info")[0].innerHTML)
                    }
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
                data.forEach(function(provider) {
                    var checked = "";
                    if (provider.active) {
                        checked = "checked";
                    }
                    var $provider_button = '<input type="checkbox" id="show-' + provider.name + '" class="pill" data-initial="' + provider.initial + '" data-control="' + provider.id + '" ' + checked + '><label for="show-' + provider.name + '">' + provider.name + ' <span class="glyphicon glyphicon-ok"></span></label>'
                    $("#metadata_provider").append($provider_button);
                });
            },
        });
    }

    $(document).on("change", ".pill", function () {
        var element = $(this);
        var id = element.data("control");
        var initial = element.data("initial");
        var val = element.prop('checked');
        var params = {id : id, value: val};
        if (!initial) {
            params['initial'] = initial;
            params['query'] = keyword;
        }
        $.ajax({
            method:"post",
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            url: getPath() + "/metadata/provider/" + id,
            data: JSON.stringify(params),
            success: function success(data) {
                element.data("initial", "true");
                data.forEach(function(book) {
                    var $book = $(templates.bookResult(book));
                    $book.find("img").on("click", function () {
                        populateForm(book);
                    });
                    $("#book-list").append($book);
                });
            }
        });
    });

    $("#meta-search").on("submit", function (e) {
        e.preventDefault();
        keyword = $("#keyword").val();
        $('.pill').each(function(){
            $(this).data("initial", $(this).prop('checked'));
        });
        doSearch(keyword);
    });

    $("#get_meta").click(function () {
        populate_provider();
        var bookTitle = $("#book_title").val();
        $("#keyword").val(bookTitle);
        keyword = bookTitle;
        doSearch(bookTitle);
    });
    $("#metaModal").on("show.bs.modal", function(e) {
        $(e.relatedTarget).one('focus', function (e) {
            $(this).blur();
        });
    });
});
