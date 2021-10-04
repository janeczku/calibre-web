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

from . import logger, isoLanguages
from .constants import BookMeta


log = logger.create()


try:
    from wand.image import Image
    use_IM = True
except (ImportError, RuntimeError) as e:
    use_IM = False


try:
    from comicapi.comicarchive import ComicArchive, MetaDataStyle
    use_comic_meta = True
    try:
        from comicapi import __version__ as comic_version
    except ImportError:
        comic_version = ''
except (ImportError, LookupError) as e:
    log.debug('Cannot import comicapi, extracting comic metadata will not work: %s', e)
    import zipfile
    import tarfile
    try:
        import rarfile
        use_rarfile = True
    except (ImportError, SyntaxError) as e:
        log.debug('Cannot import rarfile, extracting cover files from rar files will not work: %s', e)
        use_rarfile = False
    use_comic_meta = False

NO_JPEG_EXTENSIONS = ['.png', '.webp', '.bmp']
COVER_EXTENSIONS = ['.png', '.webp', '.bmp', '.jpg', '.jpeg']

def _cover_processing(tmp_file_name, img, extension):
    tmp_cover_name = os.path.join(os.path.dirname(tmp_file_name), 'cover.jpg')
    if use_IM:
        # convert to jpg because calibre only supports jpg
        if extension in NO_JPEG_EXTENSIONS:
            with Image(filename=tmp_file_name) as imgc:
                imgc.format = 'jpeg'
                imgc.transform_colorspace('rgb')
                imgc.save(tmp_cover_name)
                return tmp_cover_name

    if not img:
        return None

    with open(tmp_cover_name, 'wb') as f:
        f.write(img)
    return tmp_cover_name


def _extract_Cover_from_archive(original_file_extension, tmp_file_name, rarExecutable):
    cover_data = None
    if original_file_extension.upper() == '.CBZ':
        cf = zipfile.ZipFile(tmp_file_name)
        for name in cf.namelist():
            ext = os.path.splitext(name)
            if len(ext) > 1:
                extension = ext[1].lower()
                if extension in COVER_EXTENSIONS:
                    cover_data = cf.read(name)
                    break
    elif original_file_extension.upper() == '.CBT':
        cf = tarfile.TarFile(tmp_file_name)
        for name in cf.getnames():
            ext = os.path.splitext(name)
            if len(ext) > 1:
                extension = ext[1].lower()
                if extension in COVER_EXTENSIONS:
                    cover_data = cf.extractfile(name).read()
                    break
    elif original_file_extension.upper() == '.CBR' and use_rarfile:
        try:
            rarfile.UNRAR_TOOL = rarExecutable
            cf = rarfile.RarFile(tmp_file_name)
            for name in cf.getnames():
                ext = os.path.splitext(name)
                if len(ext) > 1:
                    extension = ext[1].lower()
                    if extension in COVER_EXTENSIONS:
                        cover_data = cf.read(name)
                        break
        except Exception as ex:
            log.debug('Rarfile failed with error: %s', ex)
    return cover_data


def _extractCover(tmp_file_name, original_file_extension, rarExecutable):
    cover_data = extension = None
    if use_comic_meta:
        archive = ComicArchive(tmp_file_name, rar_exe_path=rarExecutable)
        for index, name in enumerate(archive.getPageNameList()):
            ext = os.path.splitext(name)
            if len(ext) > 1:
                extension = ext[1].lower()
                if extension in COVER_EXTENSIONS:
                    cover_data = archive.getPage(index)
                    break
    else:
        cover_data = _extract_Cover_from_archive(original_file_extension, tmp_file_name, rarExecutable)
    return _cover_processing(tmp_file_name, cover_data, extension)


def get_comic_info(tmp_file_path, original_file_name, original_file_extension, rarExecutable):
    if use_comic_meta:
        archive = ComicArchive(tmp_file_path, rar_exe_path=rarExecutable)
        if archive.seemsToBeAComicArchive():
            if archive.hasMetadata(MetaDataStyle.CIX):
                style = MetaDataStyle.CIX
            elif archive.hasMetadata(MetaDataStyle.CBI):
                style = MetaDataStyle.CBI
            else:
                style = None

            # if style is not None:
            loadedMetadata = archive.readMetadata(style)

            lang = loadedMetadata.language or ""
            loadedMetadata.language = isoLanguages.get_lang3(lang)

            return BookMeta(
                file_path=tmp_file_path,
                extension=original_file_extension,
                title=loadedMetadata.title or original_file_name,
                author=" & ".join([credit["person"]
                                   for credit in loadedMetadata.credits if credit["role"] == "Writer"]) or u'Unknown',
                cover=_extractCover(tmp_file_path, original_file_extension, rarExecutable),
                description=loadedMetadata.comments or "",
                tags="",
                series=loadedMetadata.series or "",
                series_id=loadedMetadata.issue or "",
                languages=loadedMetadata.language,
                publisher="")

    return BookMeta(
        file_path=tmp_file_path,
        extension=original_file_extension,
        title=original_file_name,
        author=u'Unknown',
        cover=_extractCover(tmp_file_path, original_file_extension, rarExecutable),
        description="",
        tags="",
        series="",
        series_id="",
        languages="",
        publisher="")
