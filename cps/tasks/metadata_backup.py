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
import datetime
import os
import json
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

    def __init__(self, task_message=N_('Backing up Metadata')):
        super(TaskBackupMetadata, self).__init__(task_message)
        self.log = logger.create()
        self.db_session = db.CalibreDB(expire_on_commit=False, init=True).session

    def run(self, worker_thread):
        try:
            metadata_backup = self.db_session.query(db.Metadata_Dirtied).all()
            custom_columns = self.db_session.query(db.CustomColumns).all()
            for backup in metadata_backup:
                book = self.db_session.query(db.Books).filter(db.Books.id == backup.book).one_or_none()
                # self.db_session.query(db.Metadata_Dirtied).filter(db.Metadata_Dirtied == backup.id).delete()
                # self.db_session.commit()
                if book:
                    metadata_file = self.open_metadata(book, custom_columns)
                    self._handleSuccess()
                    self.db_session.remove()
                else:
                    self.log.error("Book {} not found in database".format(backup.book))
                    self._handleError("Book {} not found in database".format(backup.book))
                    self.db_session.remove()

        except Exception as ex:
            self.log.debug('Error creating metadata backup: ' + str(ex))
            self._handleError('Error creating metadata backup: ' + str(ex))
            self.db_session.rollback()
            self.db_session.remove()

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
            book_metadata_filepath = os.path.join(config.config_calibre_dir, book.path, 'metadata.opf')
            if not os.path.isfile(book_metadata_filepath):
                self.create_new_metadata_backup(book,  custom_columns, book_metadata_filepath)
                # ToDo What to do
                return open(book_metadata_filepath, "w")
            else:
                etree.parse(book_metadata_filepath)
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
        date.text = datetime.datetime.strftime(book.pubdate, "%Y-%m-%dT%H:%M:%S+00:00")
        language = etree.SubElement(metadata, PURL + "language", nsmap=NSMAP)
        if book.languages:
            language.text = str(book.languages)
        else:
            language.text = ""  # ToDo: insert locale (2 letter code)
        if book.tags:
            subject = etree.SubElement(metadata, PURL + "subject", nsmap=NSMAP)
            subject.text = str(book.tags)
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
                         content=datetime.datetime.strftime(book.timestamp, "%Y-%m-%dT%H:%M:%S+00:00"),
                         nsmap=NSMAP)
        etree.SubElement(metadata, "meta", name="calibre:title_sort",
                         content=book.sort,
                         nsmap=NSMAP)
        for cc in custom_columns:
            etree.SubElement(metadata, "meta", name="calibre:user_metadata:#{}".format(cc.label),
                             content=escape(cc.get_display_dict()),
                             nsmap=NSMAP)

            pass

        # generate guide element and all sub elements of it
        guide = etree.SubElement(package, "guide")
        etree.SubElement(guide, "reference", type="cover", title="Titelbild", href="cover.jpg")

        # prepare finalize everything and output
        doc = etree.ElementTree(package)
        with open(book_metadata_filepath, 'wb') as f:
            doc.write(f, xml_declaration=True, encoding='utf-8', pretty_print=True)

    @property
    def name(self):
        return "Backing up Metadata"

    @property
    def is_cancellable(self):
        return True
