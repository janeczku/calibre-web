from eyed3.core import Date
from eyed3.id3 import Tag

from cps.constants import BookMeta
import eyed3


def get_mp3_file_info(
    tmp_file_path: str, original_file_extension: str, original_file_name: str
) -> BookMeta:
    mp3 = eyed3.load(tmp_file_path)
    mp3_tags: Tag = mp3.tag if mp3 is not None else Tag()
    release_date = mp3_tags.release_date
    pubdate = "-".join([
        release_date.year, release_date.month, release_date.day
    ]) if isinstance(release_date, Date) else ""

    return BookMeta(
        file_path=tmp_file_path,
        extension=original_file_extension,
        title=mp3_tags.title or original_file_name,
        author=mp3_tags.artist or mp3_tags.album_artist or "Unknown",
        cover=None,
        description="",
        tags="",
        series=mp3_tags.album or "",
        series_id="",
        languages="",
        publisher=mp3_tags.publisher or "",
        pubdate=pubdate,
        identifiers=[],
    )
