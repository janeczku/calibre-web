/*
 * Get Metadata from Douban api
 * Created by idalin<dalin.lin@gmail.com>
 */

$(document).ready(function () {
    var get_meta_btn = '<li>' +
        '<a href="#" id="get_meta" data-toggle="modal" data-target="#metaModal">' +
        '获取Meta</a></li>';
    $('#main-nav').prepend(get_meta_btn);
    var douban = 'https://api.douban.com';
    var search = '/v2/book/search';
    var get_info = '/v2/book/';
    var get_info_by_isbn = '/v2/book/isbn/ ';

    $.ajaxSetup({
        type: "GET",
        dataType: "jsonp",
        jsonp: 'callback',
        async: false
    });

    get_meta = function (id) {
        var url = douban + get_info + id;
        console.log('getting book meta:' + id);
        $.ajax({
            url: url,
            success: function (meta) {
                console.log(meta);
                //$('#metaModal').modal('hide');
                $('#description').val(meta.summary);
                $('#bookAuthor').val(meta.author.join(' & '));
                $('#book_title').val(meta.title);
                var tags = '';
                for (var i = 0; i < meta.tags.length; i++) {
                    tags = tags + meta.tags[i].title + ',';
                }
                $('#tags').val(tags);
                $('#rating').val(Math.round(meta.rating.average / 4));
            }
        });
    }

    get_meta_by_isbn = function (isbn) {
        var url = douban + get_info_by_isbn + isbn;
    }

    search_book = function (title) {
        var url = douban + search + '?q=' + title + '&fields=id,title,author,publisher,isbn13,image,summary';
        $.ajax({
            url: url,
            success: function (data) {
                if (data.books.length < 1) {
                    $('#meta-info').html('<p class="text-danger">搜索不到对应的书籍</p>');
                } else {
                    $('#meta-info').html('<ul id="book-list" class="media-list"></ul>');
                    for (var i = 0; i < data.books.length; i++) {
                        var book = '<li class="media">' +
                            '<img class="pull-left img-responsive" data-toggle="modal" data-target="#metaModal" src="' +
                            data.books[i].image + '" alt="Cover"  onclick="javascript:get_meta(' +
                            data.books[i].id + ')">' +
                            '<div class="media-body">' +
                            '<h4 class="media-heading"><a href="https://book.douban.com/subject/' +
                            data.books[i].id + '"  target="_blank">' + data.books[i].title + '</a></h4>' +
                            '<p>作者：' + data.books[i].author + '</p>' +
                            '<p>出版社：' + data.books[i].publisher + '</p>' +
                            '<p>简介:' + data.books[i].summary + '</p>' +
                            '</div>' +
                            '</li>';
                        $("#book-list").append(book);
                        if(i>20){break;}
                    }
                }
            },
            error: function () {
                $('#meta-info').html('<p class="text-danger">搜索出错</p>');
            }
        });
    }

    $('#get_meta').click(function () {
        var book_title = $('#book_title').val();
        if (book_title) {
            // console.log(book_title);
            search_book(book_title);
        }
    });
});