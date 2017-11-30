#!/usr/bin/env python
# -*- coding: utf-8 -*-

from lxml import etree
import uploader


def get_fb2_info(tmp_file_path, original_file_extension):

    ns = {
        'fb': 'http://www.gribuser.ru/xml/fictionbook/2.0',
        'l': 'http://www.w3.org/1999/xlink',
    }

    fb2_file = open(tmp_file_path)
    tree = etree.fromstring(fb2_file.read())

    authors = tree.xpath('/fb:FictionBook/fb:description/fb:title-info/fb:author', namespaces=ns)

    def get_author(element):
        last_name = element.xpath('fb:last-name/text()', namespaces=ns)
        if len(last_name):
            last_name = last_name[0]
        else:
            last_name = u''
        middle_name = element.xpath('fb:middle-name/text()', namespaces=ns)
        if len(middle_name):
            middle_name = middle_name[0]
        else:
            middle_name = u''
        first_name = element.xpath('fb:first-name/text()', namespaces=ns)
        if len(first_name):
            first_name = first_name[0]
        else:
            first_name = u''
        return first_name + ' ' + middle_name + ' ' + last_name

    author = str(", ".join(map(get_author, authors)))

    title = tree.xpath('/fb:FictionBook/fb:description/fb:title-info/fb:book-title/text()', namespaces=ns)
    if len(title):
        title = str(title[0])
    else:
        title = u''
    description = tree.xpath('/fb:FictionBook/fb:description/fb:publish-info/fb:book-name/text()', namespaces=ns)
    if len(description):
        description = str(description[0])
    else:
        description = u''

    return uploader.BookMeta(
        file_path=tmp_file_path,
        extension=original_file_extension,
        title=title.encode('utf-8').decode('utf-8'),
        author=author.encode('utf-8').decode('utf-8'),
        cover=None,
        description=description,
        tags="",
        series="",
        series_id="",
        languages="")
