#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import uploader
import os
from flask_babel import gettext as _
import comic

__author__ = 'lemmsh'

logger = logging.getLogger("book_formats")

try:
    from wand.image import Image
    from wand import version as ImageVersion
    use_generic_pdf_cover = False
except ImportError as e:
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
        pdf = PdfFileReader(open(tmp_file_path, 'rb'))
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
        cover_file_name = os.path.splitext(tmp_file_path)[0] + ".cover.jpg"
        with Image(filename=tmp_file_path + "[0]", resolution=150) as img:
            img.compression_quality = 88
            img.save(filename=os.path.join(tmp_dir, cover_file_name))
        return cover_file_name


def get_versions():
    if not use_generic_pdf_cover:
        IVersion=ImageVersion.MAGICK_VERSION
    else:
        IVersion=_(u'not installed')
    if use_pdf_meta:
        PVersion=PyPdfVersion
    else:
        PVersion=_(u'not installed')
    return {'ImageVersion': IVersion, 'PyPdfVersion': PVersion}
