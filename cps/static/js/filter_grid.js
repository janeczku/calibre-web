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

var direction = 0;  // Descending order
var sort = 0;       // Show sorted entries

$("#sort_name").click(function() {
    var count = 0;
    var index = 0;
    var store;
    // Append 2nd half of list to first half for easier processing
    var cnt = $("#second").contents();
    $("#list").append(cnt);
    // Count no of elements
    var listItems = $("#list").children(".sortable");
    var listlength = listItems.length;
    // check for each element if its Starting character matches
    $(".sortable").each(function() {
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
    /*listItems.sort(function(a,b){
        return $(a).children()[1].innerText.localeCompare($(b).children()[1].innerText)
    });*/
    // Find count of middle element
    if (count > 20) {
        var middle = parseInt(count / 2) + (count % 2);
        // search for the middle of all visibe elements
        $(".sortable").each(function() {
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
    var items = $(".sortable").get();
    $("#list").html(items.reverse());
    return;
    direction = 0;
});

$("#asc").click(function() {
    if (direction === 1) {
        return;
    }
    var items = $(".sortable").get();
    $("#list").html(items.reverse());
    return;
    direction = 1;
});

$("#all").click(function() {
    // go through all elements and make them visible
    $(".sortable").each(function() {
        $(this).show();
    });
    // We need to trigger the resize event to have all the grid item to re-align.
    window.dispatchEvent(new Event('resize'));
});

$(".char").click(function() {
    var character = this.innerText;
    $(".sortable").each(function() {
        if (this.attributes["data-id"].value.charAt(0).toUpperCase() !== character) {
            $(this).hide();
        } else {
            $(this).show();
        }
    });
    // We need to trigger the resize event to have all the grid item to re-align.
    window.dispatchEvent(new Event('resize'));

});
