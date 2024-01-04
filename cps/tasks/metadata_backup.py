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
from urllib.request import urlopen
from lxml import etree


from cps import config, db, gdriveutils, logger
from cps.services.worker import CalibreTask
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

    def __init__(self, export_language="en",
                 translated_title="Cover",
                 set_dirty=False,
                 task_message=N_('Backing up Metadata')):
        super(TaskBackupMetadata, self).__init__(task_message)
        self.log = logger.create()
        self.calibre_db = db.CalibreDB(expire_on_commit=False, init=True)
        self.export_language = export_language
        self.translated_title = translated_title
        self.set_dirty = set_dirty

    def run(self, worker_thread):
        if self.set_dirty:
            self.set_all_books_dirty()
        else:
            self.backup_metadata()

    def set_all_books_dirty(self):
        try:
            books = self.calibre_db.session.query(db.Books).all()
            for book in books:
                self.calibre_db.set_metadata_dirty(book.id)
            self.calibre_db.session.commit()
            self._handleSuccess()
        except Exception as ex:
            self.log.debug('Error adding book for backup: ' + str(ex))
            self._handleError('Error adding book for backup: ' + str(ex))
            self.calibre_db.session.rollback()
        self.calibre_db.session.close()

    def backup_metadata(self):
        try:
            metadata_backup = self.calibre_db.session.query(db.Metadata_Dirtied).all()
            custom_columns = (self.calibre_db.session.query(db.CustomColumns)
                              .filter(db.CustomColumns.mark_for_delete == 0)
                              .filter(db.CustomColumns.datatype.notin_(db.cc_exceptions))
                              .order_by(db.CustomColumns.label).all())
            count = len(metadata_backup)
            i = 0
            for backup in metadata_backup:
                book = self.calibre_db.session.query(db.Books).filter(db.Books.id == backup.book).one_or_none()
                self.calibre_db.session.query(db.Metadata_Dirtied).filter(
                    db.Metadata_Dirtied.book == backup.book).delete()
                self.calibre_db.session.commit()
                if book:
                    self.open_metadata(book, custom_columns)
                else:
                    self.log.error("Book {} not found in database".format(backup.book))
                i += 1
                self.progress = (1.0 / count) * i
            self._handleSuccess()
            self.calibre_db.session.close()

        except Exception as ex:
            b = "NaN" if not hasattr(book, 'id') else book.id
            self.log.debug('Error creating metadata backup for book {}: '.format(b) + str(ex))
            self._handleError('Error creating metadata backup: ' + str(ex))
            self.calibre_db.session.rollback()
            self.calibre_db.session.close()

    def open_metadata(self, book, custom_columns):
        package = self.create_new_metadata_backup(book, custom_columns)
        if config.config_use_google_drive:
            if not gdriveutils.is_gdrive_ready():
                raise Exception('Google Drive is configured but not ready')

            gdriveutils.uploadFileToEbooksFolder(os.path.join(book.path, 'metadata.opf').replace("\\", "/"),
                                                 etree.tostring(package,
                                                                xml_declaration=True,
                                                                encoding='utf-8',
                                                                pretty_print=True).decode('utf-8'),
                                                 True)
        else:
            # ToDo: Handle book folder not found or not readable
            book_metadata_filepath = os.path.join(config.config_calibre_dir, book.path, 'metadata.opf')
            # prepare finalize everything and output
            doc = etree.ElementTree(package)
            try:
                with open(book_metadata_filepath, 'wb') as f:
                    doc.write(f, xml_declaration=True, encoding='utf-8', pretty_print=True)
            except Exception as ex:
                raise Exception('Writing Metadata failed with error: {} '.format(ex))

    def create_new_metadata_backup(self, book,  custom_columns):
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
            language.text = self.export_language
        else:
            for b in book.languages:
                language = etree.SubElement(metadata, PURL + "language", nsmap=NSMAP)
                language.text = str(b.lang_code)
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
        etree.SubElement(guide, "reference", type="cover", title=self.translated_title, href="cover.jpg")

        return package

    @property
    def name(self):
        return "Metadata backup"

    # needed for logging
    def __str__(self):
        if self.set_dirty:
            return "Queue all books for metadata backup"
        else:
            return "Perform metadata backup"

    @property
    def is_cancellable(self):
        return True
