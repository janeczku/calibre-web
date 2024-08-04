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

function getPath() {
    var jsFileLocation = $("script[src*=jquery]").attr("src");  // the js file path
    return jsFileLocation.substr(0, jsFileLocation.search("/static/js/libs/jquery.min.js"));  // the js folder path
}

function postButton(event, action, location=""){
    event.preventDefault();
    var newForm = jQuery('<form>', {
        "action": action,
        'target': "_top",
        'method': "post"
    }).append(jQuery('<input>', {
        'name': 'csrf_token',
        'value': $("input[name=\'csrf_token\']").val(),
        'type': 'hidden'
    })).appendTo('body')
    if(location !== "") {
        newForm.append(jQuery('<input>', {
            'name': 'location',
            'value': location,
            'type': 'hidden'
        })).appendTo('body');
    }
    newForm.submit();
}

function elementSorter(a, b) {
    a = +a.slice(0, -2);
    b = +b.slice(0, -2);
    if (a > b) return 1;
    if (a < b) return -1;
    return 0;
}

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
    var showOrHide = parseInt($this.val(), 10);
    // var showOrHideLast = $("#" + name + " option:last").val()
    for (var i = 0; i < $(this)[0].length; i++) {
        var element = parseInt($(this)[0][i].value, 10);
        if (element === showOrHide) {
            $("[data-related^=" + name + "][data-related*=-" + element + "]").show();
        } else {
            $("[data-related^=" + name + "][data-related*=-" + element + "]").hide();
        }
    }
});

// Generic control/related handler to show/hide fields based on a select' value
// this one is made to show all values if select value is not 0
$(document).on("change", "select[data-controlall]", function() {
    var $this = $(this);
    var name = $this.data("controlall");
    var showOrHide = parseInt($this.val(), 10);
    if (showOrHide) {
        $("[data-related=" + name + "]").show();
    } else {
        $("[data-related=" + name + "]").hide();
    }
});


$(document).on("click", ".postAction", function (event) {
    // $(".sendbutton").on("click", "body", function(event) {
    postButton(event, $(this).data('action'));
});


// Syntax has to be bind not on, otherwise problems with firefox
$(".container-fluid").bind("dragenter dragover", function () {
    if($("#btn-upload").length && !$('body').hasClass('shelforder')) {
        $(this).css('background', '#e6e6e6');
    }
    return false;
});

// Syntax has to be bind not on, otherwise problems with firefox
$(".container-fluid").bind("dragleave", function () {
    if($("#btn-upload").length && !$('body').hasClass('shelforder')) {
        $(this).css('background', '');
    }
    return false;
});

// Syntax has to be bind not on, otherwise problems with firefox
$(".container-fluid").bind('drop', function (e) {
    e.preventDefault()
    e.stopPropagation();
    if($("#btn-upload").length) {
        var files = e.originalEvent.dataTransfer.files;
        var test = $("#btn-upload")[0].accept;
        $(this).css('background', '');
        const dt = new DataTransfer();
        jQuery.each(files, function (index, item) {
            if (test.indexOf(item.name.substr(item.name.lastIndexOf('.'))) !== -1) {
                dt.items.add(item);
            }
        });
        if (dt.files.length) {
            $("#btn-upload")[0].files = dt.files;
            $("#form-upload").submit();
        }
    }
});

$("#btn-upload").change(function() {
    $("#form-upload").submit();
});

$("#form-upload").uploadprogress({
    redirect_url: getPath() + "/", //"{{ url_for('web.index')}}",
    uploadedMsg: $("#form-upload").data("message"), //"{{_('Upload done, processing, please wait...')}}",
    modalTitle: $("#form-upload").data("title"), //"{{_('Uploading...')}}",
    modalFooter: $("#form-upload").data("footer"), //"{{_('Close')}}",
    modalTitleFailed: $("#form-upload").data("failed") //"{{_('Error')}}"
});

$(document).ready(function() {
    var inp = $('#query').first()
    if (inp.length) {
        var val = inp.val()
        if (val.length) {
            inp.val('').blur().focus().val(val)
        }
    }
});

$(".session").click(function() {
    window.sessionStorage.setItem("back", window.location.pathname);
    window.sessionStorage.setItem("search", window.location.search);
});

$("#back").click(function() {
   var loc = sessionStorage.getItem("back");
   var param = sessionStorage.getItem("search");
   if (!loc) {
       loc = $(this).data("back");
   }
   sessionStorage.removeItem("back");
   sessionStorage.removeItem("search");
   if (param === null) {
       param = "";
   }
   window.location.href = loc + param;

});

function confirmDialog(id, dialogid, dataValue, yesFn, noFn) {
    var $confirm = $("#" + dialogid);
    $("#btnConfirmYes-"+ dialogid).off('click').click(function () {
        yesFn(dataValue);
        $confirm.modal("hide");
    });
    $("#btnConfirmNo-"+ dialogid).off('click').click(function () {
        if (typeof noFn !== 'undefined') {
            noFn(dataValue);
        }
        $confirm.modal("hide");
    });
    $.ajax({
        method:"post",
        dataType: "json",
        url: getPath() + "/ajax/loaddialogtexts/" + id,
        success: function success(data) {
            $("#header-"+ dialogid).html(data.header);
            $("#text-"+ dialogid).html(data.main);
        }
    });
    $confirm.modal('show');
}

$("#delete_confirm").click(function(event) {
    //get data-id attribute of the clicked element
    var deleteId = $(this).data("delete-id");
    var bookFormat = $(this).data("delete-format");
    var ajaxResponse = $(this).data("ajax");
    if (bookFormat) {
        postButton(event, getPath() + "/delete/" + deleteId + "/" + bookFormat);
    } else {
        if (ajaxResponse) {
            path = getPath() + "/ajax/delete/" + deleteId;
            $.ajax({
                method:"post",
                url: path,
                timeout: 900,
                success:function(data) {
                    data.forEach(function(item) {
                        if (!jQuery.isEmptyObject(item)) {
                            if (item.format != "") {
                                $("button[data-delete-format='"+item.format+"']").addClass('hidden');
                            }
                            $( ".navbar" ).after( '<div class="row-fluid text-center" >' +
                                '<div id="flash_'+item.type+'" class="alert alert-'+item.type+'">'+item.message+'</div>' +
                                '</div>');
                        }
                    });
                    $("#books-table").bootstrapTable("refresh");
                }
            });
        } else {
            var loc = sessionStorage.getItem("back");
            if (!loc) {
                loc = $(this).data("back");
            }
            sessionStorage.removeItem("back");
            postButton(event, getPath() + "/delete/" + deleteId, location=loc);
        }
    }
});

//triggered when modal is about to be shown
$("#deleteModal").on("show.bs.modal", function(e) {
    //get data-id attribute of the clicked element and store in button
    var bookId = $(e.relatedTarget).data("delete-id");
    var bookfomat = $(e.relatedTarget).data("delete-format");
    if (bookfomat) {
        $("#book_format").removeClass('hidden');
        $("#book_complete").addClass('hidden');
    } else {
        $("#book_complete").removeClass('hidden');
        $("#book_format").addClass('hidden');
    }
    $(e.currentTarget).find("#delete_confirm").data("delete-id", bookId);
    $(e.currentTarget).find("#delete_confirm").data("delete-format", bookfomat);
    $(e.currentTarget).find("#delete_confirm").data("ajax", $(e.relatedTarget).data("ajax"));
});

$(function() {
    var updateTimerID;
    var updateText;

    // Allow ajax prefilters to be added/removed dynamically
    // eslint-disable-next-line new-cap
    var preFilters = $.Callbacks();
    $.ajaxPrefilter(preFilters.fire);

    // equip all post requests with csrf_token
    var csrftoken = $("input[name='csrf_token']").val();
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken)
            }
        }
    });

    function restartTimer() {
        $("#spinner").addClass("hidden");
        $("#RestartDialog").modal("hide");
    }

    function cleanUp() {
        clearInterval(updateTimerID);
        $("#spinner2").hide();
        $("#DialogFinished").removeClass("hidden");
        $("#check_for_update").removeClass("hidden");
        $("#perform_update").addClass("hidden");
        $("#message").alert("close");
        $("#update_table > tbody > tr").each(function () {
            if ($(this).attr("id") !== "current_version") {
                $(this).closest("tr").remove();
            }
        });
    }

    function updateTimer() {
        var no_response = 0;
        $.ajax({
            dataType: "json",
            url: getPath() + "/get_updater_status",
            success: function success(data) {
                $("#DialogContent").html(updateText[data.status]);
                if (data.status > 6) {
                    cleanUp();
                }
            },
            error: function error() {
                // Server has to restart in 60 Sek. otherwise output error message
                no_response += 1;
                if (no_response > 30) {
                    $("#DialogContent").html(updateText[11]);
                    cleanUp();
                }
            },
            timeout: 2000
        });
    }

    function fillFileTable(path, type, folder, filt) {
        var request_path = "/ajax/pathchooser/";
        $.ajax({
            dataType: "json",
            data: {
                path: path,
                folder: folder,
                filter: filt
            },
            url: getPath() + request_path,
            success: function success(data) {
                if ($("#element_selected").text() ==="") {
                    $("#element_selected").text(data.cwd);
                }
                $("#file_table > tbody > tr").each(function () {
                    if ($(this).attr("id") !== "parent") {
                        $(this).closest("tr").remove();
                    } else {
                        if(data.absolute && data.parentdir !== "") {
                           $(this)[0].attributes['data-path'].value  = data.parentdir;
                        } else {
                            $(this)[0].attributes['data-path'].value  = "..";
                        }
                    }
                });
                if (data.parentdir !== "") {
                    $("#parent").removeClass('hidden')
                } else {
                    $("#parent").addClass('hidden')
                }
                data.files.forEach(function(entry) {
                    if(entry.type === "dir") {
                        var type = "<span class=\"glyphicon glyphicon-folder-close\"></span>";
                } else {
                    var type = "";
                }
                    $("<tr class=\"tr-clickable\" data-type=\"" + entry.type + "\" data-path=\"" +
                        entry.fullpath + "\"><td>" + type + "</td><td>" + entry.name + "</td><td>" +
                        entry.size + "</td></tr>").appendTo($("#file_table"));
                });
            },
            timeout: 2000
        });
    }

    $(".discover .row").isotope({
        // options
        itemSelector : ".book",
        layoutMode : "fitRows"
    });

    if ($(".load-more").length && $(".next").length) {
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
            $(".pagination").addClass("hidden").html(() => $(response).find(".pagination").html());
            if ($("body").hasClass("blur")) {
                $(" a:not(.dropdown-toggle) ")
                  .removeAttr("data-toggle");
            }
            $(".load-more .row").isotope( "appended", $(data), null );
        });

        // fix for infinite scroll on CaliBlur Theme (#981)
        if ($("body").hasClass("blur")) {
            $(".col-sm-10").bind("scroll", function () {
                if (
                    $(this).scrollTop() + $(this).innerHeight() >=
                    $(this)[0].scrollHeight
                ) {
                    $loadMore.infiniteScroll("loadNextPage");
                    window.history.replaceState({}, null, $loadMore.infiniteScroll("getAbsolutePath"));
                }
            });
        }
    }

    $("#restart").click(function() {
        $.ajax({
            method:"post",
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            url: getPath() + "/shutdown",
            data: JSON.stringify({"parameter":0}),
            success: function success() {
                $("#spinner").show();
                setTimeout(restartTimer, 3000);
            }
        });
    });
    $("#shutdown").click(function() {
        $.ajax({
            method:"post",
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            url: getPath() + "/shutdown",
            data: JSON.stringify({"parameter":1}),
            success: function success(data) {
                return alert(data.text);
            }
        });
    });
    $("#check_for_update").click(function() {
        var $this = $(this);
        var buttonText = $this.html();
        $this.html("...");
        $("#DialogContent").html("");
        $("#DialogFinished").addClass("hidden");
        $("#update_error").addClass("hidden");
        if ($("#message").length) {
            $("#message").alert("close");
        }
        $.ajax({
            dataType: "json",
            url: getPath() + "/get_update_status",
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
    $("#admin_refresh_cover_cache").click(function() {
        confirmDialog("admin_refresh_cover_cache", "GeneralChangeModal", 0, function () {
            $.ajax({
                method:"post",
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                url: getPath() + "/ajax/updateThumbnails",
            });
        });
    });

    $("#restart_database").click(function() {
        $("#DialogHeader").addClass("hidden");
        $("#DialogFinished").addClass("hidden");
        $("#DialogContent").html("");
        $("#spinner2").show();
        $.ajax({
            method:"post",
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            url: getPath() + "/shutdown",
            data: JSON.stringify({"parameter":2}),
            success: function success(data) {
                $("#spinner2").hide();
                $("#DialogContent").html(data.text);
                $("#DialogFinished").removeClass("hidden");
            }
        });
    });
    $("#metadata_backup").click(function() {
        $("#DialogHeader").addClass("hidden");
        $("#DialogFinished").addClass("hidden");
        $("#DialogContent").html("");
        $("#spinner2").show();
        $.ajax({
            method: "post",
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            url: getPath() + "/metadata_backup",
            success: function success(data) {
                $("#spinner2").hide();
                $("#DialogContent").html(data.text);
                $("#DialogFinished").removeClass("hidden");
            }
        });
    });
    $("#perform_update").click(function() {
        $("#DialogHeader").removeClass("hidden");
        $("#spinner2").show();
        $.ajax({
            type: "POST",
            dataType: "json",
            data: { start: "True" },
            url: getPath() + "/get_updater_status",
            success: function success(data) {
                updateText = data.text;
                $("#DialogContent").html(updateText[data.status]);
                updateTimerID = setInterval(updateTimer, 2000);
            }
        });
    });

    // Init all data control handlers to default
    $("input[data-control]").trigger("change");
    $("select[data-control]").trigger("change");
    $("select[data-controlall]").trigger("change");

    $("#bookDetailsModal")
        .on("show.bs.modal", function(e) {
            $("#flash_danger").remove();
            $("#flash_success").remove();
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
                $("#back").remove();
            });
        })
        .on("hidden.bs.modal", function() {
            $(this).find(".modal-body").html("...");
        });

    $("#modal_kobo_token")
        .on("show.bs.modal", function(e) {
            $(e.relatedTarget).one('focus', function(e){$(this).blur();});
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
            $("#kobo_full_sync").show();
        });

    $("#config_delete_kobo_token").click(function() {
        confirmDialog(
            $(this).attr('id'),
            "GeneralDeleteModal",
            $(this).data('value'),
            function (value) {
                $.ajax({
                    method: "post",
                    url: getPath() + "/kobo_auth/deleteauthtoken/" + value,
                });
                $("#config_delete_kobo_token").hide();
                $("#kobo_full_sync").hide();
            }
        );
    });

    $("#toggle_order_shelf").click(function() {
        $("#new").toggleClass("disabled");
        $("#old").toggleClass("disabled");
        $("#asc").toggleClass("disabled");
        $("#desc").toggleClass("disabled");
        $("#auth_az").toggleClass("disabled");
        $("#auth_za").toggleClass("disabled");
        $("#pub_new").toggleClass("disabled");
        $("#pub_old").toggleClass("disabled");
        var alternative_text = $("#toggle_order_shelf").data('alt-text');
        $("#toggle_order_shelf").data('alt-text', $("#toggle_order_shelf").html());
        $("#toggle_order_shelf").html(alternative_text);
    });

    $("#btndeluser").click(function() {
        confirmDialog(
            $(this).attr('id'),
            "GeneralDeleteModal",
            $(this).data('value'),
            function(value){
                var subform = $('#user_submit').closest("form");
                subform.submit(function(eventObj) {
                    $(this).append('<input type="hidden" name="delete" value="True" />');
                    return true;
                });
                subform.submit();
            }
        );
    });

    $("#kobo_full_sync").click(function() {
        confirmDialog(
           "btnfullsync",
            "GeneralDeleteModal",
            $(this).data('value'),
            function(userid) {
                if (userid) {
                    path = getPath() + "/ajax/fullsync/" + userid
                } else {
                    path = getPath() + "/ajax/fullsync"
                }
                $.ajax({
                    method:"post",
                    url: path,
                    timeout: 900,
                    success:function(data) {
                        data.forEach(function(item) {
                            if (!jQuery.isEmptyObject(item)) {
                                $( ".navbar" ).after( '<div class="row-fluid text-center" >' +
                                    '<div id="flash_'+item.type+'" class="alert alert-'+item.type+'">'+item.message+'</div>' +
                                    '</div>');
                            }
                        });
                    }
                });
            }
        );
    });

    $("#user_submit").click(function() {
        this.closest("form").submit();
    });

    function handle_response(data) {
        if (!jQuery.isEmptyObject(data)) {
            data.forEach(function (item) {
                $(".navbar").after('<div class="row-fluid text-center">' +
                    '<div id="flash_' + item.type + '" class="alert alert-' + item.type + '">' + item.message + '</div>' +
                    '</div>');
            });
        }
    }

    $('.collapse').on('shown.bs.collapse', function(){
        $(this).parent().find(".glyphicon-plus").removeClass("glyphicon-plus").addClass("glyphicon-minus");
    }).on('hidden.bs.collapse', function(){
    $(this).parent().find(".glyphicon-minus").removeClass("glyphicon-minus").addClass("glyphicon-plus");
    });

    function changeDbSettings() {
        $("#db_submit").closest('form').submit();
    }

    $("#db_submit").click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        this.blur();
        $.ajax({
            method:"post",
            dataType: "json",
            url: getPath() + "/ajax/simulatedbchange",
            data: {config_calibre_dir: $("#config_calibre_dir").val(), csrf_token: $("input[name='csrf_token']").val()},
            success: function success(data) {
                if ( data.change ) {
                    if ( data.valid ) {
                        confirmDialog(
                            "db_submit",
                            "GeneralChangeModal",
                            0,
                            changeDbSettings
                        );
                    }
                    else {
                        $("#InvalidDialog").modal('show');
                    }
                } else {
                    changeDbSettings();
                }
            }
        });
    });

    $("#config_submit").click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        this.blur();
        window.scrollTo({top: 0, behavior: 'smooth'});
        var request_path = "/admin/ajaxconfig";
        $("#flash_success").remove();
        $("#flash_danger").remove();
        $.post(getPath() + request_path, $(this).closest("form").serialize(), function(data) {
            $('#config_upload_formats').val(data.config_upload);
            if(data.reboot) {
                $("#spinning_success").show();
                var rebootInterval = setInterval(function(){
                    $.get({
                        url:getPath() + "/admin/alive",
                        success: function (d, statusText, xhr) {
                            if (xhr.status < 400) {
                                $("#spinning_success").hide();
                                clearInterval(rebootInterval);
                                if (data.result) {
                                    handle_response(data.result);
                                    data.result = "";
                                }
                            }
                        },
                    });
                }, 1000);
            } else {
                handle_response(data.result);
            }
        });
    });

    $("#delete_shelf").click(function(event) {
        confirmDialog(
            $(this).attr('id'),
            "GeneralDeleteModal",
            $(this).data('value'),
            function(value){
                postButton(event, $("#delete_shelf").data("action"));
            }
        );

    });

    $("#fileModal").on("show.bs.modal", function(e) {
        var target = $(e.relatedTarget);
        var path = $("#" + target.data("link"))[0].value;
        var folder = target.data("folderonly");
        var filter = target.data("filefilter");
        $("#element_selected").text(path);
        $("#file_confirm").data("link", target.data("link"));
        $("#file_confirm").data("folderonly", (typeof folder === 'undefined') ? false : true);
        $("#file_confirm").data("filefilter", (typeof filter === 'undefined') ? "" : filter);
        $("#file_confirm").data("newfile", target.data("newfile"));
        fillFileTable(path,"dir", folder, filter);
    });

    $("#file_confirm").click(function() {
        $("#" + $(this).data("link"))[0].value = $("#element_selected").text()
    });

    $(document).on("click", ".tr-clickable", function() {
        var path = this.attributes["data-path"].value;
        var type = this.attributes["data-type"].value;
        var folder = $(file_confirm).data("folderonly");
        var filter = $(file_confirm).data("filefilter");
        var newfile = $(file_confirm).data("newfile");
        if (newfile !== "") {
            $("#element_selected").text(path + $("#new_file".text()));
        } else {
            $("#element_selected").text(path);
        }
        if(type === "dir") {
            fillFileTable(path, type, folder, filter);
        }
    });

    $(window).resize(function() {
        $(".discover .row").isotope("layout");
    });

    $("#import_ldap_users").click(function() {
        $("#DialogHeader").addClass("hidden");
        $("#DialogFinished").addClass("hidden");
        $("#DialogContent").html("");
        $("#spinner2").show();
        $.ajax({
            method:"post",
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            url: getPath() + "/import_ldap_users",
            success: function success(data) {
                $("#spinner2").hide();
                $("#DialogContent").html(data.text);
                $("#DialogFinished").removeClass("hidden");
            }
        });
    });

    $(".author-expand").click(function() {
        $(this).parent().find("a.author-name").slice($(this).data("authors-max")).toggle();
        $(this).parent().find("span.author-hidden-divider").toggle();
        $(this).html() === $(this).data("collapse-caption") ? $(this).html("(...)") : $(this).html($(this).data("collapse-caption"));
        $(".discover .row").isotope("layout");
    });

    $(".update-view").click(function(e) {
        var view = $(this).data("view");
        e.preventDefault();
        e.stopPropagation();
        $.ajax({
            method:"post",
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            url: getPath() + "/ajax/view",
            data: "{\"series\": {\"series_view\": \""+ view +"\"}}",
            success: function success() {
                location.reload();
            }
        });
    });
});
