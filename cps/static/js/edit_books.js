/**
 * Created by SpeedProg on 05.04.2015.
 */
/* global Bloodhound */


/*
Takes a prefix, query typeahead callback, Bloodhound typeahead adapter
 and returns the completions it gets from the bloodhound engine prefixed.
 */
function prefixed_source(prefix, query, cb, bhAdapter) {
    bhAdapter(query, function(retArray){
        var matches = [];
        for (var i = 0; i < retArray.length; i++) {
            var obj = {name : prefix + retArray[i].name};
            matches.push(obj);
        }
        cb(matches);
    });
}
function get_path(){
    var jsFileLocation = $("script[src*=edit_books]").attr("src");  // the js file path
    jsFileLocation = jsFileLocation.replace("/static/js/edit_books.js", '');   // the js folder path
    return jsFileLocation;
}

var authors = new Bloodhound({
    name: "authors",
    datumTokenizer: function(datum) {
        return [datum.name];
    },
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    remote: {
        url: get_path()+"/get_authors_json?q=%QUERY"
    }
});

var series = new Bloodhound({
    name: "series",
    datumTokenizer: function(datum) {
        return [datum.name];
    },
    queryTokenizer: function(query) {
        return [query];
    },
    remote: {
        url: get_path()+"/get_series_json?q=",
        replace: function(url, query) {
            return url+encodeURIComponent(query);
        }
    }
});


var tags = new Bloodhound({
    name: "tags",
    datumTokenizer: function(datum) {
        return [datum.name];
    },
    queryTokenizer: function(query) {
        var tokens = query.split(",");
        tokens = [tokens[tokens.length-1].trim()];
        return tokens;
    },
    remote: {
        url: get_path()+"/get_tags_json?q=%QUERY"
    }
});

var languages = new Bloodhound({
    name: "languages",
    datumTokenizer: function(datum) {
        return [datum.name];
    },
    queryTokenizer: function(query) {
        return [query];
    },
    remote: {
        url: get_path()+"/get_languages_json?q=",
        replace: function(url, query) {
            url_query = url+encodeURIComponent(query);
            return url_query;
        }
    }
});

function sourceSplit(query, cb, split, source) {
    var bhAdapter = source.ttAdapter();

    var tokens = query.split(split);
    var currentSource = tokens[tokens.length-1].trim();

    tokens.splice(tokens.length-1, 1); // remove last element
    var prefix = "";
    var newSplit;
    if (split === "&"){
        newSplit = " " + split + " ";
    }else{
        newSplit = split + " ";
    }
    for (var i = 0; i < tokens.length; i++) {
        prefix += tokens[i].trim() + newSplit;
    }
    prefixed_source(prefix, currentSource, cb, bhAdapter);
}

var promiseAuthors = authors.initialize();
    promiseAuthors.done(function(){
    $("#bookAuthor").typeahead(
            {
                highlight: true, minLength: 1,
                hint: true
            }, {
                name: "authors",
                displayKey: "name",
                source: function(query, cb){
                    return sourceSplit(query, cb, "&", authors); //sourceSplit //("&")
            }
    });
});

var promiseSeries = series.initialize();
    promiseSeries.done(function(){
    $("#series").typeahead(
            {
                highlight: true, minLength: 0,
                hint: true
            }, {
                name: "series",
                displayKey: "name",
                source: series.ttAdapter()
            }
    )
});

var promiseTags = tags.initialize();
    promiseTags.done(function(){
    $("#tags").typeahead(
            {
                highlight: true, minLength: 0,
                hint: true
            }, {
                name: "tags",
                displayKey: "name",
                source: function(query, cb){
                    return sourceSplit(query, cb, ",", tags);
                }
            });
    });

var promiseLanguages = languages.initialize();
    promiseLanguages.done(function(){
    $("#languages").typeahead(
            {
                highlight: true, minLength: 0,
                hint: true
            }, {
                name: "languages",
                displayKey: "name",
                source: function(query, cb){
                    return sourceSplit(query, cb, ",", languages); //(",")
                }
            });
    });

$("form").on("change input typeahead:selected", function(data){
    var form = $("form").serialize();
    $.getJSON( get_path()+"/get_matching_tags", form, function( data ) {
      $(".tags_click").each(function() {
        if ($.inArray(parseInt($(this).children("input").first().val(), 10), data.tags) === -1 ) {
          if (!($(this).hasClass("active"))) {
            $(this).addClass("disabled");
          }
        }
        else {
          $(this).removeClass("disabled");
        }
      });
    });
});
