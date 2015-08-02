
from . import exclusions
from .. import schema, event
from . import config

__all__ = 'Table', 'Column',

table_options = {}


def Table(*args, **kw):
    """A schema.Table wrapper/hook for dialect-specific tweaks."""

    test_opts = dict([(k, kw.pop(k)) for k in kw.keys()
                      if k.startswith('test_')])

    kw.update(table_options)

    if exclusions.against('mysql'):
        if 'mysql_engine' not in kw and 'mysql_type' not in kw:
            if 'test_needs_fk' in test_opts or 'test_needs_acid' in test_opts:
                kw['mysql_engine'] = 'InnoDB'
            else:
                kw['mysql_engine'] = 'MyISAM'

    # Apply some default cascading rules for self-referential foreign keys.
    # MySQL InnoDB has some issues around seleting self-refs too.
    if exclusions.against('firebird'):
        table_name = args[0]
        unpack = (config.db.dialect.
                  identifier_preparer.unformat_identifiers)

        # Only going after ForeignKeys in Columns.  May need to
        # expand to ForeignKeyConstraint too.
        fks = [fk
               for col in args if isinstance(col, schema.Column)
               for fk in col.foreign_keys]

        for fk in fks:
            # root around in raw spec
            ref = fk._colspec
            if isinstance(ref, schema.Column):
                name = ref.table.name
            else:
                # take just the table name: on FB there cannot be
                # a schema, so the first element is always the
                # table name, possibly followed by the field name
                name = unpack(ref)[0]
            if name == table_name:
                if fk.ondelete is None:
                    fk.ondelete = 'CASCADE'
                if fk.onupdate is None:
                    fk.onupdate = 'CASCADE'

    return schema.Table(*args, **kw)


def Column(*args, **kw):
    """A schema.Column wrapper/hook for dialect-specific tweaks."""

    test_opts = dict([(k, kw.pop(k)) for k in kw.keys()
                      if k.startswith('test_')])

    if not config.requirements.foreign_key_ddl.enabled:
        args = [arg for arg in args if not isinstance(arg, schema.ForeignKey)]

    col = schema.Column(*args, **kw)
    if 'test_needs_autoincrement' in test_opts and \
        kw.get('primary_key', False):

        # allow any test suite to pick up on this
        col.info['test_needs_autoincrement'] = True

        # hardcoded rule for firebird, oracle; this should
        # be moved out
        if exclusions.against('firebird', 'oracle'):
            def add_seq(c, tbl):
                c._init_items(
                    schema.Sequence(_truncate_name(
                            config.db.dialect, tbl.name + '_' + c.name + '_seq'),
                        optional=True)
                )
            event.listen(col, 'after_parent_attach', add_seq, propagate=True)
    return col





def _truncate_name(dialect, name):
    if len(name) > dialect.max_identifier_length:
        return name[0:max(dialect.max_identifier_length - 6, 0)] + \
                "_" + hex(hash(name) % 64)[2:]
    else:
        return name
