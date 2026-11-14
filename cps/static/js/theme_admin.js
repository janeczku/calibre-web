/* This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
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

/* global bootstrap */

$(function () {
    var $root = $("#theme-admin");
    if (!$root.length) {
        return;
    }
    var csrfToken = $root.closest("form").find("input[name='csrf_token']").val();
    var writable = $root.attr("data-writable") === "true";
    var failedText = $root.attr("data-msg-failed");
    var expiredText = $root.attr("data-msg-expired");
    var $status = $("#theme-status");
    var $file = $("#theme-file");

    function setStatus(lines) {
        $status.empty();
        lines.forEach(function (line) {
            $("<div>").text(line).appendTo($status);
        });
    }

    function setBusy(busy) {
        $("#theme-check-updates").prop("disabled", busy);
        $("#theme-upload, #theme-table .theme-update").prop("disabled", busy || !writable);
    }

    // Resolves with the JSON body; rejects with an Error carrying a message fit for the status line.
    // A non-JSON 400 (expired CSRF token) says the page expired; other non-JSON answers get the generic message.
    function post(url, data) {
        return fetch(url, {
            method: "POST",
            body: data,
            credentials: "same-origin",
            headers: {"X-CSRFToken": csrfToken}
        }).catch(function () {
            throw new Error(failedText);
        }).then(function (resp) {
            return resp.json().catch(function () {
                return null;
            }).then(function (json) {
                if (resp.ok && json) {
                    return json;
                }
                if (json && typeof json.error === "string") {
                    throw new Error(json.error);
                }
                // A 400 that is not ours (JSON) is the CSRF error page of an expired form.
                throw new Error(resp.status === 400 ? expiredText : failedText);
            });
        });
    }

    // One pass with a function replacer, so "$&" or "{old}" inside a value is inserted literally.
    function fill(template, values) {
        return template.replace(/\{(new|old|version)\}/g, function (match, key) {
            return key in values ? String(values[key]) : match;
        });
    }

    function formData(fields) {
        var data = new FormData();
        Object.keys(fields).forEach(function (key) {
            data.append(key, fields[key]);
        });
        return data;
    }

    // Shows a modal; resolves true only if its .theme-confirm button was used. Cancel, the close button
    // and Esc all resolve false.
    function ask(id) {
        return new Promise(function (resolve) {
            var el = document.getElementById(id);
            var modal = bootstrap.Modal.getOrCreateInstance(el);
            var confirmed = false;
            // Bootstrap ignores hide() while the modal is still opening; a click then must not count as a decision.
            var $confirm = $(el).find(".theme-confirm").prop("disabled", true);
            $confirm.off("click").on("click", function () {
                confirmed = true;
                modal.hide();
            });
            $(el).one("shown.bs.modal", function () {
                $confirm.prop("disabled", false);
            });
            $(el).one("hidden.bs.modal", function () {
                resolve(confirmed);
            });
            modal.show();
        });
    }

    function confirmFlow(summary) {
        var needsTrust = summary.has_templates || summary.has_js;
        var step = Promise.resolve(true);
        if (summary.installed) {
            var $text = $("#themeVersionModal .theme-version-text");
            var unknown = $text.attr("data-unknown");
            $text.text(fill($text.attr("data-template"), {
                "new": summary.version || unknown,
                old: summary.installed_version || unknown
            }));
            step = ask("themeVersionModal");
        }
        return step.then(function (ok) {
            if (!ok || !needsTrust) {
                return ok;
            }
            $("#themeTrustModal .trust-templates").toggleClass("d-none", !summary.has_templates);
            $("#themeTrustModal .trust-js").toggleClass("d-none", !summary.has_js);
            return ask("themeTrustModal");
        }).then(function (ok) {
            if (!ok) {
                return post($root.attr("data-discard-url"), formData({token: summary.token}))
                    .catch(function () {});
            }
            var fields = {token: summary.token};
            if (summary.installed) {
                fields.confirm_version = summary.version || "";
            }
            if (needsTrust) {
                fields.trust_code = "true";
            }
            return post($root.attr("data-commit-url"), formData(fields)).then(function () {
                location.reload();
            });
        });
    }

    function install(request) {
        setBusy(true);
        setStatus([]);
        request().then(confirmFlow).catch(function (err) {
            setStatus([err.message || failedText]);
        }).then(function () {
            setBusy(false);
        });
    }

    $("#theme-upload").on("click", function () {
        $file.val("");
        $file.trigger("click");
    });

    $file.on("change", function () {
        var file = this.files[0];
        if (!file) {
            return;
        }
        install(function () {
            return post($root.attr("data-stage-url"), formData({file: file}));
        });
    });

    $("#theme-table").on("click", ".theme-update", function () {
        var identifier = $(this).attr("data-identifier");
        install(function () {
            return post($root.attr("data-stage-update-url"), formData({identifier: identifier}));
        });
    });

    function comparable(version) {
        return /^[0-9]+(\.[0-9]+)*$/.test(String(version).replace(/^[vV]/, ""));
    }

    $("#theme-check-updates").on("click", function () {
        setBusy(true);
        setStatus([]);
        $("#theme-table .theme-update").remove();
        post($root.attr("data-check-url"), new FormData()).then(function (result) {
            var lines = [];
            Object.keys(result).forEach(function (identifier) {
                var entry = result[identifier];
                var $row = $("#theme-table tbody tr").filter(function () {
                    return $(this).attr("data-identifier") === identifier;
                });
                var name = $row.find(".theme-name").text().trim() || identifier;
                var installed = $row.children("td").eq(1).text().trim();
                if (entry.error) {
                    lines.push(name + ": " + entry.error);
                } else if (entry.update_available) {
                    $("<button type=\"button\" class=\"btn btn-link p-0 border-0 align-baseline theme-update\"></button>")
                        .attr("data-identifier", identifier)
                        .text(fill($root.attr("data-msg-update"), {version: entry.latest}))
                        .appendTo($row.find(".theme-action"));
                } else if (entry.latest && !(comparable(entry.latest) && comparable(installed))) {
                    lines.push(name + ": " + fill($root.attr("data-msg-latest"), {version: entry.latest}));
                } else {
                    lines.push(name + ": " + $root.attr("data-msg-up-to-date"));
                }
            });
            setStatus(Object.keys(result).length ? lines : [$root.attr("data-msg-no-repository")]);
        }).catch(function (err) {
            setStatus([err.message || failedText]);
        }).then(function () {
            setBusy(false);
        });
    });
});
