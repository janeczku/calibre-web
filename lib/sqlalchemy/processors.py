# sqlalchemy/processors.py
# Copyright (C) 2010-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
# Copyright (C) 2010 Gaetan de Menten gdementen@gmail.com
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""defines generic type conversion functions, as used in bind and result
processors.

They all share one common characteristic: None is passed through unchanged.

"""

import codecs
import re
import datetime


def str_to_datetime_processor_factory(regexp, type_):
    rmatch = regexp.match
    # Even on python2.6 datetime.strptime is both slower than this code
    # and it does not support microseconds.
    has_named_groups = bool(regexp.groupindex)

    def process(value):
        if value is None:
            return None
        else:
            try:
                m = rmatch(value)
            except TypeError:
                raise ValueError("Couldn't parse %s string '%r' "
                                "- value is not a string." %
                                (type_.__name__, value))
            if m is None:
                raise ValueError("Couldn't parse %s string: "
                                "'%s'" % (type_.__name__, value))
            if has_named_groups:
                groups = m.groupdict(0)
                return type_(**dict(zip(groups.iterkeys(),
                                        map(int, groups.itervalues()))))
            else:
                return type_(*map(int, m.groups(0)))
    return process


def boolean_to_int(value):
    if value is None:
        return None
    else:
        return int(value)


def py_fallback():
    def to_unicode_processor_factory(encoding, errors=None):
        decoder = codecs.getdecoder(encoding)

        def process(value):
            if value is None:
                return None
            else:
                # decoder returns a tuple: (value, len). Simply dropping the
                # len part is safe: it is done that way in the normal
                # 'xx'.decode(encoding) code path.
                return decoder(value, errors)[0]
        return process

    def to_decimal_processor_factory(target_class, scale=10):
        fstring = "%%.%df" % scale

        def process(value):
            if value is None:
                return None
            else:
                return target_class(fstring % value)
        return process

    def to_float(value):
        if value is None:
            return None
        else:
            return float(value)

    def to_str(value):
        if value is None:
            return None
        else:
            return str(value)

    def int_to_boolean(value):
        if value is None:
            return None
        else:
            return value and True or False

    DATETIME_RE = re.compile(
                        "(\d+)-(\d+)-(\d+) (\d+):(\d+):(\d+)(?:\.(\d+))?")
    TIME_RE = re.compile("(\d+):(\d+):(\d+)(?:\.(\d+))?")
    DATE_RE = re.compile("(\d+)-(\d+)-(\d+)")

    str_to_datetime = str_to_datetime_processor_factory(DATETIME_RE,
                                                        datetime.datetime)
    str_to_time = str_to_datetime_processor_factory(TIME_RE, datetime.time)
    str_to_date = str_to_datetime_processor_factory(DATE_RE, datetime.date)
    return locals()

try:
    from sqlalchemy.cprocessors import UnicodeResultProcessor, \
                                       DecimalResultProcessor, \
                                       to_float, to_str, int_to_boolean, \
                                       str_to_datetime, str_to_time, \
                                       str_to_date

    def to_unicode_processor_factory(encoding, errors=None):
        # this is cumbersome but it would be even more so on the C side
        if errors is not None:
            return UnicodeResultProcessor(encoding, errors).process
        else:
            return UnicodeResultProcessor(encoding).process

    def to_decimal_processor_factory(target_class, scale=10):
        # Note that the scale argument is not taken into account for integer
        # values in the C implementation while it is in the Python one.
        # For example, the Python implementation might return
        # Decimal('5.00000') whereas the C implementation will
        # return Decimal('5'). These are equivalent of course.
        return DecimalResultProcessor(target_class, "%%.%df" % scale).process

except ImportError:
    globals().update(py_fallback())
