# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2012-2019 lemmsh cervinko Kennyl matthazinski OzzieIsaacs
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

from __future__ import division, print_function, unicode_literals
import os
import hashlib
from tempfile import gettempdir
from flask_babel import gettext as _

from . import logger, comic
from .constants import BookMeta


log = logger.create()


try:
    from lxml.etree import LXML_VERSION as lxmlversion
except ImportError:
    lxmlversion = None

try:
    from wand.image import Image
    from wand import version as ImageVersion
    from wand.exceptions import PolicyError
    use_generic_pdf_cover = False
except (ImportError, RuntimeError) as e:
    log.debug('Cannot import Image, generating pdf covers for pdf uploads will not work: %s', e)
    use_generic_pdf_cover = True

try:
    from PyPDF2 import PdfFileReader
    from PyPDF2 import __version__ as PyPdfVersion
    use_pdf_meta = True
except ImportError as e:
    log.debug('Cannot import PyPDF2, extracting pdf metadata will not work: %s', e)
    use_pdf_meta = False

try:
    from . import epub
    use_epub_meta = True
except ImportError as e:
    log.debug('Cannot import epub, extracting epub metadata will not work: %s', e)
    use_epub_meta = False

try:
    from . import fb2
    use_fb2_meta = True
except ImportError as e:
    log.debug('Cannot import fb2, extracting fb2 metadata will not work: %s', e)
    use_fb2_meta = False

try:
    from PIL import Image as PILImage
    from PIL import __version__ as PILversion
    use_PIL = True
except ImportError as e:
    log.debug('Cannot import Pillow, using png and webp images as cover will not work: %s', e)
    use_PIL = False


def process(tmp_file_path, original_file_name, original_file_extension, rarExecutable):
    meta = None
    extension_upper = original_file_extension.upper()
    try:
        if ".PDF" == extension_upper:
            meta = pdf_meta(tmp_file_path, original_file_name, original_file_extension)
        elif extension_upper in [".KEPUB", ".EPUB"] and use_epub_meta is True:
            meta = epub.get_epub_info(tmp_file_path, original_file_name, original_file_extension)
        elif ".FB2" == extension_upper and use_fb2_meta is True:
            meta = fb2.get_fb2_info(tmp_file_path, original_file_extension)
        elif extension_upper in ['.CBZ', '.CBT', '.CBR']:
            meta = comic.get_comic_info(tmp_file_path,
                                        original_file_name,
                                        original_file_extension,
                                        rarExecutable)
    except Exception as ex:
        log.warning('cannot parse metadata, using default: %s', ex)

    if meta and meta.title.strip() and meta.author.strip():
        if meta.author.lower() == 'unknown':
            meta = meta._replace(author=_(u'Unknown'))
        return meta
    return default_meta(tmp_file_path, original_file_name, original_file_extension)


def default_meta(tmp_file_path, original_file_name, original_file_extension):
    return BookMeta(
        file_path=tmp_file_path,
        extension=original_file_extension,
        title=original_file_name,
        author=_(u'Unknown'),
        cover=None,
        description="",
        tags="",
        series="",
        series_id="",
        languages="")


def pdf_meta(tmp_file_path, original_file_name, original_file_extension):
    doc_info = None
    if use_pdf_meta:
        doc_info = PdfFileReader(open(tmp_file_path, 'rb')).getDocumentInfo()

    if doc_info:
        author = doc_info.author if doc_info.author else u'Unknown'
        title = doc_info.title if doc_info.title else original_file_name
        subject = doc_info.subject
    else:
        author = u'Unknown'
        title = original_file_name
        subject = ""

    return BookMeta(
        file_path=tmp_file_path,
        extension=original_file_extension,
        title=title,
        author=author,
        cover=pdf_preview(tmp_file_path, original_file_name),
        description=subject,
        tags="",
        series="",
        series_id="",
        languages="")


def pdf_preview(tmp_file_path, tmp_dir):
    if use_generic_pdf_cover:
        return None
    try:
        cover_file_name = os.path.splitext(tmp_file_path)[0] + ".cover.jpg"
        with Image() as img:
            img.options["pdf:use-cropbox"] = "true"
            img.read(filename=tmp_file_path + '[0]', resolution=150)
            img.compression_quality = 88
            img.save(filename=os.path.join(tmp_dir, cover_file_name))
        return cover_file_name
    except PolicyError as ex:
        log.warning('Pdf extraction forbidden by Imagemagick policy: %s', ex)
        return None
    except Exception as ex:
        log.warning('Cannot extract cover image, using default: %s', ex)
        return None


def get_versions():
    if not use_generic_pdf_cover:
        IVersion = ImageVersion.MAGICK_VERSION
        WVersion = ImageVersion.VERSION
    else:
        IVersion = u'not installed'
        WVersion = u'not installed'
    if use_pdf_meta:
        PVersion='v'+PyPdfVersion
    else:
        PVersion=u'not installed'
    if lxmlversion:
        XVersion = 'v'+'.'.join(map(str, lxmlversion))
    else:
        XVersion = u'not installed'
    if use_PIL:
        PILVersion = 'v' + PILversion
    else:
        PILVersion = u'not installed'
    if comic.use_comic_meta:
        ComicVersion = comic.comic_version or u'installed'
    else:
        ComicVersion = u'not installed'
    return {'Image Magick': IVersion,
            'PyPdf': PVersion,
            'lxml':XVersion,
            'Wand': WVersion,
            'Pillow': PILVersion,
            'Comic_API': ComicVersion}


def upload(uploadfile, rarExcecutable):
    tmp_dir = os.path.join(gettempdir(), 'calibre_web')

    if not os.path.isdir(tmp_dir):
        os.mkdir(tmp_dir)

    filename = uploadfile.filename
    filename_root, file_extension = os.path.splitext(filename)
    md5 = hashlib.md5(filename.encode('utf-8')).hexdigest()
    tmp_file_path = os.path.join(tmp_dir, md5)
    log.debug("Temporary file: %s", tmp_file_path)
    uploadfile.save(tmp_file_path)
    return process(tmp_file_path, filename_root, file_extension, rarExcecutable)
