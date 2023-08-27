/* This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
 *    Copyright (C) 2018-2023 jkrehm, OzzieIsaacs
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

/* global _ */

function handleResponse (data) {
    $(".row-fluid.text-center").remove();
    $("#flash_danger").remove();
    $("#flash_success").remove();
    if (!jQuery.isEmptyObject(data)) {
        if($("#bookDetailsModal").is(":visible")) {
            data.forEach(function (item) {
                $(".modal-header").after('<div id="flash_' + item.type +
                    '" class="text-center alert alert-' + item.type + '">' + item.message + '</div>');
            });
        } else {
            data.forEach(function (item) {
                $(".navbar").after('<div class="row-fluid text-center">' +
                    '<div id="flash_' + item.type + '" class="alert alert-' + item.type + '">' + item.message + '</div>' +
                    '</div>');
            });
        }
    }
}
$(".sendbtn-form").click(function() {
    $.ajax({
        method: 'post',
        url: $(this).data('href'),
        data: {csrf_token: $("input[name='csrf_token']").val()},
        success: function (data) {
            handleResponse(data)
        }
    })
});

$(function() {
    $("#have_read_form").ajaxForm();
});

$("#have_read_cb").on("change", function() {
    $.ajax({
        url: this.closest("form").action,
        method:"post",
        data: $(this).closest("form").serialize(),
        error: function(response) {
            var data = [{type:"danger", message:response.responseText}]
            // $("#flash_success").parent().remove();
            $("#flash_danger").remove();
            $(".row-fluid.text-center").remove();
            if (!jQuery.isEmptyObject(data)) {
                $("#have_read_cb").prop("checked", !$("#have_read_cb").prop("checked"));
                if($("#bookDetailsModal").is(":visible")) {
                    data.forEach(function (item) {
                        $(".modal-header").after('<div id="flash_' + item.type +
                            '" class="text-center alert alert-' + item.type + '">' + item.message + '</div>');
                    });
                } else
                {
                    data.forEach(function (item) {
                        $(".navbar").after('<div class="row-fluid text-center" >' +
                            '<div id="flash_' + item.type + '" class="alert alert-' + item.type + '">' + item.message + '</div>' +
                            '</div>');
                    });
                }
            }
        }
    });
});

$(function() {
    $("#archived_form").ajaxForm();
});

$("#archived_cb").on("change", function() {
    $(this).closest("form").submit();
});

(function() {
    var templates = {
        add: _.template(
            $("#template-shelf-add").html()
        ),
        remove: _.template(
            $("#template-shelf-remove").html()
        )
    };

    $("#add-to-shelves, #remove-from-shelves").on("click", "[data-shelf-action]", function (e) {
        e.preventDefault();
        $.ajax({
                url: $(this).data('href'),
                method:"post",
                data: {csrf_token:$("input[name='csrf_token']").val()},
            })
            .done(function() {
                var $this = $(this);
                switch ($this.data("shelf-action")) {
                    case "add":
                        $("#remove-from-shelves").append(
                            templates.remove({
                                add: $this.data('href'),
                                remove: $this.data("remove-href"),
                                content: $("<div>").text(this.textContent).html()
                            })
                        );
                        break;
                    case "remove":
                        $("#add-to-shelves").append(
                            templates.add({
                                add: $this.data("add-href"),
                                remove: $this.data('href'),
                                content: $("<div>").text(this.textContent).html(),
                            })
                        );
                        break;
                }
                this.parentNode.removeChild(this);
            }.bind(this))
            .fail(function(xhr) {
                var $msg = $("<span/>", { "class": "text-danger"}).text(xhr.responseText);
                $("#shelf-action-status").html($msg);

                setTimeout(function() {
                    $msg.remove();
                }, 10000);
            });
    });
})();
