__author__ = 'lemmsh'

import logging
logger = logging.getLogger("book_formats")

import uploader
import os
try:
    from wand.image import Image
    use_generic_pdf_cover = False
except ImportError, e:
    logger.warning('cannot import Image, generating pdf covers for pdf uploads will not work: %s', e)
    use_generic_pdf_cover = True
try:
    from PyPDF2 import PdfFileReader
    use_pdf_meta = True
except ImportError, e:
    logger.warning('cannot import PyPDF2, extracting pdf metadata will not work: %s', e)
    use_pdf_meta = False

try:
    import epub
    use_epub_meta = True
except ImportError, e:
    logger.warning('cannot import epub, extracting epub metadata will not work: %s', e)
    use_epub_meta = False

try:
    import fb2
    use_fb2_meta = True
except ImportError, e:
    logger.warning('cannot import fb2, extracting fb2 metadata will not work: %s', e)
    use_fb2_meta = False


def process(tmp_file_path, original_file_name, original_file_extension):
    try:
        if ".PDF" == original_file_extension.upper():
            return pdf_meta(tmp_file_path, original_file_name, original_file_extension)
        if ".EPUB" == original_file_extension.upper() and use_epub_meta == True:
            return epub.get_epub_info(tmp_file_path, original_file_name, original_file_extension)
        if ".FB2" == original_file_extension.upper() and use_fb2_meta == True:
            return fb2.get_fb2_info(tmp_file_path, original_file_name, original_file_extension)
    except Exception, e:
        logger.warning('cannot parse metadata, using default: %s', e)

    return default_meta(tmp_file_path, original_file_name, original_file_extension)



def default_meta(tmp_file_path, original_file_name, original_file_extension):
    return uploader.BookMeta(
        file_path = tmp_file_path,
        extension = original_file_extension,
        title = original_file_name,
        author = "Unknown",
        cover = None,
        description = "",
        tags = "",
        series = "",
        series_id="")


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
