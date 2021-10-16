/* This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
 *    Copyright (C) 2021 Ozzieisaacs
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

$(document).ready(function() {
    //to int
    $("#area").width($("#area").width());
    $("#content").width($("#content").width());
    //bind text
    $("#content").load($("#readmain").data('load'), function(textStr) {
        $(this).height($(this).parent().height()*0.95);
        $(this).text(textStr);
    });
    //keybind
    $(document).keydown(function(event){
        if(event.keyCode == 37){
            prevPage();
        }
        if(event.keyCode == 39){
            nextPage();
        }
    });
    //click
    $( "#left" ).click(function() {
        prevPage();
    });
    $( "#right" ).click(function() {
        nextPage();
    });
    $("#readmain").swipe( {
        swipeRight:function() {
            prevPage();
        },
        swipeLeft:function() {
            nextPage();
        },
    });

    //bind mouse
    $(window).bind('DOMMouseScroll mousewheel', function(event) {
        var delta = 0;
        if (event.originalEvent.wheelDelta) {
            delta = event.originalEvent.wheelDelta;
        } else if (event.originalEvent.detail) {
            delta = event.originalEvent.detail*-1;
        }
        if (delta >= 0) {
            prevPage();
        } else {
            nextPage();
        }
    });

    //page animate
    var origwidth = $("#content")[0].getBoundingClientRect().width;
    var gap = 20;
    function prevPage() {
        if($("#content").offset().left > 0) {
            return;
        }
        leftoff = $("#content").offset().left;
        leftoff = leftoff+origwidth+gap;
        $("#content").offset({left:leftoff});
    }
    function nextPage() {
        leftoff = $("#content").offset().left;
        leftoff = leftoff-origwidth-gap;
        if (leftoff + $("#content")[0].scrollWidth < 0) {
            return;
        }
        $("#content").offset({left:leftoff});
    }
});
