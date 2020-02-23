/* This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
 *    Copyright (C) 2012-2019  mutschler, janeczku, jkrehm, OzzieIsaacs
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

// Generic control/related handler to show/hide fields based on a checkbox' value
// e.g.
//  <input type="checkbox" data-control="stuff-to-show">
//  <div data-related="stuff-to-show">...</div>
$(document).on("change", "input[type=\"checkbox\"][data-control]", function () {
    var $this = $(this);
    var name = $this.data("control");
    var showOrHide = $this.prop("checked");

    $("[data-related=\"" + name + "\"]").each(function () {
        $(this).toggle(showOrHide);
    });
});


// Generic control/related handler to show/hide fields based on a select' value
$(document).on("change", "select[data-control]", function() {
    var $this = $(this);
    var name = $this.data("control");
    var showOrHide = parseInt($this.val());
    // var showOrHideLast = $("#" + name + " option:last").val()
    for (var i = 0; i < $(this)[0].length; i++) {
        var element = parseInt($(this)[0][i].value);
        if (element === showOrHide) {
            $("[data-related=" + name + "-" + element + "]").show();
        } else {
            $("[data-related=" + name + "-" + element + "]").hide();
        }
    }
});


$(function() {
    var updateTimerID;
    var updateText;

    // Allow ajax prefilters to be added/removed dynamically
    // eslint-disable-next-line new-cap
    var preFilters = $.Callbacks();
    $.ajaxPrefilter(preFilters.fire);

    function restartTimer() {
        $("#spinner").addClass("hidden");
        $("#RestartDialog").modal("hide");
    }

    function updateTimer() {
        $.ajax({
            dataType: "json",
            url: window.location.pathname + "/../../get_updater_status",
            success: function success(data) {
                // console.log(data.status);
                $("#Updatecontent").html(updateText[data.status]);
                if (data.status > 6) {
                    clearInterval(updateTimerID);
                    $("#spinner2").hide();
                    $("#updateFinished").removeClass("hidden");
                    $("#check_for_update").removeClass("hidden");
                    $("#perform_update").addClass("hidden");
                }
            },
            error: function error() {
                // console.log('Done');
                clearInterval(updateTimerID);
                $("#spinner2").hide();
                $("#Updatecontent").html(updateText[7]);
                $("#updateFinished").removeClass("hidden");
                $("#check_for_update").removeClass("hidden");
                $("#perform_update").addClass("hidden");
            },
            timeout: 2000
        });
    }

    $(".discover .row").isotope({
        // options
        itemSelector : ".book",
        layoutMode : "fitRows"
    });

    $(".grid").isotope({
        // options
        itemSelector : ".grid-item",
        layoutMode : "fitColumns"
    });


    var $loadMore = $(".load-more .row").infiniteScroll({
        debug: false,
        // selector for the paged navigation (it will be hidden)
        path : ".next",
        // selector for the NEXT link (to page 2)
        append : ".load-more .book"
        //animate      : true, # ToDo: Reenable function
        //extraScrollPx: 300
    });
    $loadMore.on( "append.infiniteScroll", function( event, response, path, data ) {
        $(".pagination").addClass("hidden");
        $(".load-more .row").isotope( "appended", $(data), null );
    });

    $("#restart").click(function() {
        $.ajax({
            dataType: "json",
            url: window.location.pathname + "/../../shutdown",
            data: {"parameter":0},
            success: function success() {
                $("#spinner").show();
                setTimeout(restartTimer, 3000);
            }
        });
    });
    $("#shutdown").click(function() {
        $.ajax({
            dataType: "json",
            url: window.location.pathname + "/../../shutdown",
            data: {"parameter":1},
            success: function success(data) {
                return alert(data.text);
            }
        });
    });
    $("#check_for_update").click(function() {
        var $this = $(this);
        var buttonText = $this.html();
        $this.html("...");
        $("#update_error").addClass("hidden");
        if ($("#message").length) {
            $("#message").alert("close");
        }
        $.ajax({
            dataType: "json",
            url: window.location.pathname + "/../../get_update_status",
            success: function success(data) {
                $this.html(buttonText);

                var cssClass = "";
                var message = "";

                if (data.success === true) {
                    if (data.update === true) {
                        $("#check_for_update").addClass("hidden");
                        $("#perform_update").removeClass("hidden");
                        $("#update_info")
                            .removeClass("hidden")
                            .find("span").html(data.commit);

                        data.history.forEach(function(entry) {
                            $("<tr><td>" + entry[0] + "</td><td>" + entry[1] + "</td></tr>").appendTo($("#update_table"));
                        });
                        cssClass = "alert-warning";
                    } else {
                        cssClass = "alert-success";
                    }
                } else {
                    cssClass = "alert-danger";
                }

                message = "<div id=\"message\" class=\"alert " + cssClass
                    + " fade in\"><a href=\"#\" class=\"close\" data-dismiss=\"alert\">&times;</a>"
                    + data.message + "</div>";

                $(message).insertAfter($("#update_table"));
            }
        });
    });
    $("#restart_database").click(function() {
        $.ajax({
            dataType: "json",
            url: window.location.pathname + "/../../shutdown",
            data: {"parameter":2}
        });
    });
    $("#perform_update").click(function() {
        $("#spinner2").show();
        $.ajax({
            type: "POST",
            dataType: "json",
            data: { start: "True"},
            url: window.location.pathname + "/../../get_updater_status",
            success: function success(data) {
                updateText = data.text;
                $("#Updatecontent").html(updateText[data.status]);
                // console.log(data.status);
                updateTimerID = setInterval(updateTimer, 2000);
            }
        });
    });

    // Init all data control handlers to default
    $("input[data-control]").trigger("change");
    $("select[data-control]").trigger("change");

    $("#bookDetailsModal")
        .on("show.bs.modal", function(e) {
            var $modalBody = $(this).find(".modal-body");

            // Prevent static assets from loading multiple times
            var useCache = function(options) {
                options.async = true;
                options.cache = true;
            };
            preFilters.add(useCache);

            $.get(e.relatedTarget.href).done(function(content) {
                $modalBody.html(content);
                preFilters.remove(useCache);
            });
        })
        .on("hidden.bs.modal", function() {
            $(this).find(".modal-body").html("...");
        });

    $("#modal_kobo_token")
        .on("show.bs.modal", function(e) {
            var $modalBody = $(this).find(".modal-body");

            // Prevent static assets from loading multiple times
            var useCache = function(options) {
                options.async = true;
                options.cache = true;
            };
            preFilters.add(useCache);

            $.get(e.relatedTarget.href).done(function(content) {
                $modalBody.html(content);
                preFilters.remove(useCache);
            });
        })
        .on("hidden.bs.modal", function() {
            $(this).find(".modal-body").html("...");
             $("#config_delete_kobo_token").show();
        });

    $("#btndeletetoken").click(function() {
        //get data-id attribute of the clicked element
        var pathname = document.getElementsByTagName("script"), src = pathname[pathname.length-1].src;
        var path = src.substring(0,src.lastIndexOf("/"));
        // var domainId = $(this).value("domainId");
        $.ajax({
            method:"get",
            url: path + "/../../kobo_auth/deleteauthtoken/" + this.value,
        });
        $("#modalDeleteToken").modal("hide");
        $("#config_delete_kobo_token").hide();

    });

    $(window).resize(function() {
        $(".discover .row").isotope("layout");
    });

    $(".author-expand").click(function() {
        $(this).parent().find("a.author-name").slice($(this).data("authors-max")).toggle();
        $(this).parent().find("span.author-hidden-divider").toggle();
        $(this).html() === $(this).data("collapse-caption") ? $(this).html("(...)") : $(this).html($(this).data("collapse-caption"));
        $(".discover .row").isotope("layout");
    });

});
