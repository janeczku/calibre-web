#!/usr/bin/env python
# -*- coding: utf-8 -*-

import zipfile
from lxml import etree
import os
import uploader
from iso639 import languages as isoLanguages

def extractCover(zip, coverFile, coverpath, tmp_file_name):
    if coverFile is None:
        return None
    else:
        zipCoverPath = os.path.join(coverpath , coverFile).replace('\\','/')
        cf = zip.read(zipCoverPath)
        prefix = os.path.splitext(tmp_file_name)[0]
        tmp_cover_name = prefix + '.' + os.path.basename(zipCoverPath)
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

    coverpath=os.path.dirname(cfname)

    p = tree.xpath('/pkg:package/pkg:metadata', namespaces=ns)[0]

    epub_metadata = {}

    for s in ['title', 'description', 'creator', 'language']:
        tmp = p.xpath('dc:%s/text()' % s, namespaces=ns)
        if len(tmp) > 0:
            epub_metadata[s] = p.xpath('dc:%s/text()' % s, namespaces=ns)[0]
        else:
            epub_metadata[s] = "Unknown"

    if epub_metadata['description'] == "Unknown":
        description = tree.xpath("//*[local-name() = 'description']/text()")
        if len(description) > 0:
            epub_metadata['description'] = description
        else:
            epub_metadata['description'] = ""

    if epub_metadata['language'] == "Unknown":
        epub_metadata['language'] == ""
    else:
        lang = epub_metadata['language'].split('-', 1)[0].lower()
        if len(lang) == 2:
            epub_metadata['language'] = isoLanguages.get(part1=lang).name
        elif len(lang) == 3:
            epub_metadata['language'] = isoLanguages.get(part3=lang).name
        else:
            epub_metadata['language'] = ""

    coversection = tree.xpath("/pkg:package/pkg:manifest/pkg:item[@id='cover-image']/@href", namespaces=ns)
    coverfile = None
    if len(coversection) > 0:
        coverfile = extractCover(zip, coversection[0], coverpath, tmp_file_path)
    else:
        meta_cover = tree.xpath("/pkg:package/pkg:metadata/pkg:meta[@name='cover']/@content", namespaces=ns)
        if len(meta_cover) > 0:
            coversection = tree.xpath("/pkg:package/pkg:manifest/pkg:item[@id='"+meta_cover[0]+"']/@href", namespaces=ns)
            if len(coversection) > 0:
                filetype = coversection[0].rsplit('.',1)[-1]
                if filetype == "xhtml" or filetype == "html": #if cover is (x)html format
                    markup = zip.read(os.path.join(coverpath,coversection[0]))
                    markupTree = etree.fromstring(markup)
                    #no matter xhtml or html with no namespace
                    imgsrc = markupTree.xpath("//*[local-name() = 'img']/@src")
                    #imgsrc maybe startwith "../"" so fullpath join then relpath to cwd
                    filename = os.path.relpath(os.path.join(os.path.dirname(os.path.join(coverpath, coversection[0])), imgsrc[0]))
                    coverfile = extractCover(zip, filename, "", tmp_file_path)
                else:
                    coverfile = extractCover(zip, coversection[0], coverpath, tmp_file_path)
            
    if epub_metadata['title'] is None:
        title = original_file_name
    else:
        title = epub_metadata['title']

    return uploader.BookMeta(
        file_path=tmp_file_path,
        extension=original_file_extension,
        title=title.encode('utf-8').decode('utf-8'),
        author=epub_metadata['creator'].encode('utf-8').decode('utf-8'),
        cover=coverfile,
        description=epub_metadata['description'],
        tags="",
        series="",
        series_id="",
        languages=epub_metadata['language'])
