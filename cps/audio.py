# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2024 Ozzieisaacs
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

import mutagen
import base64

from cps.constants import BookMeta


def get_audio_file_info(tmp_file_path, original_file_extension, original_file_name):
    tmp_cover_name = None
    audio_file = mutagen.File(tmp_file_path)
    if original_file_extension in [".mp3", ".wav"]:
        title = audio_file.tags.get('TIT2').text[0] if "TIT2" in audio_file.tags else None
        author = audio_file.tags.get('TPE1').text[0] if "TPE1" in audio_file.tags else None
        if author is None:
            author = audio_file.tags.get('TPE2').text[0] if "TPE2" in audio_file.tags else None
        comments = audio_file.tags.get('COMM').text[0] if "COMM" in audio_file.tags else None
        tags = audio_file.tags.get('TCON').text[0] if "TCON" in audio_file.tags else None # Genre
        series = audio_file.tags.get('TALB').text[0] if "TALB" in audio_file.tags else None# Album
        series_id = audio_file.tags.get('TRCK').text[0] if "TRCK" in audio_file.tags else None # track no.
        publisher = audio_file.tags.get('TPUB').text[0] if "TPUB" in audio_file.tags else None
        pubdate = audio_file.tags.get('XDOR').text[0] if "XDOR" in audio_file.tags else None
        cover_data = audio_file.tags.get('APIC:')
        if cover_data:
            tmp_cover_name = os.path.join(os.path.dirname(tmp_file_path), 'cover.jpg')
            with open(tmp_cover_name, "wb") as cover_file:
                cover_file.write(cover_data.data)
    elif original_file_extension in [".ogg", ".flac"]:
        title = audio_file.tags.get('TITLE')[0] if "TITLE" in audio_file else None
        author = audio_file.tags.get('ARTIST')[0] if "ARTIST" in audio_file else None
        comments = None # audio_file.tags.get('COMM', None)
        tags = ""
        series = audio_file.tags.get('ALBUM')[0] if "ALBUM" in audio_file else None
        series_id = audio_file.tags.get('TRACKNUMBER')[0] if "TRACKNUMBER" in audio_file else None
        publisher = audio_file.tags.get('LABEL')[0] if "LABEL" in audio_file else None
        pubdate = audio_file.tags.get('DATE')[0] if "DATE" in audio_file else None
        cover_data = audio_file.tags.get('METADATA_BLOCK_PICTURE')
        if cover_data:
            tmp_cover_name = os.path.join(os.path.dirname(tmp_file_path), 'cover.jpg')
            with open(tmp_cover_name, "wb") as cover_file:
                cover_file.write(mutagen.flac.Picture(base64.b64decode(cover_data[0])).data)
        if hasattr(audio_file, "pictures"):
            tmp_cover_name = os.path.join(os.path.dirname(tmp_file_path), 'cover.jpg')
            with open(tmp_cover_name, "wb") as cover_file:
                cover_file.write(audio_file.pictures[0].data)

    return BookMeta(
        file_path=tmp_file_path,
        extension=original_file_extension,
        title=title or original_file_name ,
        author="Unknown" if author is None else author,
        cover=tmp_cover_name,
        description="" if comments is None else comments,
        tags="" if tags is None else tags,
        series="" if series is None else series,
        series_id="1" if series_id is None else series_id.split("/")[0],
        languages="",
        publisher= "" if publisher is None else publisher,
        pubdate="" if pubdate is None else pubdate,
        identifiers=[],
    )
