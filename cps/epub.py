# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2018 lemmsh, Kennyl, Kyosfonica, matthazinski
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program. If not, see <http://www.gnu.org/licenses/>.

import os
import zipfile
from lxml import etree

from . import isoLanguages
from .helper import split_authors
from .constants import BookMeta



def extractCover(zipFile, coverFile, coverpath, tmp_file_name):
    if coverFile is None:
        return None
    else:
        zipCoverPath = os.path.join(coverpath, coverFile).replace('\\', '/')
        cf = zipFile.read(zipCoverPath)
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

    epubZip = zipfile.ZipFile(tmp_file_path)

    txt = epubZip.read('META-INF/container.xml')
    tree = etree.fromstring(txt)
    cfname = tree.xpath('n:rootfiles/n:rootfile/@full-path', namespaces=ns)[0]
    cf = epubZip.read(cfname)
    tree = etree.fromstring(cf)

    coverpath = os.path.dirname(cfname)

    p = tree.xpath('/pkg:package/pkg:metadata', namespaces=ns)[0]

    epub_metadata = {}

    for s in ['title', 'description', 'creator', 'language', 'subject']:
        tmp = p.xpath('dc:%s/text()' % s, namespaces=ns)
        if len(tmp) > 0:
            if s == 'creator':
                epub_metadata[s] = ' & '.join(split_authors(tmp))
            elif s == 'subject':
                epub_metadata[s] = ', '.join(tmp)
            else:
                epub_metadata[s] = tmp[0]
        else:
            epub_metadata[s] = u'Unknown'

    if epub_metadata['subject'] == u'Unknown':
        epub_metadata['subject'] = ''

    if epub_metadata['description'] == u'Unknown':
        description = tree.xpath("//*[local-name() = 'description']/text()")
        if len(description) > 0:
            epub_metadata['description'] = description
        else:
            epub_metadata['description'] = ""

    lang = epub_metadata['language'].split('-', 1)[0].lower()
    epub_metadata['language'] = isoLanguages.get_lang3(lang)

    epub_metadata = parse_epbub_series(ns, tree, epub_metadata)

    coverfile = parse_ebpub_cover(ns, tree, epubZip, coverpath, tmp_file_path)

    if not epub_metadata['title']:
        title = original_file_name
    else:
        title = epub_metadata['title']

    return BookMeta(
        file_path=tmp_file_path,
        extension=original_file_extension,
        title=title.encode('utf-8').decode('utf-8'),
        author=epub_metadata['creator'].encode('utf-8').decode('utf-8'),
        cover=coverfile,
        description=epub_metadata['description'],
        tags=epub_metadata['subject'].encode('utf-8').decode('utf-8'),
        series=epub_metadata['series'].encode('utf-8').decode('utf-8'),
        series_id=epub_metadata['series_id'].encode('utf-8').decode('utf-8'),
        languages=epub_metadata['language'],
        publisher="")

def parse_ebpub_cover(ns, tree, epubZip, coverpath, tmp_file_path):
    coversection = tree.xpath("/pkg:package/pkg:manifest/pkg:item[@id='cover-image']/@href", namespaces=ns)
    coverfile = None
    if len(coversection) > 0:
        coverfile = extractCover(epubZip, coversection[0], coverpath, tmp_file_path)
    else:
        meta_cover = tree.xpath("/pkg:package/pkg:metadata/pkg:meta[@name='cover']/@content", namespaces=ns)
        if len(meta_cover) > 0:
            coversection = tree.xpath("/pkg:package/pkg:manifest/pkg:item[@id='"+meta_cover[0]+"']/@href", namespaces=ns)
        else:
            coversection = tree.xpath("/pkg:package/pkg:guide/pkg:reference/@href", namespaces=ns)
        if len(coversection) > 0:
            filetype = coversection[0].rsplit('.', 1)[-1]
            if filetype == "xhtml" or filetype == "html":  # if cover is (x)html format
                markup = epubZip.read(os.path.join(coverpath, coversection[0]))
                markupTree = etree.fromstring(markup)
                # no matter xhtml or html with no namespace
                imgsrc = markupTree.xpath("//*[local-name() = 'img']/@src")
                # Alternative image source
                if not len(imgsrc):
                    imgsrc = markupTree.xpath("//attribute::*[contains(local-name(), 'href')]")
                if len(imgsrc):
                    # imgsrc maybe startwith "../"" so fullpath join then relpath to cwd
                    filename = os.path.relpath(os.path.join(os.path.dirname(os.path.join(coverpath, coversection[0])),
                                                            imgsrc[0]))
                    coverfile = extractCover(epubZip, filename, "", tmp_file_path)
            else:
                coverfile = extractCover(epubZip, coversection[0], coverpath, tmp_file_path)
    return coverfile

def parse_epbub_series(ns, tree, epub_metadata):
    series = tree.xpath("/pkg:package/pkg:metadata/pkg:meta[@name='calibre:series']/@content", namespaces=ns)
    if len(series) > 0:
        epub_metadata['series'] = series[0]
    else:
        epub_metadata['series'] = ''

    series_id = tree.xpath("/pkg:package/pkg:metadata/pkg:meta[@name='calibre:series_index']/@content", namespaces=ns)
    if len(series_id) > 0:
        epub_metadata['series_id'] = series_id[0]
    else:
        epub_metadata['series_id'] = '1'
    return epub_metadata
