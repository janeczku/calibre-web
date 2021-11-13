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

import os
import hashlib
from tempfile import gettempdir
from flask_babel import gettext as _

from . import logger, comic, isoLanguages
from .constants import BookMeta
from .helper import split_authors

log = logger.create()


try:
    from lxml.etree import LXML_VERSION as lxmlversion
except ImportError:
    lxmlversion = None

try:
    from wand.image import Image, Color
    from wand import version as ImageVersion
    from wand.exceptions import PolicyError
    use_generic_pdf_cover = False
except (ImportError, RuntimeError) as e:
    log.debug('Cannot import Image, generating pdf covers for pdf uploads will not work: %s', e)
    use_generic_pdf_cover = True

try:
    from PyPDF3 import PdfFileReader
    from PyPDF3 import __version__ as PyPdfVersion
    use_pdf_meta = True
except ImportError as ex:
    try:
        from PyPDF2 import PdfFileReader
        from PyPDF2 import __version__ as PyPdfVersion
        use_pdf_meta = True
    except ImportError as e:
        log.debug('Cannot import PyPDF3/PyPDF2, extracting pdf metadata will not work: %s / %s', ex, e)
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
        cover=None, #pdf_preview(tmp_file_path, original_file_name),
        description="",
        tags="",
        series="",
        series_id="",
        languages="",
        publisher="")


def parse_xmp(pdf_file):
    """
    Parse XMP Metadata and prepare for BookMeta object
    """
    try:
        xmp_info = pdf_file.getXmpMetadata()
    except Exception as ex:
        log.debug('Can not read XMP metadata {}'.format(ex))
        return None

    if xmp_info:
        try:
            xmp_author = xmp_info.dc_creator # list
        except AttributeError:
            xmp_author = ['']

        if xmp_info.dc_title:
            xmp_title = xmp_info.dc_title['x-default']
        else:
            xmp_title = ''

        if xmp_info.dc_description:
            xmp_description = xmp_info.dc_description['x-default']
        else:
            xmp_description = ''

        languages = []
        try:
            for i in xmp_info.dc_language:
                #calibre-web currently only takes one language.
                languages.append(isoLanguages.get_lang3(i))
        except AttributeError:
            languages.append('')

        xmp_tags = ', '.join(xmp_info.dc_subject)
        xmp_publisher = ', '.join(xmp_info.dc_publisher)

        return {'author': xmp_author,
                    'title': xmp_title,
                    'subject': xmp_description,
                    'tags': xmp_tags, 'languages': languages,
                    'publisher': xmp_publisher
                    }


def parse_xmp(pdf_file):
    """
    Parse XMP Metadata and prepare for BookMeta object
    """
    try:
        xmp_info = pdf_file.getXmpMetadata()
    except Exception as ex:
        log.debug('Can not read XMP metadata {}'.format(ex))
        return None

    if xmp_info:
        try:
            xmp_author = xmp_info.dc_creator # list
        except AttributeError:
            xmp_author = ['Unknown']

        if xmp_info.dc_title:
            xmp_title = xmp_info.dc_title['x-default']
        else:
            xmp_title = ''

        if xmp_info.dc_description:
            xmp_description = xmp_info.dc_description['x-default']
        else:
            xmp_description = ''

        languages = []
        try:
            for i in xmp_info.dc_language:
                languages.append(isoLanguages.get_lang3(i))
        except AttributeError:
            languages.append('')

        xmp_tags = ', '.join(xmp_info.dc_subject)
        xmp_publisher = ', '.join(xmp_info.dc_publisher)

        return {'author': xmp_author,
                'title': xmp_title,
                'subject': xmp_description,
                'tags': xmp_tags,
                'languages': languages,
                'publisher': xmp_publisher
                }


def pdf_meta(tmp_file_path, original_file_name, original_file_extension):
    doc_info = None
    xmp_info = None

    if use_pdf_meta:
        with open(tmp_file_path, 'rb') as f:
            pdf_file = PdfFileReader(f)
            doc_info = pdf_file.getDocumentInfo()
            xmp_info = parse_xmp(pdf_file)

    if xmp_info:
        author = ' & '.join(split_authors(xmp_info['author']))
        title = xmp_info['title']
        subject = xmp_info['subject']
        tags = xmp_info['tags']
        languages = xmp_info['languages']
        publisher = xmp_info['publisher']
    else:
        author = u'Unknown'
        title = ''
        languages = [""]
        publisher = ""
        subject = ""
        tags = ""

    if doc_info:
        if author == '':
            author = ' & '.join(split_authors([doc_info.author])) if doc_info.author else u'Unknown'
        if title == '':
            title = doc_info.title if doc_info.title else original_file_name
        if subject == '':
            subject = doc_info.subject
        if tags == '' and '/Keywords' in doc_info:
            tags = doc_info['/Keywords']
    else:
        title = original_file_name

    return BookMeta(
        file_path=tmp_file_path,
        extension=original_file_extension,
        title=title,
        author=author,
        cover=pdf_preview(tmp_file_path, original_file_name),
        description=subject,
        tags=tags,
        series="",
        series_id="",
        languages=','.join(languages),
        publisher=publisher)


def pdf_preview(tmp_file_path, tmp_dir):
    if use_generic_pdf_cover:
        return None
    try:
        cover_file_name = os.path.splitext(tmp_file_path)[0] + ".cover.jpg"
        with Image() as img:
            img.options["pdf:use-cropbox"] = "true"
            img.read(filename=tmp_file_path + '[0]', resolution=150)
            img.compression_quality = 88
            if img.alpha_channel:
                img.alpha_channel = 'remove'
                img.background_color = Color('white')
            img.save(filename=os.path.join(tmp_dir, cover_file_name))
        return cover_file_name
    except PolicyError as ex:
        log.warning('Pdf extraction forbidden by Imagemagick policy: %s', ex)
        return None
    except Exception as ex:
        log.warning('Cannot extract cover image, using default: %s', ex)
        log.warning('On Windows this error could be caused by missing ghostscript')
        return None


def get_versions(all=True):
    ret = dict()
    if not use_generic_pdf_cover:
        ret['Image Magick'] = ImageVersion.MAGICK_VERSION
    else:
        ret['Image Magick'] = u'not installed'
    if all:
        if not use_generic_pdf_cover:
            ret['Wand'] = ImageVersion.VERSION
        else:
            ret['Wand'] = u'not installed'
        if use_pdf_meta:
            ret['PyPdf'] = PyPdfVersion
        else:
            ret['PyPdf'] = u'not installed'
        if lxmlversion:
            ret['lxml'] = '.'.join(map(str, lxmlversion))
        else:
            ret['lxml'] = u'not installed'
        if comic.use_comic_meta:
            ret['Comic_API'] = comic.comic_version or u'installed'
        else:
            ret['Comic_API'] = u'not installed'
    return ret


def upload(uploadfile, rarExcecutable):
    tmp_dir = os.path.join(gettempdir(), 'calibre_web')

    if not os.path.isdir(tmp_dir):
        os.mkdir(tmp_dir)

    filename = uploadfile.filename
    filename_root, file_extension = os.path.splitext(filename)
    md5 = hashlib.md5(filename.encode('utf-8')).hexdigest()  # nosec
    tmp_file_path = os.path.join(tmp_dir, md5)
    log.debug("Temporary file: %s", tmp_file_path)
    uploadfile.save(tmp_file_path)
    return process(tmp_file_path, filename_root, file_extension, rarExcecutable)
