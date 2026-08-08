# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2026 Martin Grzeslowski
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
import re
import struct

from . import cover, isoLanguages, logger
from .constants import BookMeta
from .string_helper import strip_whitespaces

log = logger.create()

PDB_HEADER_LEN = 78
PDB_RECORD_INFO_LEN = 8
PALMDOC_HEADER_LEN = 16
MOBI_HEADER_START = PALMDOC_HEADER_LEN
MOBI_FULL_NAME_OFFSET = 0x44
MOBI_FULL_NAME_LENGTH = 0x48
MOBI_FIRST_IMAGE_INDEX = 0x5C
UNKNOWN_INDEX = 0xFFFFFFFF

EXTH_AUTHOR = 100
EXTH_PUBLISHER = 101
EXTH_DESCRIPTION = 103
EXTH_ISBN = 104
EXTH_SUBJECT = 105
EXTH_PUBLISH_DATE = 106
EXTH_COVER_OFFSET = 201
EXTH_THUMBNAIL_OFFSET = 202
EXTH_TITLE = 503
EXTH_LANGUAGE = 524


def get_mobi_info(tmp_file_path, original_file_name, original_file_extension, no_cover_processing):
    data = _read_file(tmp_file_path)
    record_offsets = _read_record_offsets(data)
    record0 = _record(data, record_offsets, 0)
    _ensure_mobi_record(record0)

    encoding = _text_encoding(record0)
    exth_records = _read_exth_records(record0)

    title = _book_title(record0, encoding) or _first_text(exth_records, EXTH_TITLE, encoding) or original_file_name
    author = _author_string(_texts(exth_records, EXTH_AUTHOR, encoding))
    publisher = _first_text(exth_records, EXTH_PUBLISHER, encoding)
    description = _first_text(exth_records, EXTH_DESCRIPTION, encoding)
    tags = ', '.join(_unique(_texts(exth_records, EXTH_SUBJECT, encoding)))
    pubdate = _first_text(exth_records, EXTH_PUBLISH_DATE, encoding)[:10]
    languages = _language_code(_first_text(exth_records, EXTH_LANGUAGE, encoding))

    identifiers = []
    isbn = _first_text(exth_records, EXTH_ISBN, encoding)
    if isbn:
        identifiers.append(['isbn', isbn])

    cover_file = None
    if not no_cover_processing:
        cover_file = _extract_cover(data, record_offsets, record0, exth_records, tmp_file_path)

    return BookMeta(
        file_path=tmp_file_path,
        extension=original_file_extension,
        title=title,
        author=author or 'Unknown',
        cover=cover_file,
        description=description,
        tags=tags,
        series="",
        series_id="",
        languages=languages,
        publisher=publisher,
        pubdate=pubdate,
        identifiers=identifiers)


def _read_file(file_path):
    with open(file_path, 'rb') as mobi_file:
        return mobi_file.read()


def _u16(data, offset):
    return struct.unpack('>H', data[offset:offset + 2])[0]


def _u32(data, offset):
    return struct.unpack('>I', data[offset:offset + 4])[0]


def _read_record_offsets(data):
    if len(data) < PDB_HEADER_LEN:
        raise ValueError('MOBI file is shorter than the Palm database header')

    record_count = _u16(data, 76)
    table_end = PDB_HEADER_LEN + record_count * PDB_RECORD_INFO_LEN
    if record_count < 1 or table_end > len(data):
        raise ValueError('Invalid Palm database record table')

    offsets = [_u32(data, PDB_HEADER_LEN + index * PDB_RECORD_INFO_LEN) for index in range(record_count)]
    offsets.append(len(data))

    previous = table_end
    for offset in offsets[:-1]:
        if offset < previous or offset > len(data):
            raise ValueError('Invalid Palm database record offset')
        previous = offset
    return offsets


def _record(data, record_offsets, index):
    if index < 0 or index >= len(record_offsets) - 1:
        return b''
    return data[record_offsets[index]:record_offsets[index + 1]]


def _ensure_mobi_record(record0):
    if len(record0) < MOBI_HEADER_START + 8 or record0[MOBI_HEADER_START:MOBI_HEADER_START + 4] != b'MOBI':
        raise ValueError('File does not contain a MOBI header')


def _mobi_header_len(record0):
    return _u32(record0, MOBI_HEADER_START + 4)


def _text_encoding(record0):
    encoding = _u32(record0, MOBI_HEADER_START + 12)
    if encoding == 1252:
        return 'cp1252'
    if encoding == 65001:
        return 'utf-8'
    return 'utf-8'


def _read_exth_records(record0):
    header_len = _mobi_header_len(record0)
    exth_start = MOBI_HEADER_START + header_len

    if record0[exth_start:exth_start + 4] != b'EXTH':
        exth_start = record0.find(b'EXTH', MOBI_HEADER_START)
    if exth_start < 0:
        return {}

    exth_len = _u32(record0, exth_start + 4)
    record_count = _u32(record0, exth_start + 8)
    exth_end = min(len(record0), exth_start + exth_len)
    position = exth_start + 12
    records = {}

    for __ in range(record_count):
        if position + 8 > exth_end:
            break
        record_type = _u32(record0, position)
        record_len = _u32(record0, position + 4)
        if record_len < 8 or position + record_len > exth_end:
            break
        records.setdefault(record_type, []).append(record0[position + 8:position + record_len])
        position += record_len

    return records


def _decode_text(value, encoding):
    value = value.rstrip(b'\0')
    for candidate in (encoding, 'utf-8', 'cp1252', 'latin-1'):
        try:
            return strip_whitespaces(value.decode(candidate))
        except UnicodeDecodeError:
            pass
    return ''


def _texts(exth_records, record_type, encoding):
    return [text for text in (_decode_text(value, encoding) for value in exth_records.get(record_type, [])) if text]


def _first_text(exth_records, record_type, encoding):
    values = _texts(exth_records, record_type, encoding)
    return values[0] if values else ''


def _book_title(record0, encoding):
    header_len = _mobi_header_len(record0)
    if header_len < MOBI_FULL_NAME_LENGTH + 4:
        return ''

    name_offset = _u32(record0, MOBI_HEADER_START + MOBI_FULL_NAME_OFFSET)
    name_length = _u32(record0, MOBI_HEADER_START + MOBI_FULL_NAME_LENGTH)
    if name_length and name_offset + name_length <= len(record0):
        return _decode_text(record0[name_offset:name_offset + name_length], encoding)

    alternate_offset = MOBI_HEADER_START + name_offset
    if name_length and alternate_offset + name_length <= len(record0):
        return _decode_text(record0[alternate_offset:alternate_offset + name_length], encoding)
    return ''


def _author_string(authors):
    normalized = []
    for value in authors:
        normalized.extend(_split_author_value(value))

    return ' & '.join(_unique(normalized))


def _split_author_value(value):
    authors = []
    for part in re.split('[&;]', value):
        part = strip_whitespaces(part)
        if not part:
            continue

        if part.count(',') == 1:
            left, right = [strip_whitespaces(item) for item in part.split(',', 1)]
            if ' ' in left and ' ' in right:
                authors.extend([left, right])
            else:
                authors.append(strip_whitespaces('%s %s' % (right, left)))
        elif part.count(',') > 1:
            authors.extend([strip_whitespaces(item) for item in part.split(',') if strip_whitespaces(item)])
        else:
            authors.append(part)
    return authors


def _unique(values):
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _language_code(language):
    if not language:
        return ''
    language = language.split('-', 1)[0].lower()
    return isoLanguages.get_lang3(language)


def _first_image_index(record0):
    header_len = _mobi_header_len(record0)
    if header_len < MOBI_FIRST_IMAGE_INDEX + 4:
        return None
    index = _u32(record0, MOBI_HEADER_START + MOBI_FIRST_IMAGE_INDEX)
    return None if index == UNKNOWN_INDEX else index


def _exth_int(exth_records, record_type):
    values = exth_records.get(record_type, [])
    if not values or len(values[0]) < 4:
        return None
    return _u32(values[0], 0)


def _extract_cover(data, record_offsets, record0, exth_records, tmp_file_path):
    first_image_index = _first_image_index(record0)
    candidates = []
    if first_image_index is not None:
        for record_type in (EXTH_COVER_OFFSET, EXTH_THUMBNAIL_OFFSET):
            image_offset = _exth_int(exth_records, record_type)
            if image_offset is not None:
                candidates.append(first_image_index + image_offset)

    for index in candidates:
        cover_file = _cover_from_record(data, record_offsets, index, tmp_file_path)
        if cover_file:
            return cover_file

    return _largest_image_cover(data, record_offsets, first_image_index, tmp_file_path)


def _cover_from_record(data, record_offsets, index, tmp_file_path):
    blob = _record(data, record_offsets, index)
    extension = _image_extension(blob)
    if not extension:
        return None
    try:
        return cover.cover_processing(tmp_file_path, blob, extension)
    except Exception as ex:
        log.warning('Cannot extract MOBI cover image, using default: %s', ex)
        return None


def _largest_image_cover(data, record_offsets, first_image_index, tmp_file_path):
    start = first_image_index if first_image_index is not None else 1
    images = []
    for index in range(start, len(record_offsets) - 1):
        blob = _record(data, record_offsets, index)
        extension = _image_extension(blob)
        if extension:
            images.append((len(blob), index))

    for __, index in sorted(images, reverse=True):
        cover_file = _cover_from_record(data, record_offsets, index, tmp_file_path)
        if cover_file:
            return cover_file
    return None


def _image_extension(blob):
    if blob.startswith(b'\xff\xd8\xff'):
        return '.jpg'
    if blob.startswith(b'\x89PNG\r\n\x1a\n'):
        return '.png'
    if blob.startswith(b'RIFF') and blob[8:12] == b'WEBP':
        return '.webp'
    if blob.startswith(b'BM'):
        return '.bmp'
    return None
