
from lxml import etree
import os
import uploader


def get_fb2_info(tmp_file_path, original_file_name, original_file_extension):

    ns = {
        'fb': 'http://www.gribuser.ru/xml/fictionbook/2.0',
        'l': 'http://www.w3.org/1999/xlink',
    }

    fb2_file = open(tmp_file_path)
    tree = etree.fromstring(fb2_file.read())

    authors = tree.xpath('/fb:FictionBook/fb:description/fb:title-info/fb:author', namespaces=ns)

    def get_author(element):
        return element.xpath('fb:first-name/text()', namespaces=ns)[0] + ' ' + element.xpath('fb:middle-name/text()',
                            namespaces=ns)[0] + ' ' + element.xpath('fb:last-name/text()', namespaces=ns)[0]
    author = ", ".join(map(get_author, authors))

    title = unicode(tree.xpath('/fb:FictionBook/fb:description/fb:title-info/fb:book-title/text()', namespaces=ns)[0])
    description = unicode(tree.xpath('/fb:FictionBook/fb:description/fb:publish-info/fb:book-name/text()',
                                     namespaces=ns)[0])

    return uploader.BookMeta(
        file_path=tmp_file_path,
        extension=original_file_extension,
        title=title,
        author=author,
        cover=None,
        description=description,
        tags="",
        series="",
        series_id="")
