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

import zipfile
from lxml import etree

from . import isoLanguages

default_ns = {
    'n': 'urn:oasis:names:tc:opendocument:xmlns:container',
    'pkg': 'http://www.idpf.org/2007/opf',
}

OPF_NAMESPACE = "http://www.idpf.org/2007/opf"
PURL_NAMESPACE = "http://purl.org/dc/elements/1.1/"

OPF = "{%s}" % OPF_NAMESPACE
PURL = "{%s}" % PURL_NAMESPACE

etree.register_namespace("opf", OPF_NAMESPACE)
etree.register_namespace("dc", PURL_NAMESPACE)

OPF_NS = {None: OPF_NAMESPACE}  # the default namespace (no prefix)
NSMAP = {'dc': PURL_NAMESPACE, 'opf': OPF_NAMESPACE}


def updateEpub(src, dest, filename, data, ):
    # create a temp copy of the archive without filename
    with zipfile.ZipFile(src, 'r') as zin:
        with zipfile.ZipFile(dest, 'w') as zout:
            zout.comment = zin.comment  # preserve the comment
            for item in zin.infolist():
                if item.filename != filename:
                    zout.writestr(item, zin.read(item.filename))

    # now add filename with its new data
    with zipfile.ZipFile(dest, mode='a', compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(filename, data)


def get_content_opf(file_path, ns=None):
    if ns is None:
        ns = default_ns
    epubZip = zipfile.ZipFile(file_path)
    txt = epubZip.read('META-INF/container.xml')
    tree = etree.fromstring(txt)
    cf_name = tree.xpath('n:rootfiles/n:rootfile/@full-path', namespaces=ns)[0]
    cf = epubZip.read(cf_name)

    return etree.fromstring(cf), cf_name


def create_new_metadata_backup(book,  custom_columns, export_language, translated_cover_name, lang_type=3):
    # generate root package element
    package = etree.Element(OPF + "package", nsmap=OPF_NS)
    package.set("unique-identifier", "uuid_id")
    package.set("version", "2.0")

    # generate metadata element and all sub elements of it
    metadata = etree.SubElement(package, "metadata", nsmap=NSMAP)
    identifier = etree.SubElement(metadata, PURL + "identifier", id="calibre_id", nsmap=NSMAP)
    identifier.set(OPF + "scheme", "calibre")
    identifier.text = str(book.id)
    identifier2 = etree.SubElement(metadata, PURL + "identifier", id="uuid_id", nsmap=NSMAP)
    identifier2.set(OPF + "scheme", "uuid")
    identifier2.text = book.uuid
    for i in book.identifiers:
        identifier = etree.SubElement(metadata, PURL + "identifier", nsmap=NSMAP)
        identifier.set(OPF + "scheme", i.format_type())
        identifier.text = str(i.val)
    title = etree.SubElement(metadata, PURL + "title", nsmap=NSMAP)
    title.text = book.title
    for author in book.authors:
        creator = etree.SubElement(metadata, PURL + "creator", nsmap=NSMAP)
        creator.text = str(author.name)
        creator.set(OPF + "file-as", book.author_sort)     # ToDo Check
        creator.set(OPF + "role", "aut")
    contributor = etree.SubElement(metadata, PURL + "contributor", nsmap=NSMAP)
    contributor.text = "calibre (5.7.2) [https://calibre-ebook.com]"
    contributor.set(OPF + "file-as", "calibre")     # ToDo Check
    contributor.set(OPF + "role", "bkp")

    date = etree.SubElement(metadata, PURL + "date", nsmap=NSMAP)
    date.text = '{d.year:04}-{d.month:02}-{d.day:02}T{d.hour:02}:{d.minute:02}:{d.second:02}'.format(d=book.pubdate)
    if book.comments and book.comments[0].text:
        for b in book.comments:
            description = etree.SubElement(metadata, PURL + "description", nsmap=NSMAP)
            description.text = b.text
    for b in book.publishers:
        publisher = etree.SubElement(metadata, PURL + "publisher", nsmap=NSMAP)
        publisher.text = str(b.name)
    if not book.languages:
        language = etree.SubElement(metadata, PURL + "language", nsmap=NSMAP)
        language.text = export_language
    else:
        for b in book.languages:
            language = etree.SubElement(metadata, PURL + "language", nsmap=NSMAP)
            language.text = str(b.lang_code) if lang_type == 3 else isoLanguages.get(part3=b.lang_code).part1
    for b in book.tags:
        subject = etree.SubElement(metadata, PURL + "subject", nsmap=NSMAP)
        subject.text = str(b.name)
    etree.SubElement(metadata, "meta", name="calibre:author_link_map",
                     content="{" + ", ".join(['"' + str(a.name) + '": ""' for a in book.authors]) + "}",
                     nsmap=NSMAP)
    for b in book.series:
        etree.SubElement(metadata, "meta", name="calibre:series",
                         content=str(str(b.name)),
                         nsmap=NSMAP)
    if book.series:
        etree.SubElement(metadata, "meta", name="calibre:series_index",
                         content=str(book.series_index),
                         nsmap=NSMAP)
    if len(book.ratings) and book.ratings[0].rating > 0:
        etree.SubElement(metadata, "meta", name="calibre:rating",
                         content=str(book.ratings[0].rating),
                         nsmap=NSMAP)
    etree.SubElement(metadata, "meta", name="calibre:timestamp",
                     content='{d.year:04}-{d.month:02}-{d.day:02}T{d.hour:02}:{d.minute:02}:{d.second:02}'.format(
                         d=book.timestamp),
                     nsmap=NSMAP)
    etree.SubElement(metadata, "meta", name="calibre:title_sort",
                     content=book.sort,
                     nsmap=NSMAP)
    sequence = 0
    for cc in custom_columns:
        value = None
        extra = None
        cc_entry = getattr(book, "custom_column_" + str(cc.id))
        if cc_entry.__len__():
            value = [c.value for c in cc_entry] if cc.is_multiple else cc_entry[0].value
            extra = cc_entry[0].extra if hasattr(cc_entry[0], "extra") else None
        etree.SubElement(metadata, "meta", name="calibre:user_metadata:#{}".format(cc.label),
                         content=cc.to_json(value, extra, sequence),
                         nsmap=NSMAP)
        sequence += 1

    # generate guide element and all sub elements of it
    # Title is translated from default export language
    guide = etree.SubElement(package, "guide")
    etree.SubElement(guide, "reference", type="cover", title=translated_cover_name, href="cover.jpg")

    return package


def replace_metadata(tree, package):
    rep_element = tree.xpath('/pkg:package/pkg:metadata', namespaces=default_ns)[0]
    new_element = package.xpath('//metadata', namespaces=default_ns)[0]
    tree.replace(rep_element, new_element)
    return etree.tostring(tree,
                          xml_declaration=True,
                          encoding='utf-8',
                          pretty_print=True).decode('utf-8')


