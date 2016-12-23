import zipfile
from lxml import etree
import os
import uploader


def extractCover(zip, coverFile, tmp_file_name):
    if coverFile is None:
        return None
    else:
        cf = zip.read("OPS/" + coverFile)
        prefix = os.path.splitext(tmp_file_name)[0]
        tmp_cover_name = prefix + "." + coverFile
        image = open(tmp_cover_name, 'wb')
        image.write(cf)
        image.close()
        return tmp_cover_name


def get_epub_info(tmp_file_path, original_file_name, original_file_extension):
    ns = {
        'n': 'urn:oasis:names:tc:opendocument:xmlns:container',
        'pkg': 'http://www.idpf.org/2007/opf',
        'dc': 'http://purl.org/dc/elements/1.1/'
    }

    zip = zipfile.ZipFile(tmp_file_path)

    txt = zip.read('META-INF/container.xml')
    tree = etree.fromstring(txt)
    cfname = tree.xpath('n:rootfiles/n:rootfile/@full-path', namespaces=ns)[0]

    cf = zip.read(cfname)
    tree = etree.fromstring(cf)

    p = tree.xpath('/pkg:package/pkg:metadata', namespaces=ns)[0]

    epub_metadata = {}
    for s in ['title', 'description', 'creator']:
        tmp = p.xpath('dc:%s/text()' % s, namespaces=ns)
        if len(tmp) > 0:
            epub_metadata[s] = p.xpath('dc:%s/text()' % s, namespaces=ns)[0]
        else:
            epub_metadata[s] = "Unknown"

    coversection = tree.xpath("/pkg:package/pkg:manifest/pkg:item[@id='cover']/@href", namespaces=ns)
    if len(coversection) > 0:
        coverfile = extractCover(zip, coversection[0], tmp_file_path)
    else:
        coverfile = None
    if epub_metadata['title'] is None:
        title = original_file_name
    else:
        title = epub_metadata['title']

    return uploader.BookMeta(
        file_path=tmp_file_path,
        extension=original_file_extension,
        title=title,
        author=epub_metadata['creator'],
        cover=coverfile,
        description=epub_metadata['description'],
        tags="",
        series="",
        series_id="")
