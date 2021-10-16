/* This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
 *    Copyright (C) 2017-2021  jkrehm, OzzieIsaacs
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

(function () {
    // Poll the server to check if the user has authenticated
    var t = setInterval(function () {
        $.post(getPath() + "/ajax/verify_token", { token: $("#verify_url").data("token") })
            .done(function(response) {
                if (response.status === 'success') {
                // Wait a tick so cookies are updated
                setTimeout(function () {
                    window.location.href = getPath() + '/';
                }, 0);
            }
        })
        .fail(function (xhr) {
            clearInterval(t);
            var response = JSON.parse(xhr.responseText);
            alert(response.message);
        });
    }, 5000);
})()
