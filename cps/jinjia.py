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

from __future__ import division, print_function, unicode_literals
import datetime
import mimetypes
import re

from babel.dates import format_date
from flask import Blueprint, request, url_for
from flask_babel import get_locale
from flask_login import current_user

from . import logger


jinjia = Blueprint('jinjia', __name__)
log = logger.create()


# pagination links in jinja
@jinjia.app_template_filter('url_for_other_page')
def url_for_other_page(page):
    args = request.view_args.copy()
    args['page'] = page
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
        conformed_timestamp = re.sub(r"[:]|([-](?!((\d{2}[:]\d{2})|(\d{4}))$))", '', val)
        formatdate = datetime.datetime.strptime(conformed_timestamp[:15], "%Y%m%d %H%M%S")
        return format_date(formatdate, format='medium', locale=get_locale())
    except AttributeError as e:
        log.error('Babel error: %s, Current user locale: %s, Current User: %s', e,
                  current_user.locale,
                  current_user.nickname
                  )
        return formatdate


@jinjia.app_template_filter('formatdateinput')
def format_date_input(val):
    conformed_timestamp = re.sub(r"[:]|([-](?!((\d{2}[:]\d{2})|(\d{4}))$))", '', val)
    date_obj = datetime.datetime.strptime(conformed_timestamp[:15], "%Y%m%d %H%M%S")
    input_date = date_obj.isoformat().split('T', 1)[0]  # Hack to support dates <1900
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
