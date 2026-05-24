/* This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
 *    Copyright (C) 2025 akharlamov
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

function incrementProgress() {
    let pb = document.getElementById('progressbar');
    let val = parseInt(pb.getAttribute('aria-valuenow') || '0') + 1;
    let w = Math.round(100 * val / parseInt(pb.getAttribute('aria-valuemax') || '10'));

    pb.setAttribute('style', `width:${w}%`);
    pb.setAttribute('aria-valuenow', `${val}`);
}

$(document).ready(function () {
        setTimeout(function () {
            location.reload();
        }, 5000);
        setInterval(incrementProgress, 1000);
    }
);
