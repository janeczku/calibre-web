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

from . import isoLanguages, cover
from .helper import split_authors
from .constants import BookMeta


def _extract_cover(zip_file, cover_path, tmp_file_name):
    if cover_path is None:
        return None
    else:
        cf = extension = None

        prefix = os.path.splitext(tmp_file_name)[0]
        tmp_cover_name = prefix + '.' + os.path.basename(cover_path)
        ext = os.path.splitext(tmp_cover_name)
        if len(ext) > 1:
            extension = ext[1].lower()
        if extension in cover.COVER_EXTENSIONS:
            cf = zip_file.read(cover_path)
        return cover.cover_processing(tmp_file_name, cf, extension)


def get_epub_cover(zipfile):
    namespaces = {
   "calibre":"http://calibre.kovidgoyal.net/2009/metadata",
   "dc":"http://purl.org/dc/elements/1.1/",
   "dcterms":"http://purl.org/dc/terms/",
   "opf":"http://www.idpf.org/2007/opf",
   "u":"urn:oasis:names:tc:opendocument:xmlns:container",
   "xsi":"http://www.w3.org/2001/XMLSchema-instance",
   "xhtml":"http://www.w3.org/1999/xhtml"
}
    t = etree.fromstring(zipfile.read("META-INF/container.xml"))
        # We use xpath() to find the attribute "full-path":
    '''
    <container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
        <rootfiles>
        <rootfile full-path="OEBPS/content.opf" ... />
        </rootfiles>
    </container>
    '''
    rootfile_path =  t.xpath("/u:container/u:rootfiles/u:rootfile",
                                            namespaces=namespaces)[0].get("full-path")
    
    # We load the "root" file, indicated by the "full_path" attribute of "META-INF/container.xml", using lxml.etree.fromString():
    t = etree.fromstring(zipfile.read(rootfile_path))

    cover_href = None
    try:
        # For EPUB 2.0, we use xpath() to find a <meta> 
        # named "cover" and get the attribute "content":
        '''
        <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
            ...
            <meta content="my-cover-image" name="cover"/>
            ...
        </metadata>            '''

        cover_id = t.xpath("//opf:metadata/opf:meta[@name='cover']",
                                    namespaces=namespaces)[0].get("content")
        # Next, we use xpath() to find the <item> (in <manifest>) with this id 
        # and get the attribute "href":
        '''
        <manifest>
            ...
            <item id="my-cover-image" href="images/978.jpg" ... />
            ... 
        </manifest>
        '''
        cover_href = t.xpath("//opf:manifest/opf:item[@id='" + cover_id + "']",
                                namespaces=namespaces)[0].get("href")
    except IndexError:
        pass
    
    if not cover_href:
        # For EPUB 3.0, We use xpath to find the <item> (in <manifest>) that
        # has properties='cover-image' and get the attribute "href":
        '''
        <manifest>
            ...
            <item href="images/cover.png" id="cover-img" media-type="image/png" properties="cover-image"/>
            ...
        </manifest>
        '''
        try:
            cover_href = t.xpath("//opf:manifest/opf:item[@properties='cover-image']",
                                    namespaces=namespaces)[0].get("href")
        except IndexError:
            pass

    if not cover_href:
        # Some EPUB files do not declare explicitly a cover image.
        # Instead, they use an "<img src=''>" inside the first xhmtl file.
        try:
            # The <spine> is a list that defines the linear reading order
            # of the content documents of the book. The first item in the  
            # list is the first item in the book.  
            '''
            <spine toc="ncx">
                <itemref idref="cover"/>
                <itemref idref="nav"/>
                <itemref idref="s04"/>
            </spine>
            '''
            cover_page_id = t.xpath("//opf:spine/opf:itemref",
                                    namespaces=namespaces)[0].get("idref")
            # Next, we use xpath() to find the item (in manifest) with this id 
            # and get the attribute "href":
            cover_page_href = t.xpath("//opf:manifest/opf:item[@id='" + cover_page_id + "']",
                                        namespaces=namespaces)[0].get("href")
            # In order to get the full path for the cover page,
            # we have to join rootfile_path and cover_page_href:
            cover_page_path = os.path.join(os.path.dirname(rootfile_path), cover_page_href)
            # We try to find the <img> and get the "src" attribute:
            t = etree.fromstring(zipfile.read(cover_page_path))              
            cover_href = t.xpath("//xhtml:img", namespaces=namespaces)[0].get("src")
        except IndexError:
            pass

    if not cover_href:
        return None

    # In order to get the full path for the cover image,
    # we have to join rootfile_path and cover_href:
    cover_href = cover_href.replace("../", "")
    cover_path = os.path.join(os.path.dirname(rootfile_path), cover_href)
    return cover_path

def get_epub_info(tmp_file_path, original_file_name, original_file_extension):
    ns = {
        'n': 'urn:oasis:names:tc:opendocument:xmlns:container',
        'pkg': 'http://www.idpf.org/2007/opf',
        'dc': 'http://purl.org/dc/elements/1.1/'
    }

    epub_zip = zipfile.ZipFile(tmp_file_path)

    txt = epub_zip.read('META-INF/container.xml')
    tree = etree.fromstring(txt)
    cf_name = tree.xpath('n:rootfiles/n:rootfile/@full-path', namespaces=ns)[0]
    cf = epub_zip.read(cf_name)
    tree = etree.fromstring(cf)


    p = tree.xpath('/pkg:package/pkg:metadata', namespaces=ns)[0]

    epub_metadata = {}

    for s in ['title', 'description', 'creator', 'language', 'subject', 'publisher', 'date']:
        tmp = p.xpath('dc:%s/text()' % s, namespaces=ns)
        if len(tmp) > 0:
            if s == 'creator':
                epub_metadata[s] = ' & '.join(split_authors(tmp))
            elif s == 'subject':
                epub_metadata[s] = ', '.join(tmp)
            elif s == 'date':
                epub_metadata[s] = tmp[0][:10]
            else:
                epub_metadata[s] = tmp[0]
        else:
            epub_metadata[s] = 'Unknown'

    if epub_metadata['subject'] == 'Unknown':
        epub_metadata['subject'] = ''

    if epub_metadata['publisher'] == u'Unknown':
        epub_metadata['publisher'] = ''

    if epub_metadata['date'] == u'Unknown':
        epub_metadata['date'] = ''

    if epub_metadata['description'] == u'Unknown':
        description = tree.xpath("//*[local-name() = 'description']/text()")
        if len(description) > 0:
            epub_metadata['description'] = description
        else:
            epub_metadata['description'] = ""

    lang = epub_metadata['language'].split('-', 1)[0].lower()
    epub_metadata['language'] = isoLanguages.get_lang3(lang)

    epub_metadata = parse_epub_series(ns, tree, epub_metadata)

    cover_file = parse_epub_cover(epub_zip, tmp_file_path)

    identifiers = []
    for node in p.xpath('dc:identifier', namespaces=ns):
        identifier_name = node.attrib.values()[-1]
        identifier_value = node.text
        if identifier_name in ('uuid', 'calibre') or identifier_value is None:
            continue
        identifiers.append([identifier_name, identifier_value])

    if not epub_metadata['title']:
        title = original_file_name
    else:
        title = epub_metadata['title']

    return BookMeta(
        file_path=tmp_file_path,
        extension=original_file_extension,
        title=title.encode('utf-8').decode('utf-8'),
        author=epub_metadata['creator'].encode('utf-8').decode('utf-8'),
        cover=cover_file,
        description=epub_metadata['description'],
        tags=epub_metadata['subject'].encode('utf-8').decode('utf-8'),
        series=epub_metadata['series'].encode('utf-8').decode('utf-8'),
        series_id=epub_metadata['series_id'].encode('utf-8').decode('utf-8'),
        languages=epub_metadata['language'],
        publisher=epub_metadata['publisher'].encode('utf-8').decode('utf-8'),
        pubdate=epub_metadata['date'],
        identifiers=identifiers)


def parse_epub_cover(epub_zip, tmp_file_path):
    cover_file = get_epub_cover(zipfile=epub_zip)
    # if len(cover_section) > 0:
    if cover_file:
        cover_file = _extract_cover(epub_zip, cover_file, tmp_file_path)
    
    return cover_file


def parse_epub_series(ns, tree, epub_metadata):
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
