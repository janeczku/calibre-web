/* This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
 *    Copyright (C) 2018 jkrehm, OzzieIsaacs
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

/* global Sortable,sortTrue */

Sortable.create(sortTrue, {
    group: "sorting",
    sort: true
});

// eslint-disable-next-line no-unused-vars
function sendData(path) {
    var elements;
    var counter;
    var maxElements;
    var tmp = [];

    elements = $(".list-group-item");
    maxElements = elements.length;

    var form = document.createElement("form");
    form.setAttribute("method", "post");
    form.setAttribute("action", path);

    for (counter = 0;counter < maxElements;counter++) {
        tmp[counter] = elements[counter].getAttribute("id");
        var hiddenField = document.createElement("input");
        hiddenField.setAttribute("type", "hidden");
        hiddenField.setAttribute("name", elements[counter].getAttribute("id"));
        hiddenField.setAttribute("value", String(counter + 1));
        form.appendChild(hiddenField);
    }
    document.body.appendChild(form);
    form.submit();
}
