#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from tempfile import gettempdir
import hashlib
from collections import namedtuple
import book_formats

BookMeta = namedtuple('BookMeta', 'file_path, extension, title, author, cover, description, tags, series, series_id, languages')

"""
 :rtype: BookMeta
"""


def upload(uploadfile):
    tmp_dir = os.path.join(gettempdir(), 'calibre_web')

    if not os.path.isdir(tmp_dir):
        os.mkdir(tmp_dir)

    filename = uploadfile.filename
    filename_root, file_extension = os.path.splitext(filename)
    md5 = hashlib.md5()
    md5.update(filename.encode('utf-8'))
    tmp_file_path = os.path.join(tmp_dir, md5.hexdigest())
    uploadfile.save(tmp_file_path)
    meta = book_formats.process(tmp_file_path, filename_root, file_extension)
    return meta
