"""
Calibre composite column template evaluator.

Ported from calibre/src/calibre/utils/formatter.py and formatter_functions.py.
Supports simple-mode templates ({field}, {field:func(args)}, {#label}).
Does not support program: or python: modes.
"""

import re
import string
from functools import lru_cache
from math import ceil, floor, modf, trunc

from . import logger

log = logger.create()


# ---------------------------------------------------------------------------
# Argument scanner — ported from calibre's args_scanner()
# ---------------------------------------------------------------------------

@lru_cache(maxsize=2)
def _args_scanner():
    return re.Scanner([
        (r',', lambda x, t: ''),
        (r'.*?(?:(?<!\\),)', lambda x, t: t[:-1]),
        (r'.*?\)', lambda x, t: t[:-1]),
    ])


def _parse_args(text):
    tokens, _ = _args_scanner().scan(text)
    return [re.sub(r'\\,', ',', a) for a in tokens]


def _split_gpm_args(args_str):
    """Split comma-separated GPM args respecting nested parens and quotes."""
    args, depth, in_quote, current = [], 0, None, []
    for ch in args_str:
        if in_quote:
            current.append(ch)
            if ch == in_quote:
                in_quote = None
        elif ch in ("'", '"'):
            in_quote = ch
            current.append(ch)
        elif ch == '(':
            depth += 1
            current.append(ch)
        elif ch == ')':
            depth -= 1
            current.append(ch)
        elif ch == ',' and depth == 0:
            args.append(''.join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        args.append(''.join(current).strip())
    return [a for a in args if a]


def _eval_gpm_expr(expr, fields):
    """Recursively evaluate a calibre General Program Mode expression."""
    expr = expr.strip()
    if not expr:
        return ''
    # String literal
    if len(expr) >= 2 and expr[0] in ("'", '"') and expr[-1] == expr[0]:
        return expr[1:-1]
    # Function call: name(args...)
    p = expr.find('(')
    if p > 0 and expr.endswith(')'):
        fname = expr[:p].strip()
        evaled = [_eval_gpm_expr(a, fields) for a in _split_gpm_args(expr[p + 1:-1])]
        if fname == 'field':
            return fields.get(evaled[0], '') if evaled else ''
        entry = _REGISTRY.get(fname)
        if entry:
            _, fn = entry
            val = evaled[0] if evaled else ''
            try:
                result = fn(val, *evaled[1:])
                return result if isinstance(result, str) else (str(result) if result is not None else '')
            except Exception as ex:
                log.warning("GPM function %r failed (args=%r): %s", fname, evaled, ex)
                return ''
        log.warning("GPM references unknown function %r", fname)
        return ''
    # Bare word — field name
    return fields.get(expr, '')


# ---------------------------------------------------------------------------
# Function implementations — signatures: fn(val, *extra_args) -> str
# ---------------------------------------------------------------------------

def _strcmp_key(x):
    return x.lower()


def _fn_strcmp(val, x, y, lt, eq, gt):
    lx, ly = x.lower(), y.lower()
    return lt if lx < ly else (eq if lx == ly else gt)


def _fn_strcmpcase(val, x, y, lt, eq, gt):
    return lt if x < y else (eq if x == y else gt)


def _fn_cmp(val, y, lt, eq, gt):
    v = float(val or 0)
    y = float(y or 0)
    return lt if v < y else (eq if v == y else gt)


def _fn_first_matching_cmp(val, *args):
    if len(args) % 2 != 0:
        raise ValueError('first_matching_cmp requires an even number of arguments')
    v = float(val or 0)
    for i in range(0, len(args) - 1, 2):
        if v < float(args[i] or 0):
            return args[i + 1]
    return args[-1]


def _fn_strcat(val, *args):
    return val + ''.join(args)


def _fn_strlen(val):
    return str(len(val))


def _fn_add(val, *args):
    return str(float(val or 0) + sum(float(a or 0) for a in args))


def _fn_subtract(val, y):
    return str(float(val or 0) - float(y or 0))


def _fn_multiply(val, *args):
    result = float(val or 0)
    for a in args:
        result *= float(a or 0)
    return str(result)


def _fn_divide(val, y):
    return str(float(val or 0) / float(y or 0))


def _fn_ceiling(val):
    return str(ceil(float(val or 0)))


def _fn_floor(val):
    return str(floor(float(val or 0)))


def _fn_round(val):
    return str(round(float(val or 0)))


def _fn_mod(val, y):
    return str(int(float(val or 0) % float(y or 0)))


def _fn_fractional_part(val):
    return str(modf(float(val or 0))[0])


def _fn_substr(val, start, end):
    s, e = int(start), int(end)
    return val[s: len(val) if e == 0 else e]


def _fn_test(val, text_if_set, text_if_empty):
    return text_if_set if val else text_if_empty


def _fn_contains(val, pattern, text_if_match, text_if_not):
    return text_if_match if re.search(pattern, val, re.I) else text_if_not


def _fn_re(val, pattern, replacement):
    return re.sub(pattern, replacement, val, flags=re.I)


def _fn_swap_around_comma(val):
    return re.sub(r'^(.*?),\s*(.*$)', r'\2 \1', val, flags=re.I).strip()


def _fn_ifempty(val, default):
    return val if val else default


def _fn_select(val, key):
    if not val:
        return ''
    prefix = key + ':'
    for part in (p.strip() for p in val.split(',')):
        if part.startswith(prefix):
            return part[len(prefix):]
    return ''


def _fn_list_count(val, sep):
    return str(len([x for x in val.split(sep) if x]))


def _fn_list_count_matching(val, pattern, sep):
    return str(sum(1 for x in (x.strip() for x in val.split(sep) if x.strip())
                   if re.search(pattern, x, re.I)))


def _fn_list_item(val, index, sep):
    if not val:
        return ''
    try:
        return val.split(sep)[int(index)].strip()
    except IndexError:
        return ''


def _fn_identifier_in_list(val, ident, *args):
    if len(args) == 0:
        fv_is_id, nfv = True, ''
    elif len(args) == 2:
        fv_is_id, fv, nfv = False, args[0], args[1]
    else:
        raise ValueError('identifier_in_list requires 2 or 4 arguments')
    parts = [v.strip() for v in val.split(',') if v.strip()]
    id_, _, regexp = ident.partition(':')
    if not id_:
        return nfv
    for candidate in parts:
        i, _, v = candidate.partition(':')
        if v and i == id_:
            if not regexp or re.search(regexp, v, re.I):
                return candidate if fv_is_id else fv
    return nfv


def _fn_str_in_list(val, sep, *args):
    if len(args) % 2 != 1:
        raise ValueError('str_in_list requires an odd number of arguments')
    l = [v.strip() for v in val.split(sep) if v.strip()]
    i = 0
    while i < len(args):
        if i + 1 >= len(args):
            return args[i]
        sf, fv = args[i], args[i + 1]
        candidates = [v.strip() for v in sf.split(sep) if v.strip()]
        for v in l:
            for c in candidates:
                if c.lower() == v.lower():
                    return fv
        i += 2
    return ''


def _fn_list_contains(val, sep, *args):
    if len(args) % 2 != 1:
        raise ValueError('list_contains requires an odd number of arguments')
    l = [v.strip() for v in val.split(sep) if v.strip()]
    i = 0
    while i < len(args):
        if i + 1 >= len(args):
            return args[i]
        sf, fv = args[i], args[i + 1]
        for v in l:
            if re.search(sf, v, re.I):
                return fv
        i += 2
    return ''


def _fn_switch(val, *args):
    if len(args) % 2 != 1:
        raise ValueError('switch requires an odd number of arguments')
    i = 0
    while i < len(args):
        if i + 1 >= len(args):
            return args[i]
        if re.search(args[i], val, re.I):
            return args[i + 1]
        i += 2
    return ''


def _fn_switch_if(val, *args):
    if len(args) % 2 != 1:
        raise ValueError('switch_if requires an odd number of arguments')
    i = 0
    while i < len(args):
        if i + 1 >= len(args):
            return args[i]
        if args[i]:
            return args[i + 1]
        i += 2
    return ''


def _fn_strcat_max(val, *args):
    if len(args) < 1 or len(args) % 2 != 1:
        raise ValueError('strcat_max requires an odd number of arguments (max, str1, [pre, str]+)')
    max_len = int(args[0])
    result = args[1] if len(args) > 1 else val
    i = 2
    while i + 1 < len(args):
        if len(result) + len(args[i]) + len(args[i + 1]) > max_len:
            break
        result += args[i] + args[i + 1]
        i += 2
    return result.strip()


def _fn_shorten(val, leading, center_string, trailing):
    l = max(0, int(leading))
    t = max(0, int(trailing))
    if len(val) > l + len(center_string) + t:
        return val[:l] + center_string + ('' if t == 0 else val[-t:])
    return val


def _fn_sublist(val, start_index, end_index, sep):
    if not val:
        return ''
    si, ei = int(start_index), int(end_index)
    parts = [v.strip() for v in val.split(sep)]
    joined_sep = ', ' if sep == ',' else sep
    try:
        return joined_sep.join(parts[si:] if ei == 0 else parts[si:ei])
    except Exception:
        return ''


_period_pattern = re.compile(r'(?<=[^\.\s])\.(?=[^\.\s])', re.U)


def _fn_subitems(val, start_index, end_index):
    if not val:
        return ''
    si, ei = int(start_index), int(end_index)
    has_periods = '.' in val
    items = [v.strip() for v in val.split(',') if v.strip()]
    rv = set()
    for item in items:
        components = _period_pattern.split(item) if has_periods and '.' in item else [item]
        try:
            t = '.'.join(components[si:] if ei == 0 else components[si:ei]).strip()
            if t:
                rv.add(t)
        except Exception:
            pass
    return ', '.join(sorted(rv, key=str.casefold))


def _fn_lookup(val, *args):
    # Simplified: cannot recurse into formatter fields, just return matched value literal
    if len(args) == 2:
        return args[0] if val else args[1]
    if len(args) % 2 != 1:
        raise ValueError('lookup requires 2 or an odd number of arguments')
    i = 0
    while i < len(args):
        if i + 1 >= len(args):
            return args[i]
        if re.search(args[i], val, re.I):
            return args[i + 1]
        i += 2
    return ''


def _fn_format_number(val, template):
    if val in ('', 'None'):
        return ''
    if '{' not in template:
        template = '{0:' + template + '}'
    try:
        v1 = float(val)
    except Exception:
        return ''
    try:
        return template.format(v1)
    except Exception:
        pass
    try:
        v2 = trunc(v1)
        if v2 == v1:
            return template.format(v2)
    except Exception:
        pass
    return ''


def _fn_uppercase(val):
    return val.upper()


def _fn_lowercase(val):
    return val.lower()


def _fn_capitalize(val):
    return val.capitalize()


def _fn_titlecase(val):
    return val.title()


# ---------------------------------------------------------------------------
# Function registry: name -> (arg_count, fn, aliases)
#   arg_count: total including val; -1 = variadic; 1 = val only, no extra args
# ---------------------------------------------------------------------------

_REGISTRY = {}


def _reg(name, arg_count, fn, *aliases):
    entry = (arg_count, fn)
    _REGISTRY[name] = entry
    for a in aliases:
        _REGISTRY[a] = entry


_reg('strcmp',              5,  _fn_strcmp)
_reg('strcmpcase',          5,  _fn_strcmpcase)
_reg('cmp',                 5,  _fn_cmp)
_reg('first_matching_cmp', -1,  _fn_first_matching_cmp)
_reg('strcat',             -1,  _fn_strcat)
_reg('strlen',              1,  _fn_strlen)
_reg('add',                -1,  _fn_add)
_reg('subtract',            2,  _fn_subtract)
_reg('multiply',           -1,  _fn_multiply)
_reg('divide',              2,  _fn_divide)
_reg('ceiling',             1,  _fn_ceiling)
_reg('floor',               1,  _fn_floor)
_reg('round',               1,  _fn_round)
_reg('mod',                 2,  _fn_mod)
_reg('fractional_part',     1,  _fn_fractional_part)
_reg('substr',              3,  _fn_substr)
_reg('test',                3,  _fn_test)
_reg('contains',            4,  _fn_contains)
_reg('re',                  3,  _fn_re)
_reg('swap_around_comma',   1,  _fn_swap_around_comma)
_reg('ifempty',             2,  _fn_ifempty)
_reg('select',              2,  _fn_select)
_reg('list_count',          2,  _fn_list_count,         'count')
_reg('list_count_matching', 3,  _fn_list_count_matching, 'count_matching')
_reg('list_item',           3,  _fn_list_item)
_reg('identifier_in_list', -1,  _fn_identifier_in_list)
_reg('str_in_list',        -1,  _fn_str_in_list)
_reg('list_contains',      -1,  _fn_list_contains,      'in_list')
_reg('switch',             -1,  _fn_switch)
_reg('switch_if',          -1,  _fn_switch_if)
_reg('strcat_max',         -1,  _fn_strcat_max)
_reg('shorten',             4,  _fn_shorten)
_reg('sublist',             4,  _fn_sublist)
_reg('subitems',            3,  _fn_subitems)
_reg('lookup',             -1,  _fn_lookup)
_reg('format_number',       2,  _fn_format_number)
_reg('uppercase',           1,  _fn_uppercase)
_reg('lowercase',           1,  _fn_lowercase)
_reg('capitalize',          1,  _fn_capitalize)
_reg('titlecase',           1,  _fn_titlecase)


# ---------------------------------------------------------------------------
# Book field value extraction
# ---------------------------------------------------------------------------

def _book_fields(book, cc_columns):
    identifiers_str = ', '.join(
        sorted(
            ('{0}:{1}'.format(i.type, i.val) for i in (book.identifiers or [])),
            key=str.casefold,
        )
    )
    isbn_val = next((i.val for i in (book.identifiers or []) if i.type == 'isbn'), '')

    fields = {
        'title':         book.title or '',
        'sort':          book.sort or '',
        'title_sort':    book.sort or '',
        'authors':       ' & '.join(a.name for a in book.authors) if book.authors else '',
        'author_sort':   book.author_sort or '',
        'series':        book.series[0].name if book.series else '',
        'series_index':  str(book.series_index) if book.series_index else '',
        'publisher':     book.publishers[0].name if book.publishers else '',
        'publishers':    book.publishers[0].name if book.publishers else '',
        'pubdate':       str(book.pubdate.date()) if book.pubdate else '',
        'timestamp':     str(book.timestamp.date()) if book.timestamp else '',
        'last_modified': str(book.last_modified.date()) if book.last_modified else '',
        'tags':          ', '.join(t.name for t in book.tags) if book.tags else '',
        'languages':     ', '.join(lang.lang_code for lang in book.languages) if book.languages else '',
        'identifiers':   identifiers_str,
        'isbn':          isbn_val,
        'uuid':          book.uuid or '',
        'rating':        (str(book.ratings[0].rating // 2) if book.ratings else ''),
        'comments':      (book.comments[0].text if book.comments else ''),
        'description':   (book.comments[0].text if book.comments else ''),
    }

    for col in cc_columns:
        if col.datatype == 'composite':
            continue
        attr = getattr(book, 'custom_column_' + str(col.id), None)
        if isinstance(attr, list):
            val = str(attr[0].value) if attr and attr[0].value is not None else ''
        elif attr is not None:
            val = str(attr.value) if attr.value is not None else ''
        else:
            val = ''
        fields['#' + col.label] = val

    return fields


# ---------------------------------------------------------------------------
# Formatter
# ---------------------------------------------------------------------------

_format_string_re = re.compile(r'^(.*)\|([^\|]*)\|(.*)$', re.DOTALL)
_compress_spaces = re.compile(r'\s+')


class CalibreTemplateFormatter(string.Formatter):
    """
    Evaluates calibre simple-mode templates against a calibre-web book.

    Ported from calibre's TemplateFormatter / SafeFormat. Handles:
      {field}                   — standard book field
      {field:func(args)}        — field with function applied
      {#label}                  — custom column
      {#label:func(args)}       — custom column with function
      {field|prefix|suffix|}    — conditional prefix/suffix wrapper
    """

    def __init__(self, book, cc_columns):
        super().__init__()
        self._fields = _book_fields(book, cc_columns)

    def get_value(self, key, args, kwargs):
        if not key or not isinstance(key, str):
            return ''
        return self._fields.get(key, self._fields.get(key.lower(), ''))

    def format_field(self, val, fmt):
        if not fmt:
            return val or ''

        # GPM mode: calibre wraps the expression in single quotes
        if len(fmt) >= 2 and fmt[0] == "'" and fmt[-1] == "'":
            return _eval_gpm_expr(fmt[1:-1], self._fields)

        # Handle |prefix|fmt|suffix| conditional wrapper
        m = _format_string_re.match(fmt)
        if m:
            fmt, prefix, suffix = m.groups()
        else:
            prefix = suffix = ''

        p = fmt.find('(')
        if p >= 0 and fmt.endswith(')'):
            colon = fmt[:p].find(':')
            colon = 0 if colon < 0 else colon + 1
            fname = fmt[colon:p].strip()

            entry = _REGISTRY.get(fname)
            if entry:
                arg_count, fn = entry
                if arg_count == 1:
                    # No extra args — just val
                    extra_args = []
                elif arg_count == 2:
                    # One extra arg; don't scan (avoids needing to escape commas)
                    extra_args = [fmt[p + 1:-1]]
                else:
                    extra_args = _parse_args(fmt[p + 1:])
                try:
                    val = fn(val, *extra_args)
                    if not isinstance(val, str):
                        val = str(val) if val is not None else ''
                except Exception as ex:
                    log.warning("Template function %r failed (args=%r): %s", fname, extra_args, ex)
                    val = ''
            elif fname:
                log.warning("Template references unknown function %r", fname)

        if not val:
            return ''
        if prefix or suffix:
            return prefix + val + suffix
        return val

    def safe_format(self, template, column_name=None):
        try:
            ans = self.vformat(template, [], self._fields)
            return _compress_spaces.sub(' ', ans).strip()
        except Exception as ex:
            ctx = ' (column %r)' % column_name if column_name else ''
            log.warning("Composite template evaluation failed%s for template %r: %s", ctx, template, ex)
            return ''


def evaluate_composite_template(template, book, cc_columns, column_name=None):
    fmt = CalibreTemplateFormatter(book, cc_columns)
    result = fmt.safe_format(template, column_name=column_name)
    log.debug(
        "Composite column %r: template=%r identifiers=%r result=%r",
        column_name,
        template,
        fmt._fields.get('identifiers', ''),
        result,
    )
    return result
