# ext/serializer.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Serializer/Deserializer objects for usage with SQLAlchemy query structures,
allowing "contextual" deserialization.

Any SQLAlchemy query structure, either based on sqlalchemy.sql.*
or sqlalchemy.orm.* can be used.  The mappers, Tables, Columns, Session
etc. which are referenced by the structure are not persisted in serialized
form, but are instead re-associated with the query structure
when it is deserialized.

Usage is nearly the same as that of the standard Python pickle module::

    from sqlalchemy.ext.serializer import loads, dumps
    metadata = MetaData(bind=some_engine)
    Session = scoped_session(sessionmaker())

    # ... define mappers

    query = Session.query(MyClass).filter(MyClass.somedata=='foo').order_by(MyClass.sortkey)

    # pickle the query
    serialized = dumps(query)

    # unpickle.  Pass in metadata + scoped_session
    query2 = loads(serialized, metadata, Session)

    print query2.all()

Similar restrictions as when using raw pickle apply; mapped classes must be
themselves be pickleable, meaning they are importable from a module-level
namespace.

The serializer module is only appropriate for query structures.  It is not
needed for:

* instances of user-defined classes.   These contain no references to engines,
  sessions or expression constructs in the typical case and can be serialized
  directly.

* Table metadata that is to be loaded entirely from the serialized structure
  (i.e. is not already declared in the application).   Regular
  pickle.loads()/dumps() can be used to fully dump any ``MetaData`` object,
  typically one which was reflected from an existing database at some previous
  point in time.  The serializer module is specifically for the opposite case,
  where the Table metadata is already present in memory.

"""

from ..orm import class_mapper
from ..orm.session import Session
from ..orm.mapper import Mapper
from ..orm.interfaces import MapperProperty
from ..orm.attributes import QueryableAttribute
from .. import Table, Column
from ..engine import Engine
from ..util import pickle
import re
import base64
# Py3K
#from io import BytesIO as byte_buffer
# Py2K
from cStringIO import StringIO as byte_buffer
# end Py2K

# Py3K
#def b64encode(x):
#    return base64.b64encode(x).decode('ascii')
#def b64decode(x):
#    return base64.b64decode(x.encode('ascii'))
# Py2K
b64encode = base64.b64encode
b64decode = base64.b64decode
# end Py2K

__all__ = ['Serializer', 'Deserializer', 'dumps', 'loads']


def Serializer(*args, **kw):
    pickler = pickle.Pickler(*args, **kw)

    def persistent_id(obj):
        #print "serializing:", repr(obj)
        if isinstance(obj, QueryableAttribute):
            cls = obj.impl.class_
            key = obj.impl.key
            id = "attribute:" + key + ":" + b64encode(pickle.dumps(cls))
        elif isinstance(obj, Mapper) and not obj.non_primary:
            id = "mapper:" + b64encode(pickle.dumps(obj.class_))
        elif isinstance(obj, MapperProperty) and not obj.parent.non_primary:
            id = "mapperprop:" + b64encode(pickle.dumps(obj.parent.class_)) + \
                                    ":" + obj.key
        elif isinstance(obj, Table):
            id = "table:" + str(obj)
        elif isinstance(obj, Column) and isinstance(obj.table, Table):
            id = "column:" + str(obj.table) + ":" + obj.key
        elif isinstance(obj, Session):
            id = "session:"
        elif isinstance(obj, Engine):
            id = "engine:"
        else:
            return None
        return id

    pickler.persistent_id = persistent_id
    return pickler

our_ids = re.compile(
            r'(mapperprop|mapper|table|column|session|attribute|engine):(.*)')


def Deserializer(file, metadata=None, scoped_session=None, engine=None):
    unpickler = pickle.Unpickler(file)

    def get_engine():
        if engine:
            return engine
        elif scoped_session and scoped_session().bind:
            return scoped_session().bind
        elif metadata and metadata.bind:
            return metadata.bind
        else:
            return None

    def persistent_load(id):
        m = our_ids.match(str(id))
        if not m:
            return None
        else:
            type_, args = m.group(1, 2)
            if type_ == 'attribute':
                key, clsarg = args.split(":")
                cls = pickle.loads(b64decode(clsarg))
                return getattr(cls, key)
            elif type_ == "mapper":
                cls = pickle.loads(b64decode(args))
                return class_mapper(cls)
            elif type_ == "mapperprop":
                mapper, keyname = args.split(':')
                cls = pickle.loads(b64decode(mapper))
                return class_mapper(cls).attrs[keyname]
            elif type_ == "table":
                return metadata.tables[args]
            elif type_ == "column":
                table, colname = args.split(':')
                return metadata.tables[table].c[colname]
            elif type_ == "session":
                return scoped_session()
            elif type_ == "engine":
                return get_engine()
            else:
                raise Exception("Unknown token: %s" % type_)
    unpickler.persistent_load = persistent_load
    return unpickler


def dumps(obj, protocol=0):
    buf = byte_buffer()
    pickler = Serializer(buf, protocol)
    pickler.dump(obj)
    return buf.getvalue()


def loads(data, metadata=None, scoped_session=None, engine=None):
    buf = byte_buffer(data)
    unpickler = Deserializer(buf, metadata, scoped_session, engine)
    return unpickler.load()
