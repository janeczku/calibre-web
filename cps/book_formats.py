__author__ = 'lemmsh'

import logging
logger = logging.getLogger("book_formats")

import uploader
import os
try:
    from wand.image import Image
    use_generic_pdf_cover = False
except ImportError, e:
    logger.warning('cannot import Image, generating pdf covers for pdf uploads will not work')
    use_generic_pdf_cover = True
try:
    from PyPDF2 import PdfFileReader
    use_pdf_meta = True
except ImportError, e:
    logger.warning('cannot import PyPDF2, extracting pdf metadata will not work')
    use_pdf_meta = False

def process(tmp_file_path, original_file_name, original_file_extension):
    if (".PDF" == original_file_extension.upper()):
        return pdf_meta(tmp_file_path, original_file_name, original_file_extension)
    else: return None


def pdf_meta(tmp_file_path, original_file_name, original_file_extension):

    if (use_pdf_meta):
        pdf = PdfFileReader(open(tmp_file_path, 'rb'))
        doc_info = pdf.getDocumentInfo()
    else:
        doc_info = None

    if (doc_info is not None):
        author = doc_info.author
        title = doc_info.title
        subject = doc_info.subject
    else:
        author = "Unknown"
        title = original_file_name
        subject = ""
    return uploader.BookMeta(
        file_path = tmp_file_path,
        extension = original_file_extension,
        title = title,
        author = author,
        cover = pdf_preview(tmp_file_path, original_file_name),
        description = subject,
        tags = "",
        series = "",
        series_id="")

def pdf_preview(tmp_file_path, tmp_dir):
    if use_generic_pdf_cover:
        return None
    else:
        cover_file_name = os.path.splitext(tmp_file_path)[0] + ".cover.jpg"
        with Image(filename=tmp_file_path + "[0]", resolution=150) as img:
            img.compression_quality = 88
            img.save(filename=os.path.join(tmp_dir, cover_file_name))
        return cover_file_name
