#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#     Copyright (C) 2018 OzzieIsaacs
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
import uploader
import logging
from iso639 import languages as isoLanguages


logger = logging.getLogger("book_formats")

try:
    from comicapi.comicarchive import ComicArchive, MetaDataStyle
    use_comic_meta = True
except ImportError as e:
    logger.warning('cannot import comicapi, extracting comic metadata will not work: %s', e)
    import zipfile
    import tarfile
    use_comic_meta = False


def extractCover(tmp_file_name, original_file_extension):
    if use_comic_meta:
        archive = ComicArchive(tmp_file_name)
        cover_data = None
        ext = os.path.splitext(archive.getPageName(0))
        if len(ext) > 1:
            extension = ext[1].lower()
            if extension == '.jpg' or extension == '.jpeg':
                cover_data = archive.getPage(0)
    else:
        if original_file_extension.upper() == '.CBZ':
            cf = zipfile.ZipFile(tmp_file_name)
            for name in cf.namelist():
                ext = os.path.splitext(name)
                if len(ext) > 1:
                    extension = ext[1].lower()
                    if extension == '.jpg':
                        cover_data = cf.read(name)
                        break
        elif original_file_extension.upper() == '.CBT':
            cf = tarfile.TarFile(tmp_file_name)
            for name in cf.getnames():
                ext = os.path.splitext(name)
                if len(ext) > 1:
                    extension = ext[1].lower()
                    if extension == '.jpg':
                        cover_data = cf.extractfile(name).read()
                        break
    prefix = os.path.dirname(tmp_file_name)
    if cover_data:
        tmp_cover_name = prefix + '/cover' + extension
        image = open(tmp_cover_name, 'wb')
        image.write(cover_data)
        image.close()
    else:
        tmp_cover_name = None
    return tmp_cover_name


def get_comic_info(tmp_file_path, original_file_name, original_file_extension):
    if use_comic_meta:
        archive = ComicArchive(tmp_file_path)
        if archive.seemsToBeAComicArchive():
            if archive.hasMetadata(MetaDataStyle.CIX):
                style = MetaDataStyle.CIX
            elif archive.hasMetadata(MetaDataStyle.CBI):
                style = MetaDataStyle.CBI
            else:
                style = None

            if style is not None:
                loadedMetadata = archive.readMetadata(style)

        lang = loadedMetadata.language
        if len(lang) == 2:
             loadedMetadata.language = isoLanguages.get(part1=lang).name
        elif len(lang) == 3:
             loadedMetadata.language = isoLanguages.get(part3=lang).name
        else:
             loadedMetadata.language = ""

        return uploader.BookMeta(
                file_path=tmp_file_path,
                extension=original_file_extension,
                title=loadedMetadata.title or original_file_name,
                author=" & ".join([credit["person"] for credit in loadedMetadata.credits if credit["role"] == "Writer"]) or u"Unknown",
                cover=extractCover(tmp_file_path, original_file_extension),
                description=loadedMetadata.comments or "",
                tags="",
                series=loadedMetadata.series or "",
                series_id=loadedMetadata.issue or "",
                languages=loadedMetadata.language)
    else:

        return uploader.BookMeta(
            file_path=tmp_file_path,
            extension=original_file_extension,
            title=original_file_name,
            author=u"Unknown",
            cover=extractCover(tmp_file_path, original_file_extension),
            description="",
            tags="",
            series="",
            series_id="",
            languages="")
