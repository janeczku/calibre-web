/* This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
 *    Copyright (C) 2018 jkrehm
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

$(function() {
    $("#have_read_form").ajaxForm();
});

$("#have_read_cb").on("change", function() {
    $(this).closest("form").submit();
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

    $("#shelf-actions").on("click", "[data-shelf-action]", function (e) {
        e.preventDefault();

        $.get(this.href)
            .done(function() {
                var $this = $(this);
                switch ($this.data("shelf-action")) {
                    case "add":
                        $("#remove-from-shelves").append(
                            templates.remove({
                                add: this.href,
                                remove: $this.data("remove-href"),
                                content: this.textContent
                            })
                        );
                        break;
                    case "remove":
                        $("#add-to-shelves").append(
                            templates.add({
                                add: $this.data("add-href"),
                                remove: this.href,
                                content: this.textContent
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
