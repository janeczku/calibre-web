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

// Upon loading load the logfile for the first option (event log)
$(function() {
    if ($("#log_group input").length) {
        var element = $("#log_group input[type='radio']:checked").val();
        init(element);
    }
});

// After change the radio option load the corresponding log file
$("#log_group input").on("change", function() {
    var element = $("#log_group input[type='radio']:checked").val();
    init(element);
});


// Handle reloading of the log file and display the content
function init(logType) {
    var d = document.getElementById("renderer");
    d.innerHTML = "loading ...";

    $.ajax({
        url: getPath() + "/ajax/log/" + logType,
        datatype: "text",
        cache: false
    })
        .done( function(data) {
            var text;
            $("#renderer").text("");
            text = (data).split("\n");
            // console.log(text.length);
            for (var i = 0; i < text.length; i++) {
                $("#renderer").append( "<div>" + _sanitize(text[i]) + "</div>" );
            }
        });
}


function _sanitize(t) {
    t = t
        .replace(/&/g, "&amp;")
        .replace(/ /g, "&nbsp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    return t;
}

