import os
import hashlib
from collections import namedtuple
import book_formats


tmp_dir = "/tmp/calibre-web"

BookMeta = namedtuple('BookMeta', 'file_path, extension, title, author, cover, description, tags, series, series_id')


"""
 :rtype: BookMeta
"""
def upload(file):
    if not os.path.isdir(tmp_dir):
        os.mkdir(tmp_dir)

    filename = file.filename
    filename_root, file_extension = os.path.splitext(filename)
    md5 = hashlib.md5()
    md5.update(filename)
    tmp_file_path = os.path.join(tmp_dir, md5.hexdigest())
    file.save(tmp_file_path)
    meta = book_formats.process(tmp_file_path, filename_root, file_extension)
    return meta




