/* This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
 *    Copyright (C) 2018 OzzieIsaacs
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

var direction = $("#asc").data('order');  // 0=Descending order; 1= ascending order

var $list = $("#list").isotope({
    itemSelector: ".book",
    layoutMode: "fitRows",
    getSortData: {
        title: ".title"
    },
});


$("#desc").click(function() {
    if (direction === 0) {
        return;
    }
    $("#asc").removeClass("active");
    $("#desc").addClass("active");

    var page = $(this).data("id");
    $.ajax({
        method:"post",
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        url: getPath() + "/ajax/view",
        data: "{\"" + page + "\": {\"dir\": \"desc\"}}",
    });
    // invert sorting order to make already inverted start order working
    $list.isotope({
        sortBy: "name",
        sortAscending: !$list.data('isotope').options.sortAscending
    });
    direction = 0;
});

$("#asc").click(function() {
    if (direction === 1) {
        return;
    }
    $("#desc").removeClass("active");
    $("#asc").addClass("active");

    var page = $(this).data("id");
    $.ajax({
        method:"post",
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        url: getPath() + "/ajax/view",
        data: "{\"" + page + "\": {\"dir\": \"asc\"}}",
    });
    $list.isotope({
        sortBy: "name",
        sortAscending: !$list.data('isotope').options.sortAscending
    });
    direction = 1;
});

$("#all").click(function() {
    $(".char").removeClass("active");
    $("#all").addClass("active");
    // go through all elements and make them visible
    $list.isotope({ filter: function() {
        return true;
    }
    });
});

$(".char").click(function() {
    $(".char").removeClass("active");
    $(this).addClass("active");
    $("#all").removeClass("active");
    var character = this.innerText;
    $list.isotope({ filter: function() {
        return this.attributes["data-id"].value.charAt(0).toUpperCase() === character;
    }
    });
});
