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

# import json
import datetime
import os
import hashlib
import subprocess
# import shlex
import shutil
import sqlite3
from flask_babel import gettext as _

from . import logger, comic, isoLanguages
from .constants import BookMeta, XKLB_DB_FILE
from .helper import split_authors
from .file_helper import get_temp_dir, validate_mime_type

log = logger.create()

try:
    from wand.image import Image, Color
    from wand import version as ImageVersion
    from wand.exceptions import PolicyError
    use_generic_pdf_cover = False
except (ImportError, RuntimeError) as e:
    log.debug('Cannot import Image, generating pdf covers for pdf uploads will not work: %s', e)
    use_generic_pdf_cover = True

try:
    from pypdf import PdfReader
    use_pdf_meta = True
except ImportError as ex:
    log.debug('PyPDF is recommended for best performance in metadata extracting from pdf files: %s', ex)
    try:
        from PyPDF2 import PdfReader
        use_pdf_meta = True
    except ImportError as ex:
        log.debug('PyPDF is recommended for best performance in metadata extracting from pdf files: %s', ex)
        log.debug('PyPdf2 is also possible for metadata extracting from pdf files, but not recommended anymore')
        try:
            from PyPDF3 import PdfFileReader as PdfReader
            use_pdf_meta = True
        except ImportError as e:
            log.debug('Cannot import PyPDF3/PyPDF2, extracting pdf metadata will not work: %s / %s', e)
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


def process(tmp_file_path, original_file_name, original_file_extension, rar_executable):
    meta = default_meta(tmp_file_path, original_file_name, original_file_extension)
    extension_upper = original_file_extension.upper()
    try:
        if ".PDF" == extension_upper:
            meta = pdf_meta(tmp_file_path, original_file_name, original_file_extension)
        elif extension_upper in [".KEPUB", ".EPUB"] and use_epub_meta is True:
            meta = epub.get_epub_info(tmp_file_path, original_file_name, original_file_extension)
        elif ".FB2" == extension_upper and use_fb2_meta is True:
            meta = fb2.get_fb2_info(tmp_file_path, original_file_extension)
        elif extension_upper in ['.CBZ', '.CBT', '.CBR', ".CB7"]:
            meta = comic.get_comic_info(tmp_file_path,
                                        original_file_name,
                                        original_file_extension,
                                        rar_executable)
        elif extension_upper in ['.MP4', '.WEBM', '.MKV']:
            meta = video_metadata(tmp_file_path, original_file_name, original_file_extension)
        elif extension_upper in ['.JPG', '.JPEG', '.PNG', '.GIF', '.SVG', '.WEBP']:
            shutil.copyfile(tmp_file_path, os.path.splitext(tmp_file_path)[0] + '.cover.jpg')
            meta = image_metadata(tmp_file_path, original_file_name, original_file_extension)

    except Exception as ex:
        log.warning('cannot parse metadata, using default: %s', ex)

    if not meta.title.strip():
        meta = meta._replace(title=original_file_name)
    if not meta.author.strip() or meta.author.lower() == 'unknown':
        meta = meta._replace(author=_('Unknown'))
    return meta


def default_meta(tmp_file_path, original_file_name, original_file_extension):
    return BookMeta(
        file_path=tmp_file_path,
        extension=original_file_extension,
        title=original_file_name,
        author=_('Unknown'),
        cover=None,
        description="",
        tags="",
        series="",
        series_id="",
        languages="",
        publisher="",
        pubdate="",
        identifiers=[]
        )


def parse_xmp(pdf_file):
    """
    Parse XMP Metadata and prepare for BookMeta object
    """
    try:
        xmp_info = pdf_file.xmp_metadata
    except Exception as ex:
        log.debug('Can not read PDF XMP metadata {}'.format(ex))
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
            pdf_file = PdfReader(f)
            try:
                doc_info = pdf_file.metadata
            except Exception as exc:
                log.debug('Can not read PDF DocumentInfo {}'.format(exc))
            xmp_info = parse_xmp(pdf_file)

    if xmp_info:
        author = ' & '.join(split_authors(xmp_info['author']))
        title = xmp_info['title']
        subject = xmp_info['subject']
        tags = xmp_info['tags']
        languages = xmp_info['languages']
        publisher = xmp_info['publisher']
    else:
        author = 'Unknown'
        title = ''
        languages = [""]
        publisher = ""
        subject = ""
        tags = ""

    if doc_info:
        if author == '':
            author = ' & '.join(split_authors([doc_info.author])) if doc_info.author else 'Unknown'
        if title == '':
            title = doc_info.title if doc_info.title else original_file_name
        if subject == '':
            subject = doc_info.subject or ""
        if tags == '' and '/Keywords' in doc_info:
            if isinstance(doc_info['/Keywords'], bytes):
                tags = doc_info['/Keywords'].decode('utf-8')
            else:
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
        publisher=publisher,
        pubdate="",
        identifiers=[])


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


def video_metadata(tmp_file_path, original_file_name, original_file_extension):
    if '[' in original_file_name and ']' in original_file_name:
        video_id = original_file_name.split('[')[1].split(']')[0]
        video_url = None
        if os.path.isfile(XKLB_DB_FILE):
            with sqlite3.connect(XKLB_DB_FILE) as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                # 2024-02-17: Dedup Design Evolving... https://github.com/iiab/calibre-web/pull/125
                c.execute("SELECT * FROM media WHERE extractor_id=? AND path LIKE ?", (video_id, f'%{original_file_name}%'))
                row = c.fetchone()
                if row is not None:
                    video_url = row['webpath']
                    title = row['title']
                    author = row['path'].split('/calibre-web/')[1].split('/')[1].replace('_', ' ')
                    publisher = row['path'].split('/calibre-web/')[1].split('/')[0].replace('_', ' ')
                    # example of time_uploaded: 1696464000
                    pubdate = row['time_uploaded']
                    pubdate = datetime.datetime.fromtimestamp(pubdate).strftime('%Y-%m-%d %H:%M:%S')
                    # find cover file
                    if os.path.isdir(os.path.dirname(row['path'])):
                        for file in os.listdir(os.path.dirname(row['path'])):
                            # 2024-05-30: YouTube (via yt_dlp and xklb) delivers WebP thumbnails by default, and occasionally also JPG thumbnails.
                            # Vimeo seems to deliver JPG thumbnails every time.
                            # FYI yt_dlp uses YouTube and Vimeo "extractors" -- among ~1810 websites it can scrape:
                            # https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md
                            # https://github.com/yt-dlp/yt-dlp/tree/master/yt_dlp/extractor
                            if file.lower().endswith(('.webp', '.jpg', '.png', '.gif')) and os.path.splitext(file)[0] == os.path.splitext(os.path.basename(row['path']))[0]:
                                cover_file_path = os.path.join(os.path.dirname(row['path']), file)
                                break
                    else:
                        log.warning('Cannot find thumbnail file, using default cover')
                        cover_file_path = os.path.splitext(tmp_file_path)[0] + '.cover.jpg'
                    c.execute("SELECT * FROM captions WHERE media_id=?", (row['id'],))
                    row = c.fetchone()
                    description = f"{row['text']}<br><br>Original Internet URL: <a href='{video_url}' target='_blank'>{video_url}</a>" if row is not None else ''
                    meta = BookMeta(
                        file_path=tmp_file_path,
                        extension=original_file_extension,
                        title=title,
                        author=author,
                        cover=cover_file_path,
                        description=description,
                        tags='',
                        series="",
                        series_id="",
                        languages="",
                        publisher=publisher,
                        pubdate=pubdate,
                        identifiers=[])
                    return meta
                else:
                    generate_video_cover(tmp_file_path)
                    return image_metadata(tmp_file_path, original_file_name, original_file_extension)
        else:
            log.warning('Cannot find the xklb database, using default metadata')
    else:
        generate_video_cover(tmp_file_path)
        return image_metadata(tmp_file_path, original_file_name, original_file_extension)

# Yes shlex.quote() can help! But flags/options/switchs can still be dangerous:
# https://stackoverflow.com/questions/49573852/is-python3-shlex-quote-safe
# def sanitize_path(path):
#     """Sanitize the file path to prevent command injection."""
#     return shlex.quote(path)

def generate_video_cover(tmp_file_path):
    ffmpeg_executable = os.getenv('FFMPEG_PATH', 'ffmpeg')
    ffmpeg_output_file = os.path.splitext(tmp_file_path)[0] + '.cover.jpg'

    ffmpeg_args = [
        ffmpeg_executable,
        '-i', tmp_file_path,
        '-vf', 'fps=1,thumbnail,scale=-1:720',  # apply filters to avoid black frames and scale
        '-frames:v', '1',  # extract only one frame
        '-vsync', 'vfr',  # variable frame rate
        '-y',  # overwrite output file if it exists
        ffmpeg_output_file
    ]

    try:
        ffmpeg_result = subprocess.run(ffmpeg_args, capture_output=True, check=True)
        log.debug(f"ffmpeg output: {ffmpeg_result.stdout}")

    except Exception as e:
        log.error(f"ffmpeg failed: {e}")
        return None

def image_metadata(tmp_file_path, original_file_name, original_file_extension):
    meta = BookMeta(
        file_path=tmp_file_path,
        extension=original_file_extension,
        title=original_file_name,
        author='Unknown',
        cover=os.path.splitext(tmp_file_path)[0] + '.cover.jpg',
        description='',
        tags='',
        series="",
        series_id="",
        languages="",
        publisher="",
        pubdate="",
        identifiers=[])
    return meta


def get_magick_version():
    ret = dict()
    if not use_generic_pdf_cover:
        ret['Image Magick'] = ImageVersion.MAGICK_VERSION
    else:
        ret['Image Magick'] = 'not installed'
    return ret


def upload(uploadfile, rar_excecutable):
    tmp_dir = get_temp_dir()

    filename = uploadfile.filename
    filename_root, file_extension = os.path.splitext(filename)
    md5 = hashlib.md5(filename.encode('utf-8')).hexdigest()  # nosec
    tmp_file_path = os.path.join(tmp_dir, md5)
    log.debug("Temporary file: %s", tmp_file_path)
    uploadfile.save(tmp_file_path)
    return process(tmp_file_path, filename_root, file_extension, rar_excecutable)
