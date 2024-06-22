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
from . import config, logger
from .helper import split_authors
from .epub_helper import get_content_opf, default_ns
from .constants import BookMeta

log = logger.create()


def _extract_cover(zip_file, cover_file, cover_path, tmp_file_name):
    if cover_file is None:
        return None

    cf = extension = None
    zip_cover_path = os.path.join(cover_path, cover_file).replace('\\', '/')

    prefix = os.path.splitext(tmp_file_name)[0]
    tmp_cover_name = prefix + '.' + os.path.basename(zip_cover_path)
    ext = os.path.splitext(tmp_cover_name)
    if len(ext) > 1:
        extension = ext[1].lower()
    if extension in cover.COVER_EXTENSIONS:
        cf = zip_file.read(zip_cover_path)
    return cover.cover_processing(tmp_file_name, cf, extension)


def get_epub_layout(book, book_data):
    file_path = os.path.normpath(os.path.join(config.get_book_path(),
                                              book.path, book_data.name + "." + book_data.format.lower()))

    try:
        tree, __ = get_content_opf(file_path, default_ns)
        p = tree.xpath('/pkg:package/pkg:metadata', namespaces=default_ns)[0]

        layout = p.xpath('pkg:meta[@property="rendition:layout"]/text()', namespaces=default_ns)
    except (etree.XMLSyntaxError, KeyError, IndexError, OSError) as e:
        log.error("Could not parse epub metadata of book {} during kobo sync: {}".format(book.id, e))
        layout = []

    if len(layout) == 0:
        return None
    else:
        return layout[0]


def get_epub_info(tmp_file_path, original_file_name, original_file_extension):
    ns = {
        'n': 'urn:oasis:names:tc:opendocument:xmlns:container',
        'pkg': 'http://www.idpf.org/2007/opf',
        'dc': 'http://purl.org/dc/elements/1.1/'
    }

    tree, cf_name = get_content_opf(tmp_file_path, ns)

    cover_path = os.path.dirname(cf_name)

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
                epub_metadata[s] = tmp[0].strip()
        else:
            epub_metadata[s] = 'Unknown'

    if epub_metadata['subject'] == 'Unknown':
        epub_metadata['subject'] = ''

    if epub_metadata['publisher'] == 'Unknown':
        epub_metadata['publisher'] = ''

    if epub_metadata['date'] == 'Unknown':
        epub_metadata['date'] = ''

    if epub_metadata['description'] == 'Unknown':
        description = tree.xpath("//*[local-name() = 'description']/text()")
        if len(description) > 0:
            epub_metadata['description'] = description
        else:
            epub_metadata['description'] = ""

    lang = epub_metadata['language'].split('-', 1)[0].lower()
    epub_metadata['language'] = isoLanguages.get_lang3(lang)

    epub_metadata = parse_epub_series(ns, tree, epub_metadata)

    epub_zip = zipfile.ZipFile(tmp_file_path)
    cover_file = parse_epub_cover(ns, tree, epub_zip, cover_path, tmp_file_path)

    identifiers = []
    for node in p.xpath('dc:identifier', namespaces=ns):
        try:
            identifier_name = node.attrib.values()[-1]
        except IndexError:
            continue
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


def parse_epub_cover(ns, tree, epub_zip, cover_path, tmp_file_path):
    cover_section = tree.xpath("/pkg:package/pkg:manifest/pkg:item[@id='cover-image']/@href", namespaces=ns)
    for cs in cover_section:
        cover_file = _extract_cover(epub_zip, cs, cover_path, tmp_file_path)
        if cover_file:
            return cover_file

    meta_cover = tree.xpath("/pkg:package/pkg:metadata/pkg:meta[@name='cover']/@content", namespaces=ns)
    if len(meta_cover) > 0:
        cover_section = tree.xpath(
            "/pkg:package/pkg:manifest/pkg:item[@id='"+meta_cover[0]+"']/@href", namespaces=ns)
        if not cover_section:
            cover_section = tree.xpath(
                "/pkg:package/pkg:manifest/pkg:item[@properties='" + meta_cover[0] + "']/@href", namespaces=ns)
    else:
        cover_section = tree.xpath("/pkg:package/pkg:guide/pkg:reference/@href", namespaces=ns)

    cover_file = None
    for cs in cover_section:
        if cs.endswith('.xhtml') or cs.endswith('.html'):
            markup = epub_zip.read(os.path.join(cover_path, cs))
            markup_tree = etree.fromstring(markup)
            # no matter xhtml or html with no namespace
            img_src = markup_tree.xpath("//*[local-name() = 'img']/@src")
            # Alternative image source
            if not len(img_src):
                img_src = markup_tree.xpath("//attribute::*[contains(local-name(), 'href')]")
            if len(img_src):
                # img_src maybe start with "../"" so fullpath join then relpath to cwd
                filename = os.path.relpath(os.path.join(os.path.dirname(os.path.join(cover_path, cover_section[0])),
                                                        img_src[0]))
                cover_file = _extract_cover(epub_zip, filename, "", tmp_file_path)
        else:
            cover_file = _extract_cover(epub_zip, cs, cover_path, tmp_file_path)
        if cover_file:
            break
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
