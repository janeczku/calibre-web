#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#     Copyright (C) 2016-2019 lemmsh cervinko Kennyl matthazinski OzzieIsaacs
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

import logging
import uploader
import os
from flask_babel import gettext as _
import comic

try:
    from lxml.etree import LXML_VERSION as lxmlversion
except ImportError:
    lxmlversion = None

__author__ = 'lemmsh'

logger = logging.getLogger("book_formats")

try:
    from wand.image import Image
    from wand import version as ImageVersion
    from wand.exceptions import PolicyError
    use_generic_pdf_cover = False
except (ImportError, RuntimeError) as e:
    logger.warning('cannot import Image, generating pdf covers for pdf uploads will not work: %s', e)
    use_generic_pdf_cover = True
try:
    from PyPDF2 import PdfFileReader
    from PyPDF2 import __version__ as PyPdfVersion
    use_pdf_meta = True
except ImportError as e:
    logger.warning('cannot import PyPDF2, extracting pdf metadata will not work: %s', e)
    use_pdf_meta = False

try:
    import epub
    use_epub_meta = True
except ImportError as e:
    logger.warning('cannot import epub, extracting epub metadata will not work: %s', e)
    use_epub_meta = False

try:
    import fb2
    use_fb2_meta = True
except ImportError as e:
    logger.warning('cannot import fb2, extracting fb2 metadata will not work: %s', e)
    use_fb2_meta = False

try:
    from PIL import Image
    from PIL import __version__ as PILversion
    use_PIL = True
except ImportError:
    use_PIL = False


def process(tmp_file_path, original_file_name, original_file_extension):
    meta = None
    try:
        if ".PDF" == original_file_extension.upper():
            meta = pdf_meta(tmp_file_path, original_file_name, original_file_extension)
        if ".EPUB" == original_file_extension.upper() and use_epub_meta is True:
            meta = epub.get_epub_info(tmp_file_path, original_file_name, original_file_extension)
        if ".FB2" == original_file_extension.upper() and use_fb2_meta is True:
            meta = fb2.get_fb2_info(tmp_file_path, original_file_extension)
        if original_file_extension.upper() in ['.CBZ', '.CBT']:
            meta = comic.get_comic_info(tmp_file_path, original_file_name, original_file_extension)

    except Exception as ex:
        logger.warning('cannot parse metadata, using default: %s', ex)

    if meta and meta.title.strip() and meta.author.strip():
        return meta
    else:
        return default_meta(tmp_file_path, original_file_name, original_file_extension)


def default_meta(tmp_file_path, original_file_name, original_file_extension):
    return uploader.BookMeta(
        file_path=tmp_file_path,
        extension=original_file_extension,
        title=original_file_name,
        author=u"Unknown",
        cover=None,
        description="",
        tags="",
        series="",
        series_id="",
        languages="")


def pdf_meta(tmp_file_path, original_file_name, original_file_extension):

    if use_pdf_meta:
        pdf = PdfFileReader(open(tmp_file_path, 'rb'), strict=False)
        doc_info = pdf.getDocumentInfo()
    else:
        doc_info = None

    if doc_info is not None:
        author = doc_info.author if doc_info.author else u"Unknown"
        title = doc_info.title if doc_info.title else original_file_name
        subject = doc_info.subject
    else:
        author = u"Unknown"
        title = original_file_name
        subject = ""
    return uploader.BookMeta(
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
    else:
        if use_PIL:
            try:
                input1 = PdfFileReader(open(tmp_file_path, 'rb'), strict=False)
                page0 = input1.getPage(0)
                xObject = page0['/Resources']['/XObject'].getObject()

                for obj in xObject:
                    if xObject[obj]['/Subtype'] == '/Image':
                        size = (xObject[obj]['/Width'], xObject[obj]['/Height'])
                        data = xObject[obj]._data # xObject[obj].getData()
                        if xObject[obj]['/ColorSpace'] == '/DeviceRGB':
                            mode = "RGB"
                        else:
                            mode = "P"
                        if '/Filter' in xObject[obj]:
                            if xObject[obj]['/Filter'] == '/FlateDecode':
                                img = Image.frombytes(mode, size, data)
                                cover_file_name = os.path.splitext(tmp_file_path)[0] + ".cover.png"
                                img.save(filename=os.path.join(tmp_dir, cover_file_name))
                                return cover_file_name
                                # img.save(obj[1:] + ".png")
                            elif xObject[obj]['/Filter'] == '/DCTDecode':
                                cover_file_name = os.path.splitext(tmp_file_path)[0] + ".cover.jpg"
                                img = open(cover_file_name, "wb")
                                img.write(data)
                                img.close()
                                return cover_file_name
                            elif xObject[obj]['/Filter'] == '/JPXDecode':
                                cover_file_name = os.path.splitext(tmp_file_path)[0] + ".cover.jp2"
                                img = open(cover_file_name, "wb")
                                img.write(data)
                                img.close()
                                return cover_file_name
                        else:
                            img = Image.frombytes(mode, size, data)
                            cover_file_name = os.path.splitext(tmp_file_path)[0] + ".cover.png"
                            img.save(filename=os.path.join(tmp_dir, cover_file_name))
                            return cover_file_name
            except Exception as ex:
                print(ex)
        try:
            cover_file_name = os.path.splitext(tmp_file_path)[0] + ".cover.jpg"
            with Image(filename=tmp_file_path + "[0]", resolution=150) as img:
                img.compression_quality = 88
                img.save(filename=os.path.join(tmp_dir, cover_file_name))
            return cover_file_name
        except PolicyError as ex:
            logger.warning('Pdf extraction forbidden by Imagemagick policy: %s', ex)
            return None
        except Exception as ex:
            logger.warning('Cannot extract cover image, using default: %s', ex)
            return None

def get_versions():
    if not use_generic_pdf_cover:
        IVersion = ImageVersion.MAGICK_VERSION
        WVersion = ImageVersion.VERSION
    else:
        IVersion = _(u'not installed')
        WVersion = _(u'not installed')
    if use_pdf_meta:
        PVersion='v'+PyPdfVersion
    else:
        PVersion=_(u'not installed')
    if lxmlversion:
        XVersion = 'v'+'.'.join(map(str, lxmlversion))
    else:
        XVersion = _(u'not installed')
    if use_PIL:
        PILVersion = 'v' + PILversion
    else:
        PILVersion = _(u'not installed')
    return {'Image Magick': IVersion,
            'PyPdf': PVersion,
            'lxml':XVersion,
            'Wand': WVersion,
            'Pillow': PILVersion}
