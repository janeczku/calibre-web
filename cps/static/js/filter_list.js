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
var sort = 0;       // Show sorted entries

$("#sort_name").click(function() {
    $("#sort_name").toggleClass("active");
    var className = $("h1").attr("Class") + "_sort_name";
    var obj = {};
    obj[className] = sort;

    var count = 0;
    var index = 0;
    var store;
    // Append 2nd half of list to first half for easier processing
    var cnt = $("#second").contents();
    $("#list").append(cnt);
    // Count no of elements
    var listItems = $("#list").children(".row");
    var listlength = listItems.length;
    // check for each element if its Starting character matches
    $(".row").each(function() {
        if ( sort === 1) {
            store = this.attributes["data-name"];
        } else {
            store = this.attributes["data-id"];
        }
        $(this).find("a").html(store.value);
        if ($(this).css("display") !== "none") {
            count++;
        }
    });

    // Find count of middle element
    if (count > 20) {
        var middle = parseInt(count / 2, 10) + (count % 2);
        // search for the middle of all visibe elements
        $(".row").each(function() {
            index++;
            if ($(this).css("display") !== "none") {
                middle--;
                if (middle <= 0) {
                    return false;
                }
            }
        });
        // Move second half of visible elements
        $("#second").append(listItems.slice(index, listlength));
    }
    sort = (sort + 1) % 2;
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
    var index = 0;
    var list = $("#list");
    var second = $("#second");
    // var cnt = ;
    list.append(second.contents());
    var listItems = list.children(".row");
    var reversed, elementLength, middle;
    reversed = listItems.get().reverse();
    elementLength = reversed.length;
    // Find count of middle element
    var count = $(".row:visible").length;
    if (count > 20) {
        middle = parseInt(count / 2, 10) + (count % 2);

        //var middle = parseInt(count / 2) + (count % 2);
        // search for the middle of all visible elements
        $(reversed).each(function() {
            index++;
            if ($(this).css("display") !== "none") {
                middle--;
                if (middle <= 0) {
                    return false;
                }
            }
        });

        list.append(reversed.slice(0, index));
        second.append(reversed.slice(index, elementLength));
    } else {
        list.append(reversed.slice(0, elementLength));
    }
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
    var index = 0;
    var list = $("#list");
    var second = $("#second");
    list.append(second.contents());
    var listItems = list.children(".row");
    var reversed = listItems.get().reverse();
    var elementLength = reversed.length;

    // Find count of middle element
    var count = $(".row:visible").length;
    if (count > 20) {
        var middle = parseInt(count / 2, 10) + (count % 2);

        //var middle = parseInt(count / 2) + (count % 2);
        // search for the middle of all visible elements
        $(reversed).each(function() {
            index++;
            if ($(this).css("display") !== "none") {
                middle--;
                if (middle <= 0) {
                    return false;
                }
            }
        });

        // middle = parseInt(elementLength / 2) + (elementLength % 2);
        list.append(reversed.slice(0, index));
        second.append(reversed.slice(index, elementLength));
    } else {
        list.append(reversed.slice(0, elementLength));
    }
    direction = 1;
});

$("#all").click(function() {
    $("#all").addClass("active");
    $(".char").removeClass("active");
    var cnt = $("#second").contents();
    $("#list").append(cnt);
    // Find count of middle element
    var listItems = $("#list").children(".row");
    var listlength = listItems.length;
    var middle = parseInt(listlength / 2, 10) + (listlength % 2);
    // go through all elements and make them visible
    listItems.each(function() {
        $(this).show();
    });
    // Move second half of all elements
    if (listlength > 20) {
        $("#second").append(listItems.slice(middle, listlength));
    }
});

$(".char").click(function() {
    $(".char").removeClass("active");
    $(this).addClass("active");
    $("#all").removeClass("active");
    var character = this.innerText;
    var count = 0;
    var index = 0;
    // Append 2nd half of list to first half for easier processing
    var cnt = $("#second").contents();
    $("#list").append(cnt);
    // Count no of elements
    var listItems = $("#list").children(".row");
    var listlength = listItems.length;
    // check for each element if its Starting character matches
    $(".row").each(function() {
        if (this.attributes["data-id"].value.charAt(0).toUpperCase() !== character) {
            $(this).hide();
        } else {
            $(this).show();
            count++;
        }
    });
    if (count > 20) {
        // Find count of middle element
        var middle = parseInt(count / 2, 10) + (count % 2);
        // search for the middle of all visibe elements
        $(".row").each(function() {
            index++;
            if ($(this).css("display") !== "none") {
                middle--;
                if (middle <= 0) {
                    return false;
                }
            }
        });
        // Move second half of visible elements
        $("#second").append(listItems.slice(index, listlength));
    }
});
