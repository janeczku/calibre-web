/**
 * Created by SpeedProg on 05.04.2015.
 */
/* global Bloodhound, language, Modernizr, tinymce, getPath */

if ($("#comments").length && typeof tinymce !== "undefined") {
    tinymce.init({
        selector: "#comments",
        plugins: 'code',
        branding: false,
        menubar: "edit view format",
        language: language
    });
}

if ($(".tiny_editor").length) {
    tinymce.init({
        selector: ".tiny_editor",
        plugins: 'code',
        branding: false,
        menubar: "edit view format",
        language: language
    });
}

$(function () {
    if (typeof TomSelect === "undefined") {
        return;
    }

    $(".advanced-search-select").each(function () {
        const select = this;

        if (select.tomselect) {
            select.tomselect.destroy();
        }

        new TomSelect(select, {
            maxItems: null,
            persist: false,
            create: false,
            plugins: ["remove_button"],
            closeAfterSelect: false,
            hideSelected: false
        });
    });
});

$(".datepicker").datepicker({
    format: "yyyy-mm-dd",
    language: language
}).on("change", function () {
    // Show localized date over top of the standard YYYY-MM-DD date
    var pubDate;
    var results = /(\d{4})[-\/\\](\d{1,2})[-\/\\](\d{1,2})/.exec(this.value); // YYYY-MM-DD
    if (results) {
        pubDate = new Date(results[1], parseInt(results[2], 10) - 1, results[3]) || new Date(this.value);
        $(this).next('input')
            .val(pubDate.toLocaleDateString(language.replaceAll("_","-")))
            .removeClass("hidden");
    }
}).trigger("change");

$(".datepicker_delete").click(function() {
    var inputs = $(this).parent().siblings('input');
    $(inputs[0]).data('datepicker').clearDates();
    $(inputs[1]).addClass('hidden');
});


/*
Takes a prefix, query typeahead callback, Bloodhound typeahead adapter
 and returns the completions it gets from the bloodhound engine prefixed.
 */
function prefixedSource(prefix, query, cb, source) {
    function async(retArray) {
        retArray = retArray || [];
        var matches = [];
        for (var i = 0; i < retArray.length; i++) {
            var obj = {name : prefix + retArray[i].name};
            matches.push(obj);
        }
        cb(matches);
    }
    source.search(query, cb, async);
}

function sourceSplit(query, cb, split, source) {
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
    prefixedSource(prefix, currentSource, cb, source);
}

var authors = new Bloodhound({
    name: "authors",
    identify: function(obj) { return obj.name; },
    datumTokenizer: function datumTokenizer(datum) {
        return [datum.name];
    },
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    remote: {
        url: getPath() + "/get_authors_json?q=%QUERY",
        wildcard: '%QUERY',
    },
});

$(".form-group #authors").typeahead(
    {
        highlight: true,
        minLength: 1,
        hint: true
    }, {
        name: "authors",
        display: 'name',
        source: function source(query, cb, asyncResults) {
            return sourceSplit(query, cb, "&", authors);
        }
    }
);


var series = new Bloodhound({
    name: "series",
    datumTokenizer: function datumTokenizer(datum) {
        return [datum.name];
    },
    // queryTokenizer: Bloodhound.tokenizers.whitespace,
    queryTokenizer: function queryTokenizer(query) {
        return [query];
    },
    remote: {
        url: getPath() + "/get_series_json?q=%QUERY",
        wildcard: '%QUERY',
        /*replace: function replace(url, query) {
            return url + encodeURIComponent(query);
        }*/
    }
});
$(".form-group #series").typeahead(
    {
        highlight: true,
        minLength: 0,
        hint: true
    }, {
        name: "series",
        displayKey: "name",
        source: series
    }
);

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
        url: getPath() + "/get_tags_json?q=%QUERY",
        wildcard: '%QUERY'
    }
});

$(".form-group #tags").typeahead(
    {
        highlight: true,
        minLength: 0,
        hint: true
    }, {
        name: "tags",
        display: "name",
        source: function source(query, cb, asyncResults) {
            return sourceSplit(query, cb, ",", tags);
        }
    }
);

var languages = new Bloodhound({
    name: "languages",
    datumTokenizer: function datumTokenizer(datum) {
        return [datum.name];
    },
    queryTokenizer: function queryTokenizer(query) {
        return [query];
    },
    remote: {
        url: getPath() + "/get_languages_json?q=%QUERY",
        wildcard: '%QUERY'
        /*replace: function replace(url, query) {
            return url + encodeURIComponent(query);
        }*/
    }
});

$(".form-group #languages").typeahead(
    {
        highlight: true, minLength: 0,
        hint: true
    }, {
        name: "languages",
        display: "name",
        source: function source(query, cb, asyncResults) {
            return sourceSplit(query, cb, ",", languages);
        }
    }
);

var publishers = new Bloodhound({
    name: "publisher",
    datumTokenizer: function datumTokenizer(datum) {
        return [datum.name];
    },
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    remote: {
        url: getPath() + "/get_publishers_json?q=%QUERY",
        wildcard: '%QUERY'
    }
});

$(".form-group #publisher").typeahead(
    {
        highlight: true, minLength: 0,
        hint: true
    }, {
        name: "publishers",
        displayKey: "name",
        source: publishers
    }
);

$("#search").on("change input.typeahead:selected", function (event) {
    if (event.target.type === "search" && event.target.tagName === "INPUT") {
        return;
    }

    var form = $("#search").serialize();
    $.getJSON(getPath() + "/get_matching_tags", form, function (data) {
        $(".tags_click").each(function () {
            var option = $(this);
            var tagId = parseInt(option.val(), 10);
            var isMatching = $.inArray(tagId, data.tags) !== -1;

            if (isMatching) {
                option.prop("disabled", false);
                return;
            }

            if (!option.prop("selected")) {
                option.prop("disabled", true);
            }
        });

        $("#include_tag, #exclude_tag").each(function () {
            var select = this;
            if (typeof TomSelect !== "undefined" && select.tomselect) {
                select.tomselect.refreshOptions(false);
                return;
            }
            if (typeof $.fn.selectpicker === "function") {
                $(select).selectpicker("refresh");
            }
        });
    });
});


$("#btn-upload-cover").on("change", function () {
    var filename = $(this).val();
    if (filename.substring(3, 11) === "fakepath") {
        filename = filename.substring(12);
    } // Remove c:\fake at beginning from localhost chrome
    $("#upload-cover").text(filename);
});

$("#xchange").click(function () {
    this.blur();
    var title = $("#title").val();
    $("#title").val($("#authors").val());
    $("#authors").val(title);
});

