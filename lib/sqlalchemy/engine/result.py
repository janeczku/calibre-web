# engine/result.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Define result set constructs including :class:`.ResultProxy`
and :class:`.RowProxy."""


from itertools import izip
from .. import exc, types, util
from ..sql import expression
import collections

# This reconstructor is necessary so that pickles with the C extension or
# without use the same Binary format.
try:
    # We need a different reconstructor on the C extension so that we can
    # add extra checks that fields have correctly been initialized by
    # __setstate__.
    from sqlalchemy.cresultproxy import safe_rowproxy_reconstructor

    # The extra function embedding is needed so that the
    # reconstructor function has the same signature whether or not
    # the extension is present.
    def rowproxy_reconstructor(cls, state):
        return safe_rowproxy_reconstructor(cls, state)
except ImportError:
    def rowproxy_reconstructor(cls, state):
        obj = cls.__new__(cls)
        obj.__setstate__(state)
        return obj

try:
    from sqlalchemy.cresultproxy import BaseRowProxy
except ImportError:
    class BaseRowProxy(object):
        __slots__ = ('_parent', '_row', '_processors', '_keymap')

        def __init__(self, parent, row, processors, keymap):
            """RowProxy objects are constructed by ResultProxy objects."""

            self._parent = parent
            self._row = row
            self._processors = processors
            self._keymap = keymap

        def __reduce__(self):
            return (rowproxy_reconstructor,
                    (self.__class__, self.__getstate__()))

        def values(self):
            """Return the values represented by this RowProxy as a list."""
            return list(self)

        def __iter__(self):
            for processor, value in izip(self._processors, self._row):
                if processor is None:
                    yield value
                else:
                    yield processor(value)

        def __len__(self):
            return len(self._row)

        def __getitem__(self, key):
            try:
                processor, obj, index = self._keymap[key]
            except KeyError:
                processor, obj, index = self._parent._key_fallback(key)
            except TypeError:
                if isinstance(key, slice):
                    l = []
                    for processor, value in izip(self._processors[key],
                                                 self._row[key]):
                        if processor is None:
                            l.append(value)
                        else:
                            l.append(processor(value))
                    return tuple(l)
                else:
                    raise
            if index is None:
                raise exc.InvalidRequestError(
                        "Ambiguous column name '%s' in result set! "
                        "try 'use_labels' option on select statement." % key)
            if processor is not None:
                return processor(self._row[index])
            else:
                return self._row[index]

        def __getattr__(self, name):
            try:
                return self[name]
            except KeyError, e:
                raise AttributeError(e.args[0])


class RowProxy(BaseRowProxy):
    """Proxy values from a single cursor row.

    Mostly follows "ordered dictionary" behavior, mapping result
    values to the string-based column name, the integer position of
    the result in the row, as well as Column instances which can be
    mapped to the original Columns that produced this result set (for
    results that correspond to constructed SQL expressions).
    """
    __slots__ = ()

    def __contains__(self, key):
        return self._parent._has_key(self._row, key)

    def __getstate__(self):
        return {
            '_parent': self._parent,
            '_row': tuple(self)
        }

    def __setstate__(self, state):
        self._parent = parent = state['_parent']
        self._row = state['_row']
        self._processors = parent._processors
        self._keymap = parent._keymap

    __hash__ = None

    def __eq__(self, other):
        return other is self or other == tuple(self)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return repr(tuple(self))

    def has_key(self, key):
        """Return True if this RowProxy contains the given key."""

        return self._parent._has_key(self._row, key)

    def items(self):
        """Return a list of tuples, each tuple containing a key/value pair."""
        # TODO: no coverage here
        return [(key, self[key]) for key in self.iterkeys()]

    def keys(self):
        """Return the list of keys as strings represented by this RowProxy."""

        return self._parent.keys

    def iterkeys(self):
        return iter(self._parent.keys)

    def itervalues(self):
        return iter(self)

try:
    # Register RowProxy with Sequence,
    # so sequence protocol is implemented
    from collections import Sequence
    Sequence.register(RowProxy)
except ImportError:
    pass


class ResultMetaData(object):
    """Handle cursor.description, applying additional info from an execution
    context."""

    def __init__(self, parent, metadata):
        self._processors = processors = []

        # We do not strictly need to store the processor in the key mapping,
        # though it is faster in the Python version (probably because of the
        # saved attribute lookup self._processors)
        self._keymap = keymap = {}
        self.keys = []
        context = parent.context
        dialect = context.dialect
        typemap = dialect.dbapi_type_map
        translate_colname = context._translate_colname
        self.case_sensitive = dialect.case_sensitive

        # high precedence key values.
        primary_keymap = {}

        for i, rec in enumerate(metadata):
            colname = rec[0]
            coltype = rec[1]

            if dialect.description_encoding:
                colname = dialect._description_decoder(colname)

            if translate_colname:
                colname, untranslated = translate_colname(colname)

            if dialect.requires_name_normalize:
                colname = dialect.normalize_name(colname)

            if context.result_map:
                try:
                    name, obj, type_ = context.result_map[colname
                                                    if self.case_sensitive
                                                    else colname.lower()]
                except KeyError:
                    name, obj, type_ = \
                        colname, None, typemap.get(coltype, types.NULLTYPE)
            else:
                name, obj, type_ = \
                        colname, None, typemap.get(coltype, types.NULLTYPE)

            processor = context.get_result_processor(type_, colname, coltype)

            processors.append(processor)
            rec = (processor, obj, i)

            # indexes as keys. This is only needed for the Python version of
            # RowProxy (the C version uses a faster path for integer indexes).
            primary_keymap[i] = rec

            # populate primary keymap, looking for conflicts.
            if primary_keymap.setdefault(
                                name if self.case_sensitive
                                else name.lower(),
                                rec) is not rec:
                # place a record that doesn't have the "index" - this
                # is interpreted later as an AmbiguousColumnError,
                # but only when actually accessed.   Columns
                # colliding by name is not a problem if those names
                # aren't used; integer access is always
                # unambiguous.
                primary_keymap[name
                                if self.case_sensitive
                                else name.lower()] = rec = (None, obj, None)

            self.keys.append(colname)
            if obj:
                for o in obj:
                    keymap[o] = rec
                    # technically we should be doing this but we
                    # are saving on callcounts by not doing so.
                    # if keymap.setdefault(o, rec) is not rec:
                    #    keymap[o] = (None, obj, None)

            if translate_colname and \
                untranslated:
                keymap[untranslated] = rec

        # overwrite keymap values with those of the
        # high precedence keymap.
        keymap.update(primary_keymap)

        if parent._echo:
            context.engine.logger.debug(
                "Col %r", tuple(x[0] for x in metadata))

    @util.pending_deprecation("0.8", "sqlite dialect uses "
                    "_translate_colname() now")
    def _set_keymap_synonym(self, name, origname):
        """Set a synonym for the given name.

        Some dialects (SQLite at the moment) may use this to
        adjust the column names that are significant within a
        row.

        """
        rec = (processor, obj, i) = self._keymap[origname if
                                                self.case_sensitive
                                                else origname.lower()]
        if self._keymap.setdefault(name, rec) is not rec:
            self._keymap[name] = (processor, obj, None)

    def _key_fallback(self, key, raiseerr=True):
        map = self._keymap
        result = None
        if isinstance(key, basestring):
            result = map.get(key if self.case_sensitive else key.lower())
        # fallback for targeting a ColumnElement to a textual expression
        # this is a rare use case which only occurs when matching text()
        # or colummn('name') constructs to ColumnElements, or after a
        # pickle/unpickle roundtrip
        elif isinstance(key, expression.ColumnElement):
            if key._label and (
                            key._label
                            if self.case_sensitive
                            else key._label.lower()) in map:
                result = map[key._label
                            if self.case_sensitive
                            else key._label.lower()]
            elif hasattr(key, 'name') and (
                                    key.name
                                    if self.case_sensitive
                                    else key.name.lower()) in map:
                # match is only on name.
                result = map[key.name
                            if self.case_sensitive
                            else key.name.lower()]
            # search extra hard to make sure this
            # isn't a column/label name overlap.
            # this check isn't currently available if the row
            # was unpickled.
            if result is not None and \
                 result[1] is not None:
                for obj in result[1]:
                    if key._compare_name_for_result(obj):
                        break
                else:
                    result = None
        if result is None:
            if raiseerr:
                raise exc.NoSuchColumnError(
                    "Could not locate column in row for column '%s'" %
                        expression._string_or_unprintable(key))
            else:
                return None
        else:
            map[key] = result
        return result

    def _has_key(self, row, key):
        if key in self._keymap:
            return True
        else:
            return self._key_fallback(key, False) is not None

    def __getstate__(self):
        return {
            '_pickled_keymap': dict(
                (key, index)
                for key, (processor, obj, index) in self._keymap.iteritems()
                if isinstance(key, (basestring, int))
            ),
            'keys': self.keys,
            "case_sensitive": self.case_sensitive,
        }

    def __setstate__(self, state):
        # the row has been processed at pickling time so we don't need any
        # processor anymore
        self._processors = [None for _ in xrange(len(state['keys']))]
        self._keymap = keymap = {}
        for key, index in state['_pickled_keymap'].iteritems():
            # not preserving "obj" here, unfortunately our
            # proxy comparison fails with the unpickle
            keymap[key] = (None, None, index)
        self.keys = state['keys']
        self.case_sensitive = state['case_sensitive']
        self._echo = False


class ResultProxy(object):
    """Wraps a DB-API cursor object to provide easier access to row columns.

    Individual columns may be accessed by their integer position,
    case-insensitive column name, or by ``schema.Column``
    object. e.g.::

      row = fetchone()

      col1 = row[0]    # access via integer position

      col2 = row['col2']   # access via name

      col3 = row[mytable.c.mycol] # access via Column object.

    ``ResultProxy`` also handles post-processing of result column
    data using ``TypeEngine`` objects, which are referenced from
    the originating SQL statement that produced this result set.

    """

    _process_row = RowProxy
    out_parameters = None
    _can_close_connection = False
    _metadata = None

    def __init__(self, context):
        self.context = context
        self.dialect = context.dialect
        self.closed = False
        self.cursor = self._saved_cursor = context.cursor
        self.connection = context.root_connection
        self._echo = self.connection._echo and \
                        context.engine._should_log_debug()
        self._init_metadata()

    def _init_metadata(self):
        metadata = self._cursor_description()
        if metadata is not None:
            self._metadata = ResultMetaData(self, metadata)

    def keys(self):
        """Return the current set of string keys for rows."""
        if self._metadata:
            return self._metadata.keys
        else:
            return []

    @util.memoized_property
    def rowcount(self):
        """Return the 'rowcount' for this result.

        The 'rowcount' reports the number of rows *matched*
        by the WHERE criterion of an UPDATE or DELETE statement.

        .. note::

           Notes regarding :attr:`.ResultProxy.rowcount`:


           * This attribute returns the number of rows *matched*,
             which is not necessarily the same as the number of rows
             that were actually *modified* - an UPDATE statement, for example,
             may have no net change on a given row if the SET values
             given are the same as those present in the row already.
             Such a row would be matched but not modified.
             On backends that feature both styles, such as MySQL,
             rowcount is configured by default to return the match
             count in all cases.

           * :attr:`.ResultProxy.rowcount` is *only* useful in conjunction
             with an UPDATE or DELETE statement.  Contrary to what the Python
             DBAPI says, it does *not* return the
             number of rows available from the results of a SELECT statement
             as DBAPIs cannot support this functionality when rows are
             unbuffered.

           * :attr:`.ResultProxy.rowcount` may not be fully implemented by
             all dialects.  In particular, most DBAPIs do not support an
             aggregate rowcount result from an executemany call.
             The :meth:`.ResultProxy.supports_sane_rowcount` and
             :meth:`.ResultProxy.supports_sane_multi_rowcount` methods
             will report from the dialect if each usage is known to be
             supported.

           * Statements that use RETURNING may not return a correct
             rowcount.

        """
        try:
            return self.context.rowcount
        except Exception, e:
            self.connection._handle_dbapi_exception(
                              e, None, None, self.cursor, self.context)

    @property
    def lastrowid(self):
        """return the 'lastrowid' accessor on the DBAPI cursor.

        This is a DBAPI specific method and is only functional
        for those backends which support it, for statements
        where it is appropriate.  It's behavior is not
        consistent across backends.

        Usage of this method is normally unnecessary when
        using insert() expression constructs; the
        :attr:`~ResultProxy.inserted_primary_key` attribute provides a
        tuple of primary key values for a newly inserted row,
        regardless of database backend.

        """
        try:
            return self._saved_cursor.lastrowid
        except Exception, e:
            self.connection._handle_dbapi_exception(
                                 e, None, None,
                                 self._saved_cursor, self.context)

    @property
    def returns_rows(self):
        """True if this :class:`.ResultProxy` returns rows.

        I.e. if it is legal to call the methods
        :meth:`~.ResultProxy.fetchone`,
        :meth:`~.ResultProxy.fetchmany`
        :meth:`~.ResultProxy.fetchall`.

        """
        return self._metadata is not None

    @property
    def is_insert(self):
        """True if this :class:`.ResultProxy` is the result
        of a executing an expression language compiled
        :func:`.expression.insert` construct.

        When True, this implies that the
        :attr:`inserted_primary_key` attribute is accessible,
        assuming the statement did not include
        a user defined "returning" construct.

        """
        return self.context.isinsert

    def _cursor_description(self):
        """May be overridden by subclasses."""

        return self._saved_cursor.description

    def close(self, _autoclose_connection=True):
        """Close this ResultProxy.

        Closes the underlying DBAPI cursor corresponding to the execution.

        Note that any data cached within this ResultProxy is still available.
        For some types of results, this may include buffered rows.

        If this ResultProxy was generated from an implicit execution,
        the underlying Connection will also be closed (returns the
        underlying DBAPI connection to the connection pool.)

        This method is called automatically when:

        * all result rows are exhausted using the fetchXXX() methods.
        * cursor.description is None.

        """

        if not self.closed:
            self.closed = True
            self.connection._safe_close_cursor(self.cursor)
            if _autoclose_connection and \
                self.connection.should_close_with_result:
                self.connection.close()
            # allow consistent errors
            self.cursor = None

    def __iter__(self):
        while True:
            row = self.fetchone()
            if row is None:
                raise StopIteration
            else:
                yield row

    @util.memoized_property
    def inserted_primary_key(self):
        """Return the primary key for the row just inserted.

        The return value is a list of scalar values
        corresponding to the list of primary key columns
        in the target table.

        This only applies to single row :func:`.insert`
        constructs which did not explicitly specify
        :meth:`.Insert.returning`.

        Note that primary key columns which specify a
        server_default clause,
        or otherwise do not qualify as "autoincrement"
        columns (see the notes at :class:`.Column`), and were
        generated using the database-side default, will
        appear in this list as ``None`` unless the backend
        supports "returning" and the insert statement executed
        with the "implicit returning" enabled.

        Raises :class:`~sqlalchemy.exc.InvalidRequestError` if the executed
        statement is not a compiled expression construct
        or is not an insert() construct.

        """

        if not self.context.compiled:
            raise exc.InvalidRequestError(
                        "Statement is not a compiled "
                        "expression construct.")
        elif not self.context.isinsert:
            raise exc.InvalidRequestError(
                        "Statement is not an insert() "
                        "expression construct.")
        elif self.context._is_explicit_returning:
            raise exc.InvalidRequestError(
                        "Can't call inserted_primary_key "
                        "when returning() "
                        "is used.")

        return self.context.inserted_primary_key

    def last_updated_params(self):
        """Return the collection of updated parameters from this
        execution.

        Raises :class:`~sqlalchemy.exc.InvalidRequestError` if the executed
        statement is not a compiled expression construct
        or is not an update() construct.

        """
        if not self.context.compiled:
            raise exc.InvalidRequestError(
                        "Statement is not a compiled "
                        "expression construct.")
        elif not self.context.isupdate:
            raise exc.InvalidRequestError(
                        "Statement is not an update() "
                        "expression construct.")
        elif self.context.executemany:
            return self.context.compiled_parameters
        else:
            return self.context.compiled_parameters[0]

    def last_inserted_params(self):
        """Return the collection of inserted parameters from this
        execution.

        Raises :class:`~sqlalchemy.exc.InvalidRequestError` if the executed
        statement is not a compiled expression construct
        or is not an insert() construct.

        """
        if not self.context.compiled:
            raise exc.InvalidRequestError(
                        "Statement is not a compiled "
                        "expression construct.")
        elif not self.context.isinsert:
            raise exc.InvalidRequestError(
                        "Statement is not an insert() "
                        "expression construct.")
        elif self.context.executemany:
            return self.context.compiled_parameters
        else:
            return self.context.compiled_parameters[0]

    def lastrow_has_defaults(self):
        """Return ``lastrow_has_defaults()`` from the underlying
        :class:`.ExecutionContext`.

        See :class:`.ExecutionContext` for details.

        """

        return self.context.lastrow_has_defaults()

    def postfetch_cols(self):
        """Return ``postfetch_cols()`` from the underlying
        :class:`.ExecutionContext`.

        See :class:`.ExecutionContext` for details.

        Raises :class:`~sqlalchemy.exc.InvalidRequestError` if the executed
        statement is not a compiled expression construct
        or is not an insert() or update() construct.

        """

        if not self.context.compiled:
            raise exc.InvalidRequestError(
                        "Statement is not a compiled "
                        "expression construct.")
        elif not self.context.isinsert and not self.context.isupdate:
            raise exc.InvalidRequestError(
                        "Statement is not an insert() or update() "
                        "expression construct.")
        return self.context.postfetch_cols

    def prefetch_cols(self):
        """Return ``prefetch_cols()`` from the underlying
        :class:`.ExecutionContext`.

        See :class:`.ExecutionContext` for details.

        Raises :class:`~sqlalchemy.exc.InvalidRequestError` if the executed
        statement is not a compiled expression construct
        or is not an insert() or update() construct.

        """

        if not self.context.compiled:
            raise exc.InvalidRequestError(
                        "Statement is not a compiled "
                        "expression construct.")
        elif not self.context.isinsert and not self.context.isupdate:
            raise exc.InvalidRequestError(
                        "Statement is not an insert() or update() "
                        "expression construct.")
        return self.context.prefetch_cols

    def supports_sane_rowcount(self):
        """Return ``supports_sane_rowcount`` from the dialect.

        See :attr:`.ResultProxy.rowcount` for background.

        """

        return self.dialect.supports_sane_rowcount

    def supports_sane_multi_rowcount(self):
        """Return ``supports_sane_multi_rowcount`` from the dialect.

        See :attr:`.ResultProxy.rowcount` for background.

        """

        return self.dialect.supports_sane_multi_rowcount

    def _fetchone_impl(self):
        try:
            return self.cursor.fetchone()
        except AttributeError:
            self._non_result()

    def _fetchmany_impl(self, size=None):
        try:
            if size is None:
                return self.cursor.fetchmany()
            else:
                return self.cursor.fetchmany(size)
        except AttributeError:
            self._non_result()

    def _fetchall_impl(self):
        try:
            return self.cursor.fetchall()
        except AttributeError:
            self._non_result()

    def _non_result(self):
        if self._metadata is None:
            raise exc.ResourceClosedError(
            "This result object does not return rows. "
            "It has been closed automatically.",
            )
        else:
            raise exc.ResourceClosedError("This result object is closed.")

    def process_rows(self, rows):
        process_row = self._process_row
        metadata = self._metadata
        keymap = metadata._keymap
        processors = metadata._processors
        if self._echo:
            log = self.context.engine.logger.debug
            l = []
            for row in rows:
                log("Row %r", row)
                l.append(process_row(metadata, row, processors, keymap))
            return l
        else:
            return [process_row(metadata, row, processors, keymap)
                    for row in rows]

    def fetchall(self):
        """Fetch all rows, just like DB-API ``cursor.fetchall()``."""

        try:
            l = self.process_rows(self._fetchall_impl())
            self.close()
            return l
        except Exception, e:
            self.connection._handle_dbapi_exception(
                                    e, None, None,
                                    self.cursor, self.context)

    def fetchmany(self, size=None):
        """Fetch many rows, just like DB-API
        ``cursor.fetchmany(size=cursor.arraysize)``.

        If rows are present, the cursor remains open after this is called.
        Else the cursor is automatically closed and an empty list is returned.

        """

        try:
            l = self.process_rows(self._fetchmany_impl(size))
            if len(l) == 0:
                self.close()
            return l
        except Exception, e:
            self.connection._handle_dbapi_exception(
                                    e, None, None,
                                    self.cursor, self.context)

    def fetchone(self):
        """Fetch one row, just like DB-API ``cursor.fetchone()``.

        If a row is present, the cursor remains open after this is called.
        Else the cursor is automatically closed and None is returned.

        """
        try:
            row = self._fetchone_impl()
            if row is not None:
                return self.process_rows([row])[0]
            else:
                self.close()
                return None
        except Exception, e:
            self.connection._handle_dbapi_exception(
                                    e, None, None,
                                    self.cursor, self.context)

    def first(self):
        """Fetch the first row and then close the result set unconditionally.

        Returns None if no row is present.

        """
        if self._metadata is None:
            self._non_result()

        try:
            row = self._fetchone_impl()
        except Exception, e:
            self.connection._handle_dbapi_exception(
                                    e, None, None,
                                    self.cursor, self.context)

        try:
            if row is not None:
                return self.process_rows([row])[0]
            else:
                return None
        finally:
            self.close()

    def scalar(self):
        """Fetch the first column of the first row, and close the result set.

        Returns None if no row is present.

        """
        row = self.first()
        if row is not None:
            return row[0]
        else:
            return None


class BufferedRowResultProxy(ResultProxy):
    """A ResultProxy with row buffering behavior.

    ``ResultProxy`` that buffers the contents of a selection of rows
    before ``fetchone()`` is called.  This is to allow the results of
    ``cursor.description`` to be available immediately, when
    interfacing with a DB-API that requires rows to be consumed before
    this information is available (currently psycopg2, when used with
    server-side cursors).

    The pre-fetching behavior fetches only one row initially, and then
    grows its buffer size by a fixed amount with each successive need
    for additional rows up to a size of 100.
    """

    def _init_metadata(self):
        self.__buffer_rows()
        super(BufferedRowResultProxy, self)._init_metadata()

    # this is a "growth chart" for the buffering of rows.
    # each successive __buffer_rows call will use the next
    # value in the list for the buffer size until the max
    # is reached
    size_growth = {
        1: 5,
        5: 10,
        10: 20,
        20: 50,
        50: 100,
        100: 250,
        250: 500,
        500: 1000
    }

    def __buffer_rows(self):
        size = getattr(self, '_bufsize', 1)
        self.__rowbuffer = collections.deque(self.cursor.fetchmany(size))
        self._bufsize = self.size_growth.get(size, size)

    def _fetchone_impl(self):
        if self.closed:
            return None
        if not self.__rowbuffer:
            self.__buffer_rows()
            if not self.__rowbuffer:
                return None
        return self.__rowbuffer.popleft()

    def _fetchmany_impl(self, size=None):
        if size is None:
            return self._fetchall_impl()
        result = []
        for x in range(0, size):
            row = self._fetchone_impl()
            if row is None:
                break
            result.append(row)
        return result

    def _fetchall_impl(self):
        self.__rowbuffer.extend(self.cursor.fetchall())
        ret = self.__rowbuffer
        self.__rowbuffer = collections.deque()
        return ret


class FullyBufferedResultProxy(ResultProxy):
    """A result proxy that buffers rows fully upon creation.

    Used for operations where a result is to be delivered
    after the database conversation can not be continued,
    such as MSSQL INSERT...OUTPUT after an autocommit.

    """
    def _init_metadata(self):
        super(FullyBufferedResultProxy, self)._init_metadata()
        self.__rowbuffer = self._buffer_rows()

    def _buffer_rows(self):
        return collections.deque(self.cursor.fetchall())

    def _fetchone_impl(self):
        if self.__rowbuffer:
            return self.__rowbuffer.popleft()
        else:
            return None

    def _fetchmany_impl(self, size=None):
        if size is None:
            return self._fetchall_impl()
        result = []
        for x in range(0, size):
            row = self._fetchone_impl()
            if row is None:
                break
            result.append(row)
        return result

    def _fetchall_impl(self):
        ret = self.__rowbuffer
        self.__rowbuffer = collections.deque()
        return ret


class BufferedColumnRow(RowProxy):
    def __init__(self, parent, row, processors, keymap):
        # preprocess row
        row = list(row)
        # this is a tad faster than using enumerate
        index = 0
        for processor in parent._orig_processors:
            if processor is not None:
                row[index] = processor(row[index])
            index += 1
        row = tuple(row)
        super(BufferedColumnRow, self).__init__(parent, row,
                                                processors, keymap)


class BufferedColumnResultProxy(ResultProxy):
    """A ResultProxy with column buffering behavior.

    ``ResultProxy`` that loads all columns into memory each time
    fetchone() is called.  If fetchmany() or fetchall() are called,
    the full grid of results is fetched.  This is to operate with
    databases where result rows contain "live" results that fall out
    of scope unless explicitly fetched.  Currently this includes
    cx_Oracle LOB objects.

    """

    _process_row = BufferedColumnRow

    def _init_metadata(self):
        super(BufferedColumnResultProxy, self)._init_metadata()
        metadata = self._metadata
        # orig_processors will be used to preprocess each row when they are
        # constructed.
        metadata._orig_processors = metadata._processors
        # replace the all type processors by None processors.
        metadata._processors = [None for _ in xrange(len(metadata.keys))]
        keymap = {}
        for k, (func, obj, index) in metadata._keymap.iteritems():
            keymap[k] = (None, obj, index)
        self._metadata._keymap = keymap

    def fetchall(self):
        # can't call cursor.fetchall(), since rows must be
        # fully processed before requesting more from the DBAPI.
        l = []
        while True:
            row = self.fetchone()
            if row is None:
                break
            l.append(row)
        return l

    def fetchmany(self, size=None):
        # can't call cursor.fetchmany(), since rows must be
        # fully processed before requesting more from the DBAPI.
        if size is None:
            return self.fetchall()
        l = []
        for i in xrange(size):
            row = self.fetchone()
            if row is None:
                break
            l.append(row)
        return l
