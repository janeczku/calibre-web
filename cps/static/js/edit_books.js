/**
 * Created by SpeedProg on 05.04.2015.
 */
/* global Bloodhound, language, Modernizr, tinymce */

if ($("#description").length) {
    tinymce.init({
        selector: "#description",
        branding: false,
        menubar: "edit view format",
        language: language
    });

    if (!Modernizr.inputtypes.date) {
        $("#pubdate").datepicker({
            format: "yyyy-mm-dd",
            language: language
        }).on("change", function () {
            // Show localized date over top of the standard YYYY-MM-DD date
            var pubDate;
            var results = /(\d{4})[-\/\\](\d{1,2})[-\/\\](\d{1,2})/.exec(this.value); // YYYY-MM-DD
            if (results) {
                pubDate = new Date(results[1], parseInt(results[2], 10) - 1, results[3]) || new Date(this.value);
                $("#fake_pubdate")
                    .val(pubDate.toLocaleDateString(language))
                    .removeClass("hidden");
            }
        }).trigger("change");
    }
}

if (!Modernizr.inputtypes.date) {
    $("#Publishstart").datepicker({
        format: "yyyy-mm-dd",
        language: language
    }).on("change", function () {
        // Show localized date over top of the standard YYYY-MM-DD date
        var pubDate;
        var results = /(\d{4})[-\/\\](\d{1,2})[-\/\\](\d{1,2})/.exec(this.value); // YYYY-MM-DD
        if (results) {
            pubDate = new Date(results[1], parseInt(results[2], 10) - 1, results[3]) || new Date(this.value);
            $("#fake_Publishstart")
                .val(pubDate.toLocaleDateString(language))
                .removeClass("hidden");
        }
    }).trigger("change");
}

if (!Modernizr.inputtypes.date) {
    $("#Publishend").datepicker({
        format: "yyyy-mm-dd",
        language: language
    }).on("change", function () {
        // Show localized date over top of the standard YYYY-MM-DD date
        var pubDate;
        var results = /(\d{4})[-\/\\](\d{1,2})[-\/\\](\d{1,2})/.exec(this.value); // YYYY-MM-DD
        if (results) {
            pubDate = new Date(results[1], parseInt(results[2], 10) - 1, results[3]) || new Date(this.value);
            $("#fake_Publishend")
                .val(pubDate.toLocaleDateString(language))
                .removeClass("hidden");
        }
    }).trigger("change");
}

/*
Takes a prefix, query typeahead callback, Bloodhound typeahead adapter
 and returns the completions it gets from the bloodhound engine prefixed.
 */
function prefixedSource(prefix, query, cb, bhAdapter) {
    bhAdapter(query, function(retArray) {
        var matches = [];
        for (var i = 0; i < retArray.length; i++) {
            var obj = {name : prefix + retArray[i].name};
            matches.push(obj);
        }
        cb(matches);
    });
}

function getPath() {
    var jsFileLocation = $("script[src*=edit_books]").attr("src");  // the js file path
    return jsFileLocation.substr(0, jsFileLocation.search("/static/js/edit_books.js"));   // the js folder path
}

var authors = new Bloodhound({
    name: "authors",
    datumTokenizer: function datumTokenizer(datum) {
        return [datum.name];
    },
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    remote: {
        url: getPath() + "/get_authors_json?q=%QUERY"
    }
});

var series = new Bloodhound({
    name: "series",
    datumTokenizer: function datumTokenizer(datum) {
        return [datum.name];
    },
    queryTokenizer: function queryTokenizer(query) {
        return [query];
    },
    remote: {
        url: getPath() + "/get_series_json?q=",
        replace: function replace(url, query) {
            return url + encodeURIComponent(query);
        }
    }
});


var tags = new Bloodhound({
    name: "tags",
    datumTokenizer: function datumTokenizer(datum) {
        return [datum.name];
    },
    queryTokenizer: function queryTokenizer(query) {
        var tokens = query.split(",");
        tokens = [tokens[tokens.length - 1].trim()];
        return tokens;
    },
    remote: {
        url: getPath() + "/get_tags_json?q=%QUERY"
    }
});

var languages = new Bloodhound({
    name: "languages",
    datumTokenizer: function datumTokenizer(datum) {
        return [datum.name];
    },
    queryTokenizer: function queryTokenizer(query) {
        return [query];
    },
    remote: {
        url: getPath() + "/get_languages_json?q=",
        replace: function replace(url, query) {
            return url + encodeURIComponent(query);
        }
    }
});

var publishers = new Bloodhound({
    name: "publisher",
    datumTokenizer: function datumTokenizer(datum) {
        return [datum.name];
    },
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    remote: {
        url: getPath() + "/get_publishers_json?q=%QUERY"
    }
});

function sourceSplit(query, cb, split, source) {
    var bhAdapter = source.ttAdapter();

    var tokens = query.split(split);
    var currentSource = tokens[tokens.length - 1].trim();

    tokens.splice(tokens.length - 1, 1); // remove last element
    var prefix = "";
    var newSplit;
    if (split === "&") {
        newSplit = " " + split + " ";
    } else {
        newSplit = split + " ";
    }
    for (var i = 0; i < tokens.length; i++) {
        prefix += tokens[i].trim() + newSplit;
    }
    prefixedSource(prefix, currentSource, cb, bhAdapter);
}

var promiseAuthors = authors.initialize();
promiseAuthors.done(function() {
    $("#bookAuthor").typeahead(
        {
            highlight: true, minLength: 1,
            hint: true
        }, {
            name: "authors",
            displayKey: "name",
            source: function source(query, cb) {
                return sourceSplit(query, cb, "&", authors); //sourceSplit //("&")
            }
        }
    );
});

var promiseSeries = series.initialize();
promiseSeries.done(function() {
    $("#series").typeahead(
        {
            highlight: true, minLength: 0,
            hint: true
        }, {
            name: "series",
            displayKey: "name",
            source: series.ttAdapter()
        }
    );
});

var promiseTags = tags.initialize();
promiseTags.done(function() {
    $("#tags").typeahead(
        {
            highlight: true, minLength: 0,
            hint: true
        }, {
            name: "tags",
            displayKey: "name",
            source: function source(query, cb) {
                return sourceSplit(query, cb, ",", tags);
            }
        }
    );
});

var promiseLanguages = languages.initialize();
promiseLanguages.done(function() {
    $("#languages").typeahead(
        {
            highlight: true, minLength: 0,
            hint: true
        }, {
            name: "languages",
            displayKey: "name",
            source: function source(query, cb) {
                return sourceSplit(query, cb, ",", languages); //(",")
            }
        }
    );
});

var promisePublishers = publishers.initialize();
promisePublishers.done(function() {
    $("#publisher").typeahead(
        {
            highlight: true, minLength: 0,
            hint: true
        }, {
            name: "publishers",
            displayKey: "name",
            source: publishers.ttAdapter()
        }
    );
});

$("#search").on("change input.typeahead:selected", function() {
    var form = $("form").serialize();
    $.getJSON( getPath() + "/get_matching_tags", form, function( data ) {
        $(".tags_click").each(function() {
            if ($.inArray(parseInt($(this).children("input").first().val(), 10), data.tags) === -1 ) {
                if (!($(this).hasClass("active"))) {
                    $(this).addClass("disabled");
                }
            } else {
                $(this).removeClass("disabled");
            }
        });
    });
});

$("#btn-upload-format").on("change", function () {
    var filename = $(this).val();
    if (filename.substring(3, 11) === "fakepath") {
        filename = filename.substring(12);
    } // Remove c:\fake at beginning from localhost chrome
    $("#upload-format").html(filename);
});

$("#btn-upload-cover").on("change", function () {
    var filename = $(this).val();
    if (filename.substring(3, 11) === "fakepath") {
        filename = filename.substring(12);
    } // Remove c:\fake at beginning from localhost chrome
    $("#upload-cover").html(filename);
});

