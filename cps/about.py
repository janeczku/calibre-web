# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2018-2019 OzzieIsaacs, cervinko, jkrehm, bodybybuddha, ok11,
#                            andy29485, idalin, Kyosfonica, wuqi, Kennyl, lemmsh,
#                            falgh1, grunjol, csitko, ytils, xybydy, trasba, vrabe,
#                            ruben-herold, marblepebble, JackED42, SiphonSquirrel,
#                            apetresc, nanu-c, mutschler
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

import sys
import platform
import sqlite3
from importlib.metadata import metadata
from collections import OrderedDict

import flask
from flask_babel import gettext as _

from . import db, calibre_db, converter, uploader, constants, dep_check
from .render_template import render_title_template
from .usermanagement import user_login_required


about = flask.Blueprint('about', __name__)

modules = dict()
req = dep_check.load_dependencies(False)
opt = dep_check.load_dependencies(True)
for i in (req + opt):
    modules[i[1]] = i[0]
modules['Jinja2'] = metadata("jinja2")["Version"]
if sys.version_info < (3, 12):
    modules['pySqlite'] = sqlite3.version
modules['SQLite'] = sqlite3.sqlite_version
sorted_modules = OrderedDict((sorted(modules.items(), key=lambda x: x[0].casefold())))


def collect_stats():
    if constants.NIGHTLY_VERSION[0] == "$Format:%H$":
        calibre_web_version = constants.STABLE_VERSION.replace("b", " Beta")
    else:
        calibre_web_version = (constants.STABLE_VERSION.replace("b", " Beta") + ' - '
                               + constants.NIGHTLY_VERSION[0].replace('%', '%%') + ' - '
                               + constants.NIGHTLY_VERSION[1].replace('%', '%%'))

    if getattr(sys, 'frozen', False):
        calibre_web_version += " - Exe-Version"
    elif constants.HOME_CONFIG:
        calibre_web_version += " - pyPi"

    _VERSIONS = {'Calibre Web': calibre_web_version}
    _VERSIONS.update(OrderedDict(
        Python=sys.version,
        Platform='{0[0]} {0[2]} {0[3]} {0[4]} {0[5]}'.format(platform.uname()),
    ))
    _VERSIONS.update(uploader.get_magick_version())
    _VERSIONS['Unrar'] = converter.get_unrar_version()
    _VERSIONS['Ebook converter'] = converter.get_calibre_version()
    _VERSIONS['Kepubify'] = converter.get_kepubify_version()
    _VERSIONS.update(sorted_modules)
    return _VERSIONS


@about.route("/stats")
@user_login_required
def stats():
    from . import ub, config
    from flask_login import current_user
    import os
    import glob as file_glob

    # Basic library stats
    counter = calibre_db.session.query(db.Books).count()
    authors = calibre_db.session.query(db.Authors).count()
    categories = calibre_db.session.query(db.Tags).count()
    series = calibre_db.session.query(db.Series).count()
    publishers = calibre_db.session.query(db.Publishers).count()
    languages = calibre_db.session.query(db.Languages).count()

    # User-specific stats
    user_id = current_user.id if not current_user.is_anonymous else None
    user_stats = {}

    if user_id:
        # Books read
        read_books = ub.session.query(ub.ReadBook).filter(
            ub.ReadBook.user_id == user_id,
            ub.ReadBook.read_status == ub.ReadBook.STATUS_FINISHED
        ).count()

        # Books in progress
        in_progress_books = ub.session.query(ub.ReadBook).filter(
            ub.ReadBook.user_id == user_id,
            ub.ReadBook.read_status == ub.ReadBook.STATUS_IN_PROGRESS
        ).count()

        # Books downloaded
        downloaded_books = ub.session.query(ub.Downloads).filter(
            ub.Downloads.user_id == user_id
        ).count()

        # Reading statistics from Kobo
        total_reading_time = ub.session.query(
            ub.func.sum(ub.KoboStatistics.spent_reading_minutes)
        ).join(ub.KoboReadingState).filter(
            ub.KoboReadingState.user_id == user_id
        ).scalar() or 0

        # Series read (count distinct series where user has read at least one book)
        series_read = ub.session.query(ub.func.count(ub.func.distinct(db.books_series_link.c.series)))\
            .select_from(ub.ReadBook)\
            .join(db.Books, ub.ReadBook.book_id == db.Books.id)\
            .join(db.books_series_link, db.Books.id == db.books_series_link.c.book)\
            .filter(
                ub.ReadBook.user_id == user_id,
                ub.ReadBook.read_status == ub.ReadBook.STATUS_FINISHED
            ).scalar() or 0

        user_stats = {
            'read_books': read_books,
            'in_progress_books': in_progress_books,
            'downloaded_books': downloaded_books,
            'reading_time_hours': total_reading_time // 60,
            'reading_time_minutes': total_reading_time % 60,
            'series_read': series_read
        }

    # Audiobook stats
    audiobook_count = 0
    total_audiobook_size = 0
    total_audiobook_duration = 0

    try:
        books = calibre_db.session.query(db.Books).all()
        for book in books:
            if book.path:
                book_dir = os.path.join(config.get_book_path(), book.path)
                if os.path.exists(book_dir):
                    audiobook_files = file_glob.glob(os.path.join(book_dir, "*_part*.mp3"))
                    if audiobook_files:
                        audiobook_count += 1
                        for audio_file in audiobook_files:
                            total_audiobook_size += os.path.getsize(audio_file)
                            # Get duration
                            try:
                                import mutagen
                                audio = mutagen.File(audio_file)
                                if audio and hasattr(audio.info, 'length'):
                                    total_audiobook_duration += int(audio.info.length)
                            except:
                                pass
    except Exception as e:
        pass

    audiobook_stats = {
        'count': audiobook_count,
        'total_size_mb': total_audiobook_size // (1024 * 1024),
        'total_duration_hours': total_audiobook_duration // 3600,
        'total_duration_minutes': (total_audiobook_duration % 3600) // 60
    }

    # Global activity stats (all users)
    global_downloads = ub.session.query(ub.Downloads).count()
    global_reads = ub.session.query(ub.ReadBook).filter(
        ub.ReadBook.read_status == ub.ReadBook.STATUS_FINISHED
    ).count()

    return render_title_template('stats.html',
                                bookcounter=counter,
                                authorcounter=authors,
                                versions=collect_stats(),
                                categorycounter=categories,
                                seriecounter=series,
                                publishercounter=publishers,
                                languagecounter=languages,
                                user_stats=user_stats,
                                audiobook_stats=audiobook_stats,
                                global_downloads=global_downloads,
                                global_reads=global_reads,
                                title=_("Statistics"),
                                page="stat")
