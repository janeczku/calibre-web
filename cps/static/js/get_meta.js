/*
 * Get Metadata from Douban Books api and Google Books api
 * Created by idalin<dalin.lin@gmail.com>
 * Google Books api document: https://developers.google.com/books/docs/v1/using
 * Douban Books api document: https://developers.douban.com/wiki/?title=book_v2 (Chinese Only)
 */

$(document).ready(function () {
    var msg = i18n_msg;
    var douban = 'https://api.douban.com';
    var db_search = '/v2/book/search';
    var db_get_info = '/v2/book/';
    var db_get_info_by_isbn = '/v2/book/isbn/ ';
    var db_done = false;

    var google = 'https://www.googleapis.com/';
    var gg_search = '/books/v1/volumes';
    var gg_get_info = '/books/v1/volumes/';
    var gg_done = false;

    var db_results = [];
    var gg_results = [];
    var show_flag = 0;
    String.prototype.replaceAll = function (s1, s2) {　　
        return this.replace(new RegExp(s1, "gm"), s2);　　
    }

    gg_search_book = function (title) {
        title = title.replaceAll(/\s+/, '+');
        var url = google + gg_search + '?q=' + title;
        $.ajax({
            url: url,
            type: "GET",
            dataType: "jsonp",
            jsonp: 'callback',
            success: function (data) {
                gg_results = data.items;
            },
            complete: function () {
                gg_done = true;
                show_result();
            }
        });
    }

    get_meta = function (source, id) {
        var meta;
        if (source == 'google') {;
            meta = gg_results[id];
            $('#description').val(meta.volumeInfo.description);
            $('#bookAuthor').val(meta.volumeInfo.authors.join(' & '));
            $('#book_title').val(meta.volumeInfo.title);
            if (meta.volumeInfo.categories) {
                var tags = meta.volumeInfo.categories.join(',');
                $('#tags').val(tags);
            }
            if (meta.volumeInfo.averageRating) {
                $('#rating').val(Math.round(meta.volumeInfo.averageRating));
            }
            return;
        }
        if (source == 'douban') {
            meta = db_results[id];
            $('#description').val(meta.summary);
            $('#bookAuthor').val(meta.author.join(' & '));
            $('#book_title').val(meta.title);
            var tags = '';
            for (var i = 0; i < meta.tags.length; i++) {
                tags = tags + meta.tags[i].title + ',';
            }
            $('#tags').val(tags);
            $('#rating').val(Math.round(meta.rating.average / 2));
            return;
        }
    }
    do_search = function (keyword) {
        show_flag = 0;
        $('#meta-info').text(msg.loading);
        var keyword = $('#keyword').val();
        if (keyword) {
            db_search_book(keyword);
            gg_search_book(keyword);
        }
    }

    db_search_book = function (title) {
        var url = douban + db_search + '?q=' + title + '&fields=all&count=10';
        $.ajax({
            url: url,
            type: "GET",
            dataType: "jsonp",
            jsonp: 'callback',
            success: function (data) {
                db_results = data.books;
            },
            error: function () {
                $('#meta-info').html('<p class="text-danger">'+ msg.search_error+'!</p>');
            },
            complete: function () {
                db_done = true;
                show_result();
            }
        });
    }

    show_result = function () {
        show_flag++;
        if (show_flag == 1) {
            $('#meta-info').html('<ul id="book-list" class="media-list"></ul>');
        }
        if (gg_done && db_done) {
            if (!gg_results && !db_results) {
                $('#meta-info').html('<p class="text-danger">'+ msg.no_result +'</p>');
                return;
            }
        }
        if (gg_done && gg_results.length > 0) {
            for (var i = 0; i < gg_results.length; i++) {
                var book = gg_results[i];
                var book_cover;
                if (book.volumeInfo.imageLinks) {
                    book_cover = book.volumeInfo.imageLinks.thumbnail;
                } else {
                    book_cover = '/static/generic_cover.jpg';
                }
                var book_html = '<li class="media">' +
                    '<img class="pull-left img-responsive" data-toggle="modal" data-target="#metaModal" src="' +
                    book_cover + '" alt="Cover" style="width:100px;height:150px" onclick=\'javascript:get_meta("google",' +
                    i + ')\'>' +
                    '<div class="media-body">' +
                    '<h4 class="media-heading"><a href="https://books.google.com/books?id=' +
                    book.id + '"  target="_blank">' + book.volumeInfo.title + '</a></h4>' +
                    '<p>'+ msg.author +'：' + book.volumeInfo.authors + '</p>' +
                    '<p>'+ msg.publisher + '：' + book.volumeInfo.publisher + '</p>' +
                    '<p>'+ msg.description + ':' + book.volumeInfo.description + '</p>' +
                    '<p>'+ msg.source + ':<a href="https://books.google.com" target="_blank">Google Books</a></p>' +
                    '</div>' +
                    '</li>';
                $("#book-list").append(book_html);
            }
            gg_done = false;
        }
        if (db_done && db_results.length > 0) {
            for (var i = 0; i < db_results.length; i++) {
                var book = db_results[i];
                var book_html = '<li class="media">' +
                    '<img class="pull-left img-responsive" data-toggle="modal" data-target="#metaModal" src="' +
                    book.image + '" alt="Cover" style="width:100px;height: 150px" onclick=\'javascript:get_meta("douban",' +
                    i + ')\'>' +
                    '<div class="media-body">' +
                    '<h4 class="media-heading"><a href="https://book.douban.com/subject/' +
                    book.id + '"  target="_blank">' + book.title + '</a></h4>' +
                    '<p>' + msg.author + '：' + book.author + '</p>' +
                    '<p>' + msg.publisher + '：' + book.publisher + '</p>' +
                    '<p>' + msg.description + ':' + book.summary + '</p>' +
                    '<p>' + msg.source + ':<a href="https://book.douban.com" target="_blank">Douban Books</a></p>' +
                    '</div>' +
                    '</li>';
                $("#book-list").append(book_html);
            }
            db_done = false;
        }
    }

    $('#do-search').click(function () {
        var keyword = $('#keyword').val();
        if (keyword) {
            do_search(keyword);
        }
    });

    $('#get_meta').click(function () {
        var book_title = $('#book_title').val();
        if (book_title) {
            $('#keyword').val(book_title);
            do_search(book_title);
        }
    });

});