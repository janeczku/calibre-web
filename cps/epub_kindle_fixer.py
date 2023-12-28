import logging
import os
import tempfile
from zipfile import ZipFile
from xml.etree import ElementTree as ET


def update_file(file,z:ZipFile):
    """removes tags that are forbidden by amazon"""
    if file.filename.endswith(".html"):
        with z.open(file) as f:
            for l in (lines := f.readlines()):
                if "amzn" in l.decode("utf-8").lower():
                    tree = ET.fromstringlist(lines)
                    for x in tree.iter():
                        if x.get("data-AmznRemoved"):
                            del x.attrib["data-AmznRemoved"]
                        if x.get("data-AmznRemoved-M8"):
                            del x.attrib["data-AmznRemoved-M8"]

                    return ET.tostring(tree)
    return z.read(file)

def fix_epub(filepath):
    if not os.path.isfile(filepath):
        print(f"invalid filepath: {filepath}")
        return
    # generate a temp file
    tmpfd, tmpname = tempfile.mkstemp(dir=os.path.dirname(filepath))
    os.close(tmpfd)

    # create a temp copy of the archive without filename
    with ZipFile(filepath, 'r') as zin:
        with ZipFile(tmpname, 'w') as zout:
            zout.comment = zin.comment  # preserve the comment
            for item in zin.infolist():
                zout.writestr(item, update_file(item,zin))

    # replace with the temp archive
    os.remove(filepath)
    os.rename(tmpname, filepath)

