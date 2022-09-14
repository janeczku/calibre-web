# -*- coding: utf-8 -*-

#   This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#     Copyright (C) 2020 monkey
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program. If not, see <http://www.gnu.org/licenses/>.

import os
from lxml import objectify
from urllib.request import urlopen
from lxml import etree
from html import escape

from cps import config, db, fs, gdriveutils, logger, ub
from cps.services.worker import CalibreTask, STAT_CANCELLED, STAT_ENDED
from flask_babel import lazy_gettext as N_

OPF_NAMESPACE = "http://www.idpf.org/2007/opf"
PURL_NAMESPACE = "http://purl.org/dc/elements/1.1/"

OPF = "{%s}" % OPF_NAMESPACE
PURL = "{%s}" % PURL_NAMESPACE

etree.register_namespace("opf", OPF_NAMESPACE)
etree.register_namespace("dc", PURL_NAMESPACE)

OPF_NS = {None: OPF_NAMESPACE}  # the default namespace (no prefix)
NSMAP = {'dc': PURL_NAMESPACE, 'opf': OPF_NAMESPACE}


class TaskBackupMetadata(CalibreTask):

    def __init__(self, export_language="en", translated_title="cover", task_message=N_('Backing up Metadata')):
        super(TaskBackupMetadata, self).__init__(task_message)
        self.log = logger.create()
        self.calibre_db = db.CalibreDB(expire_on_commit=False, init=True)
        self.export_language = export_language
        self.translated_title = translated_title

    def run(self, worker_thread):
        try:
            metadata_backup = self.calibre_db.session.query(db.Metadata_Dirtied).all()
            custom_columns = self.calibre_db.session.query(db.CustomColumns).order_by(db.CustomColumns.label).all()
            for backup in metadata_backup:
                book = self.calibre_db.session.query(db.Books).filter(db.Books.id == backup.book).one_or_none()
                # self.calibre_db.session.query(db.Metadata_Dirtied).filter(db.Metadata_Dirtied == backup.id).delete()
                # self.calibre_db.session.commit()
                if book:
                    self.open_metadata(book, custom_columns)
                    self._handleSuccess()
                    self.calibre_db.session.close()
                else:
                    self.log.error("Book {} not found in database".format(backup.book))
                    self._handleError("Book {} not found in database".format(backup.book))
                    self.calibre_db.session.close()

        except Exception as ex:
            self.log.debug('Error creating metadata backup: ' + str(ex))
            self._handleError('Error creating metadata backup: ' + str(ex))
            self.calibre_db.session.rollback()
            self.calibre_db.session.close()

    def open_metadata(self, book, custom_columns):
        if config.config_use_google_drive:
            if not gdriveutils.is_gdrive_ready():
                raise Exception('Google Drive is configured but not ready')

            web_content_link = gdriveutils.get_metadata_backup_via_gdrive(book.path)
            if not web_content_link:
                raise Exception('Google Drive cover url not found')

            stream = None
            try:
                stream = urlopen(web_content_link)
            except Exception as ex:
                # Bubble exception to calling function
                self.log.debug('Error reading metadata.opf: ' + str(ex))       # ToDo Chek whats going on
                raise ex
            finally:
                if stream is not None:
                    stream.close()
        else:
            # ToDo: Handle book folder not found or not readable
            book_metadata_filepath = os.path.join(config.config_calibre_dir, book.path, 'metadata.opf')
            #if not os.path.isfile(book_metadata_filepath):
            self.create_new_metadata_backup(book,  custom_columns, book_metadata_filepath)
            # else:
                '''namespaces = {'dc': PURL_NAMESPACE, 'opf': OPF_NAMESPACE}
                test = etree.parse(book_metadata_filepath)
                root = test.getroot()
                for i in root.iter():
                    self.log.info(i)
                title = root.find("dc:metadata", namespaces)
                pass'''
                with open(book_metadata_filepath, "rb") as f:
                    xml = f.read()

                root = objectify.fromstring(xml)
                # root.metadata['{http://purl.org/dc/elements/1.1/}title']
                # root.metadata[PURL + 'title']
                # getattr(root.metadata, PURL +'title')
                # test = objectify.parse()
                pass
                # backup not found has to be created
                #raise Exception('Book cover file not found')

    def create_new_metadata_backup(self, book,  custom_columns, book_metadata_filepath):
        # generate root package element
        package = etree.Element(OPF + "package", nsmap=OPF_NS)
        package.set("unique-identifier", "uuid_id")
        package.set("version", "2.0")

        # generate metadata element and all subelements of it
        metadata = etree.SubElement(package, "metadata", nsmap=NSMAP)
        identifier = etree.SubElement(metadata, PURL + "identifier", id="calibre_id", nsmap=NSMAP)
        identifier.set(OPF + "scheme", "calibre")
        identifier.text = str(book.id)
        identifier2 = etree.SubElement(metadata, PURL + "identifier", id="uuid_id", nsmap=NSMAP)
        identifier2.set(OPF + "scheme", "uuid")
        identifier2.text = book.uuid
        title = etree.SubElement(metadata, PURL + "title", nsmap=NSMAP)
        title.text = book.title
        for author in book.authors:
            creator = etree.SubElement(metadata, PURL + "creator", nsmap=NSMAP)
            creator.text = str(author)
            creator.set(OPF + "file-as", book.author_sort)     # ToDo Check
            creator.set(OPF + "role", "aut")
        contributor = etree.SubElement(metadata, PURL + "contributor", nsmap=NSMAP)
        contributor.text = "calibre (5.7.2) [https://calibre-ebook.com]"
        contributor.set(OPF + "file-as", "calibre")     # ToDo Check
        contributor.set(OPF + "role", "bpk")

        date = etree.SubElement(metadata, PURL + "date", nsmap=NSMAP)
        date.text = '{d.year:04}-{d.month:02}-{d.day:02}T{d.hour:02}:{d.minute:02}:{d.second:02}'.format(d=book.pubdate)

        if not book.languages:
            language = etree.SubElement(metadata, PURL + "language", nsmap=NSMAP)
            language.text = self.export_language
        else:
            for b in book.languages:
                language = etree.SubElement(metadata, PURL + "language", nsmap=NSMAP)
                language.text = str(b.languages)
        for b in book.tags:
            subject = etree.SubElement(metadata, PURL + "subject", nsmap=NSMAP)
            subject.text = str(b.tags)
        if book.comments:
            description = etree.SubElement(metadata, PURL + "description", nsmap=NSMAP)
            description.text = escape(str(book.comments))
        etree.SubElement(metadata, "meta", name="calibre:author_link_map",
                         content="{" + escape(",".join(['"' + str(a) + '":""' for a in book.authors])) + "}",
                         nsmap=NSMAP)
        etree.SubElement(metadata, "meta", name="calibre:series",
                         content=str(book.series),
                         nsmap=NSMAP)
        etree.SubElement(metadata, "meta", name="calibre:series_index",
                         content=str(book.series_index),
                         nsmap=NSMAP)
        etree.SubElement(metadata, "meta", name="calibre:timestamp",
                         content='{d.year:04}-{d.month:02}-{d.day:02}T{d.hour:02}:{d.minute:02}:{d.second:02}'.format(
                             d=book.timestamp),
                         nsmap=NSMAP)
        etree.SubElement(metadata, "meta", name="calibre:title_sort",
                         content=book.sort,
                         nsmap=NSMAP)
        for cc in custom_columns:
            value = None
            extra = None
            cc_entry = getattr(book, "custom_column_" + str(cc.id))
            if cc_entry.__len__():
                value = cc_entry[0].get("value")
                extra = cc_entry[0].get("extra")
            etree.SubElement(metadata, "meta", name="calibre:user_metadata:#{}".format(cc.label),
                             content=escape(cc.to_json(value, extra)),
                             nsmap=NSMAP)

        # generate guide element and all sub elements of it
        # Title is translated from default export language
        guide = etree.SubElement(package, "guide")
        etree.SubElement(guide, "reference", type="cover", title=self.translated_title, href="cover.jpg")

        # prepare finalize everything and output
        doc = etree.ElementTree(package)
        try:
            with open(book_metadata_filepath, 'wb') as f:
                doc.write(f, xml_declaration=True, encoding='utf-8', pretty_print=True)
        except Exception:
            # ToDo: Folder not writeable errror
            pass
    @property
    def name(self):
        return "Backing up Metadata"

    @property
    def is_cancellable(self):
        return True
