
from lxml import etree
import os
import uploader


def get_fb2_info(tmp_file_path, original_file_name, original_file_extension):

    ns = {
        'fb':'http://www.gribuser.ru/xml/fictionbook/2.0',
        'l':'ttp://www.w3.org/1999/xlink',
    }

    fb2_file = open(tmp_file_path)
    tree = etree.fromstring(fb2_file.read())

    authors = tree.xpath('/fb:FictionBook/fb:description/fb:title-info/fb:author', namespaces=ns)
    def get_author(element):
        return element.xpath('fb:first-name/text()', namespaces=ns)[0] + ' ' + element.xpath('fb:middle-name/text()', namespaces=ns)[0] + ' ' + element.xpath('fb:last-name/text()', namespaces=ns)[0]
    author = ", ".join(map(get_author, authors))

    title = unicode(tree.xpath('/fb:FictionBook/fb:description/fb:title-info/fb:book-title/text()', namespaces=ns)[0])
    description = unicode(tree.xpath('/fb:FictionBook/fb:description/fb:publish-info/fb:book-name/text()', namespaces=ns)[0])

    #
    #
    #
    # cfname = tree.xpath('n:rootfiles/n:rootfile/@full-path',namespaces=ns)[0]
    #
    # cf = zip.read(cfname)
    # tree = etree.fromstring(cf)
    #
    # p = tree.xpath('/pkg:package/pkg:metadata',namespaces=ns)[0]
    #
    # epub_metadata = {}
    # for s in ['title', 'description', 'creator']:
    #     tmp = p.xpath('dc:%s/text()'%(s),namespaces=ns)
    #     if (len(tmp) > 0):
    #         epub_metadata[s] = p.xpath('dc:%s/text()'%(s),namespaces=ns)[0]
    #     else:
    #         epub_metadata[s] = "Unknown"
    #
    # coversection = tree.xpath("/pkg:package/pkg:manifest/pkg:item[@id='cover']/@href",namespaces=ns)
    # if (len(coversection) > 0):
    #     coverfile = extractCover(zip, coversection[0], tmp_file_path)
    # else:
    #     coverfile = None
    # if epub_metadata['title'] is None:
    #     title = original_file_name
    # else:
    #     title = epub_metadata['title']
    #
    #
    return uploader.BookMeta(
        file_path = tmp_file_path,
        extension = original_file_extension,
        title = title,
        author = author,
        cover = None,
        description = description,
        tags = "",
        series = "",
        series_id="")

