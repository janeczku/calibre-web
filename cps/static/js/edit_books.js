/**
 * Created by SpeedProg on 05.04.2015.
 */

    /*
    Takes a prefix, query typeahead callback, Bloodhound typeahead adapter
     and returns the completions it gets from the bloodhound engine prefixed.
     */
    function prefixed_source(prefix, query, cb, bh_adapter) {
        bh_adapter(query, function(retArray){
            var matches = [];
            for (var i = 0; i < retArray.length; i++) {
                var obj = {name : prefix + retArray[i].name};
                matches.push(obj);
            }
            cb(matches);
        });
    }

   var authors = new Bloodhound({
        name: 'authors',
        datumTokenizer: function(datum) {
            return [datum.name];
        },
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        remote: {
            url: '/get_authors_json?q=%QUERY'
        }
    });

    function authors_source(query, cb) {
        var bh_adapter = authors.ttAdapter();

        var tokens = query.split("&");
        var current_author = tokens[tokens.length-1].trim();

        tokens.splice(tokens.length-1, 1); // remove last element
        var prefix = "";
        for (var i = 0; i < tokens.length; i++) {
            var author = tokens[i].trim();
            prefix += author + " & ";
        }

        prefixed_source(prefix, current_author, cb, bh_adapter);
  }



    var promise = authors.initialize();
    promise.done(function(){
        $("#bookAuthor").typeahead(
                {
                    highlight: true, minLength: 1,
                    hint: true
                }, {
                    name: 'authors', displayKey: 'name',
                    source: authors_source
                }
        )
    });

    var series = new Bloodhound({
        name: 'series',
        datumTokenizer: function(datum) {
            return [datum.name];
        },
        queryTokenizer: function(query) {
            return [query];
        },
        remote: {
            url: '/get_series_json?q=',
            replace: function(url, query) {
                url_query = url+encodeURIComponent(query);
                return url_query;
            }
        }
    });
    var promise = series.initialize();
    promise.done(function(){
        $("#series").typeahead(
                {
                    highlight: true, minLength: 0,
                    hint: true
                }, {
                    name: 'series', displayKey: 'name',
                    source: series.ttAdapter()
                }
        )
    });

    var tags = new Bloodhound({
        name: 'tags',
        datumTokenizer: function(datum) {
            return [datum.name];
        },
        queryTokenizer: function(query) {
            tokens = query.split(",");
            tokens = [tokens[tokens.length-1].trim()];
            return tokens
        },
        remote: {
            url: '/get_tags_json?q=%QUERY'
        }
    });

    function tag_source(query, cb) {
        var bh_adapter = tags.ttAdapter();

        var tokens = query.split(",");
        var current_tag = tokens[tokens.length-1].trim();

        tokens.splice(tokens.length-1, 1); // remove last element
        var prefix = "";
        for (var i = 0; i < tokens.length; i++) {
            var tag = tokens[i].trim();
            prefix += tag + ", ";
        }

        prefixed_source(prefix, current_tag, cb, bh_adapter);
    }

    var promise = tags.initialize();
    promise.done(function(){
        $("#tags").typeahead(
                {
                    highlight: true, minLength: 0,
                    hint: true
                }, {
                    name: 'tags', displayKey: 'name',
                    source: tag_source
                }
        )
    });
