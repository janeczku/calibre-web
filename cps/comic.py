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

from __future__ import division, print_function, unicode_literals
import os
import io

from . import logger, isoLanguages
from .constants import BookMeta

try:
    from PIL import Image as PILImage
    use_PIL = True
except ImportError as e:
    use_PIL = False


log = logger.create()


try:
    from comicapi.comicarchive import ComicArchive, MetaDataStyle
    use_comic_meta = True
    try:
        from comicapi import __version__ as comic_version
    except (ImportError):
        comic_version = ''
except ImportError as e:
    log.debug('Cannot import comicapi, extracting comic metadata will not work: %s', e)
    import zipfile
    import tarfile
    try:
        import rarfile
        use_rarfile = True
    except ImportError as e:
        log.debug('Cannot import rarfile, extracting cover files from rar files will not work: %s', e)
        use_rarfile = False
    use_comic_meta = False

def _cover_processing(tmp_file_name, img, extension):
    if use_PIL:
        # convert to jpg because calibre only supports jpg
        if extension in ('.png',  '.webp'):
            imgc = PILImage.open(io.BytesIO(img))
            im = imgc.convert('RGB')
            tmp_bytesio = io.BytesIO()
            im.save(tmp_bytesio, format='JPEG')
            img = tmp_bytesio.getvalue()

    prefix = os.path.dirname(tmp_file_name)
    if img:
        tmp_cover_name = prefix + '/cover.jpg'
        image = open(tmp_cover_name, 'wb')
        image.write(img)
        image.close()
    else:
        tmp_cover_name = None
    return tmp_cover_name



def _extractCover(tmp_file_name, original_file_extension, rarExceutable):
    cover_data = extension = None
    if use_comic_meta:
        archive = ComicArchive(tmp_file_name)
        for index, name in enumerate(archive.getPageNameList()):
            ext = os.path.splitext(name)
            if len(ext) > 1:
                extension = ext[1].lower()
                if extension in ('.jpg', '.jpeg', '.png', '.webp'):
                    cover_data = archive.getPage(index)
                    break
    else:
        if original_file_extension.upper() == '.CBZ':
            cf = zipfile.ZipFile(tmp_file_name)
            for name in cf.namelist():
                ext = os.path.splitext(name)
                if len(ext) > 1:
                    extension = ext[1].lower()
                    if extension in ('.jpg', '.jpeg', '.png', '.webp'):
                        cover_data = cf.read(name)
                        break
        elif original_file_extension.upper() == '.CBT':
            cf = tarfile.TarFile(tmp_file_name)
            for name in cf.getnames():
                ext = os.path.splitext(name)
                if len(ext) > 1:
                    extension = ext[1].lower()
                    if extension in ('.jpg', '.jpeg', '.png', '.webp'):
                        cover_data = cf.extractfile(name).read()
                        break
        elif original_file_extension.upper() == '.CBR' and use_rarfile:
            try:
                rarfile.UNRAR_TOOL = rarExceutable
                cf = rarfile.RarFile(tmp_file_name)
                for name in cf.getnames():
                    ext = os.path.splitext(name)
                    if len(ext) > 1:
                        extension = ext[1].lower()
                        if extension in ('.jpg', '.jpeg', '.png', '.webp'):
                            cover_data = cf.read(name)
                            break
            except Exception as e:
                log.debug('Rarfile failed with error: %s', e)
    return _cover_processing(tmp_file_name, cover_data, extension)


def get_comic_info(tmp_file_path, original_file_name, original_file_extension, rarExceutable):
    if use_comic_meta:
        archive = ComicArchive(tmp_file_path, rar_exe_path=rarExceutable)
        if archive.seemsToBeAComicArchive():
            if archive.hasMetadata(MetaDataStyle.CIX):
                style = MetaDataStyle.CIX
            elif archive.hasMetadata(MetaDataStyle.CBI):
                style = MetaDataStyle.CBI
            else:
                style = None

            # if style is not None:
            loadedMetadata = archive.readMetadata(style)

            lang = loadedMetadata.language
            if lang:
                if len(lang) == 2:
                     loadedMetadata.language = isoLanguages.get(part1=lang).name
                elif len(lang) == 3:
                     loadedMetadata.language = isoLanguages.get(part3=lang).name
            else:
                 loadedMetadata.language = ""

            return BookMeta(
                file_path=tmp_file_path,
                extension=original_file_extension,
                title=loadedMetadata.title or original_file_name,
                author=" & ".join([credit["person"] for credit in loadedMetadata.credits if credit["role"] == "Writer"]) or u'Unknown',
                cover=_extractCover(tmp_file_path, original_file_extension, rarExceutable),
                description=loadedMetadata.comments or "",
                tags="",
                series=loadedMetadata.series or "",
                series_id=loadedMetadata.issue or "",
                languages=loadedMetadata.language)

    return BookMeta(
        file_path=tmp_file_path,
        extension=original_file_extension,
        title=original_file_name,
        author=u'Unknown',
        cover=_extractCover(tmp_file_path, original_file_extension, rarExceutable),
        description="",
        tags="",
        series="",
        series_id="",
        languages="")
