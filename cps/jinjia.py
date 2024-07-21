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

# custom jinja filters

from markupsafe import escape
import datetime
import mimetypes
from uuid import uuid4

from flask import Blueprint, request, url_for
from flask_babel import format_date
from .cw_login import current_user

from . import constants, logger

jinjia = Blueprint('jinjia', __name__)
log = logger.create()


# pagination links in jinja
@jinjia.app_template_filter('url_for_other_page')
def url_for_other_page(page):
    args = request.view_args.copy()
    args['page'] = page
    for get, val in request.args.items():
        args[get] = val
    return url_for(request.endpoint, **args)


# shortentitles to at longest nchar, shorten longer words if necessary
@jinjia.app_template_filter('shortentitle')
def shortentitle_filter(s, nchar=20):
    text = s.split()
    res = ""  # result
    suml = 0  # overall length
    for line in text:
        if suml >= 60:
            res += '...'
            break
        # if word longer than 20 chars truncate line and append '...', otherwise add whole word to result
        # string, and summarize total length to stop at chars given by nchar
        if len(line) > nchar:
            res += line[:(nchar-3)] + '[..] '
            suml += nchar+3
        else:
            res += line + ' '
            suml += len(line) + 1
    return res.strip()


@jinjia.app_template_filter('mimetype')
def mimetype_filter(val):
    return mimetypes.types_map.get('.' + val, 'application/octet-stream')


@jinjia.app_template_filter('formatdate')
def formatdate_filter(val):
    try:
        return format_date(val, format='medium')
    except AttributeError as e:
        log.error('Babel error: %s, Current user locale: %s, Current User: %s', e,
                  current_user.locale,
                  current_user.name
                  )
        return val


@jinjia.app_template_filter('formatdateinput')
def format_date_input(val):
    input_date = val.isoformat().split('T', 1)[0]  # Hack to support dates <1900
    return '' if input_date == "0101-01-01" else input_date


@jinjia.app_template_filter('strftime')
def timestamptodate(date, fmt=None):
    date = datetime.datetime.fromtimestamp(
        int(date)/1000
    )
    native = date.replace(tzinfo=None)
    if fmt:
        time_format = fmt
    else:
        time_format = '%d %m %Y - %H:%S'
    return native.strftime(time_format)


@jinjia.app_template_filter('yesno')
def yesno(value, yes, no):
    return yes if value else no


@jinjia.app_template_filter('formatfloat')
def formatfloat(value, decimals=1):
    value = 0 if not value else value
    return ('{0:.' + str(decimals) + 'f}').format(value).rstrip('0').rstrip('.')


@jinjia.app_template_filter('formatseriesindex')
def formatseriesindex_filter(series_index):
    if series_index:
        try:
            if int(series_index) - series_index == 0:
                return int(series_index)
            else:
                return series_index
        except (ValueError, TypeError):
            return series_index
    return 0


@jinjia.app_template_filter('escapedlink')
def escapedlink_filter(url, text):
    return "<a href='{}'>{}</a>".format(url, escape(text))


@jinjia.app_template_filter('uuidfilter')
def uuidfilter(var):
    return uuid4()


@jinjia.app_template_filter('cache_timestamp')
def cache_timestamp(rolling_period='month'):
    if rolling_period == 'day':
        return str(int(datetime.datetime.today().replace(hour=1, minute=1).timestamp()))
    elif rolling_period == 'year':
        return str(int(datetime.datetime.today().replace(day=1).timestamp()))
    else:
        return str(int(datetime.datetime.today().replace(month=1, day=1).timestamp()))


@jinjia.app_template_filter('last_modified')
def book_last_modified(book):
    return str(int(book.last_modified.timestamp()))


@jinjia.app_template_filter('get_cover_srcset')
def get_cover_srcset(book):
    srcset = list()
    resolutions = {
        constants.COVER_THUMBNAIL_SMALL: 'sm',
        constants.COVER_THUMBNAIL_MEDIUM: 'md',
        constants.COVER_THUMBNAIL_LARGE: 'lg'
    }
    for resolution, shortname in resolutions.items():
        url = url_for('web.get_cover', book_id=book.id, resolution=shortname, c=book_last_modified(book))
        srcset.append(f'{url} {resolution}x')
    return ', '.join(srcset)


@jinjia.app_template_filter('get_series_srcset')
def get_cover_srcset(series):
    srcset = list()
    resolutions = {
        constants.COVER_THUMBNAIL_SMALL: 'sm',
        constants.COVER_THUMBNAIL_MEDIUM: 'md',
        constants.COVER_THUMBNAIL_LARGE: 'lg'
    }
    for resolution, shortname in resolutions.items():
        url = url_for('web.get_series_cover', series_id=series.id, resolution=shortname, c=cache_timestamp())
        srcset.append(f'{url} {resolution}x')
    return ', '.join(srcset)
