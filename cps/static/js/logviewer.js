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

// Global state
var logData = [];
var currentFilters = new Set();
var searchTerm = "";

// Upon loading load the logfile for the first option (event log)
$(function() {
    if ($("#log_group input").length) {
        var element = $("#log_group input[type='radio']:checked").val();
        init(element);
    }

    // Set up event listeners
    setupEventListeners();
});

// After change the radio option load the corresponding log file
$("#log_group input").on("change", function() {
    var element = $("#log_group input[type='radio']:checked").val();
    init(element);
});

function setupEventListeners() {
    // Search functionality
    $("#log-search").on("input", function() {
        searchTerm = $(this).val().toLowerCase();
        filterLogs();
    });

    // Keyboard shortcut for search (Ctrl+F)
    $(document).on("keydown", function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === "f") {
            e.preventDefault();
            $("#log-search").focus();
        }
    });

    // Filter buttons
    $(".filter-btn[data-level]").on("click", function() {
        var level = $(this).data("level");

        if (currentFilters.has(level)) {
            currentFilters.delete(level);
            $(this).removeClass("active");
        } else {
            currentFilters.add(level);
            $(this).addClass("active");
        }

        filterLogs();
    });

    // Reset filter button
    $("#filter-reset").on("click", function() {
        currentFilters.clear();
        $(".filter-btn[data-level]").removeClass("active");
        $(this).addClass("active");
        filterLogs();
    });

    // Refresh button
    $("#refresh-log").on("click", function() {
        var element = $("#log_group input[type='radio']:checked").val();
        init(element);
    });

    // Scroll buttons
    $("#scroll-to-bottom").on("click", function() {
        var renderer = document.getElementById("renderer");
        renderer.scrollTop = renderer.scrollHeight;
    });

    $("#scroll-to-top").on("click", function() {
        var renderer = document.getElementById("renderer");
        renderer.scrollTop = 0;
    });
}

// Handle reloading of the log file and display the content
function init(logType) {
    var d = document.getElementById("renderer");
    d.innerHTML = '<div id="log-loading"><div class="spinner"></div>Loading log file...</div>';

    $.ajax({
        url: getPath() + "/ajax/log/" + logType,
        datatype: "text",
        cache: false
    })
    .done(function(data) {
        processLogData(data);
        renderLogs();
        updateStats();
    })
    .fail(function() {
        $("#renderer").html('<div style="padding: 40px; text-align: center; color: #f44336;">Error loading log file</div>');
    });
}

function processLogData(data) {
    logData = [];
    var lines = data.split("\n");

    for (var i = 0; i < lines.length; i++) {
        if (!lines[i].trim()) continue;

        var logLine = {
            text: lines[i],
            level: detectLogLevel(lines[i]),
            index: i
        };

        logData.push(logLine);
    }
}

function detectLogLevel(line) {
    if (line.includes("ERROR") || line.includes("[E]")) return "ERROR";
    if (line.includes("WARNING") || line.includes("WARN") || line.includes("[W]")) return "WARNING";
    if (line.includes("INFO") || line.includes("[I]")) return "INFO";
    if (line.includes("DEBUG") || line.includes("[D]")) return "DEBUG";
    return "INFO";
}

function renderLogs() {
    var renderer = $("#renderer");
    renderer.empty();

    if (logData.length === 0) {
        renderer.html('<div style="padding: 40px; text-align: center; color: #888;">No log entries found</div>');
        return;
    }

    logData.forEach(function(logLine) {
        var div = $("<div></div>")
            .addClass("log-line")
            .addClass(logLine.level.toLowerCase())
            .attr("data-level", logLine.level)
            .attr("data-index", logLine.index)
            .html(formatLogLine(logLine.text, logLine.level));

        renderer.append(div);
    });

    filterLogs();
}

function formatLogLine(text, level) {
    var formatted = _sanitize(text);

    // Highlight timestamps (various formats)
    formatted = formatted.replace(
        /(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}|\d{2}:\d{2}:\d{2})/g,
        '<span class="timestamp">$1</span>'
    );

    // Highlight log levels
    formatted = formatted.replace(
        /(ERROR|WARNING|WARN|INFO|DEBUG|\[E\]|\[W\]|\[I\]|\[D\])/g,
        '<span class="level-' + level + '">$1</span>'
    );

    return formatted;
}

function filterLogs() {
    var visibleCount = 0;

    $(".log-line").each(function() {
        var $line = $(this);
        var lineLevel = $line.data("level");
        var lineText = $line.text().toLowerCase();
        var shouldShow = true;

        // Filter by level
        if (currentFilters.size > 0 && !currentFilters.has(lineLevel)) {
            shouldShow = false;
        }

        // Filter by search term
        if (searchTerm && !lineText.includes(searchTerm)) {
            shouldShow = false;
        }

        if (shouldShow) {
            $line.removeClass("hidden");
            visibleCount++;

            // Highlight search term
            if (searchTerm) {
                $line.addClass("highlight");
            } else {
                $line.removeClass("highlight");
            }
        } else {
            $line.addClass("hidden");
            $line.removeClass("highlight");
        }
    });

    updateStats();
}

function updateStats() {
    var totalLines = logData.length;
    var visibleLines = $(".log-line:not(.hidden)").length;
    var errorCount = 0;
    var warningCount = 0;

    logData.forEach(function(logLine) {
        if (logLine.level === "ERROR") errorCount++;
        if (logLine.level === "WARNING") warningCount++;
    });

    $("#total-lines").text(totalLines);
    $("#visible-lines").text(visibleLines);
    $("#error-count").text(errorCount);
    $("#warning-count").text(warningCount);

    // Update "All" button state
    if (currentFilters.size === 0) {
        $("#filter-reset").addClass("active");
    } else {
        $("#filter-reset").removeClass("active");
    }
}

function _sanitize(t) {
    t = t
        .replace(/&/g, "&amp;")
        .replace(/ /g, "&nbsp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    return t;
}
