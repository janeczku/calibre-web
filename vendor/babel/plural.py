# -*- coding: utf-8 -*-
"""
    babel.numbers
    ~~~~~~~~~~~~~

    CLDR Plural support.  See UTS #35.

    :copyright: (c) 2013 by the Babel Team.
    :license: BSD, see LICENSE for more details.
"""

import re


_plural_tags = ('zero', 'one', 'two', 'few', 'many', 'other')
_fallback_tag = 'other'


class PluralRule(object):
    """Represents a set of language pluralization rules.  The constructor
    accepts a list of (tag, expr) tuples or a dict of CLDR rules. The
    resulting object is callable and accepts one parameter with a positive or
    negative number (both integer and float) for the number that indicates the
    plural form for a string and returns the tag for the format:

    >>> rule = PluralRule({'one': 'n is 1'})
    >>> rule(1)
    'one'
    >>> rule(2)
    'other'

    Currently the CLDR defines these tags: zero, one, two, few, many and
    other where other is an implicit default.  Rules should be mutually
    exclusive; for a given numeric value, only one rule should apply (i.e.
    the condition should only be true for one of the plural rule elements.
    """

    __slots__ = ('abstract', '_func')

    def __init__(self, rules):
        """Initialize the rule instance.

        :param rules: a list of ``(tag, expr)``) tuples with the rules
                      conforming to UTS #35 or a dict with the tags as keys
                      and expressions as values.
        :raise RuleError: if the expression is malformed
        """
        if isinstance(rules, dict):
            rules = rules.items()
        found = set()
        self.abstract = []
        for key, expr in sorted(list(rules)):
            if key not in _plural_tags:
                raise ValueError('unknown tag %r' % key)
            elif key in found:
                raise ValueError('tag %r defined twice' % key)
            found.add(key)
            self.abstract.append((key, _Parser(expr).ast))

    def __repr__(self):
        rules = self.rules
        return '<%s %r>' % (
            type(self).__name__,
            ', '.join(['%s: %s' % (tag, rules[tag]) for tag in _plural_tags
                       if tag in rules])
        )

    @classmethod
    def parse(cls, rules):
        """Create a `PluralRule` instance for the given rules.  If the rules
        are a `PluralRule` object, that object is returned.

        :param rules: the rules as list or dict, or a `PluralRule` object
        :raise RuleError: if the expression is malformed
        """
        if isinstance(rules, cls):
            return rules
        return cls(rules)

    @property
    def rules(self):
        """The `PluralRule` as a dict of unicode plural rules.

        >>> rule = PluralRule({'one': 'n is 1'})
        >>> rule.rules
        {'one': 'n is 1'}
        """
        _compile = _UnicodeCompiler().compile
        return dict([(tag, _compile(ast)) for tag, ast in self.abstract])

    tags = property(lambda x: frozenset([i[0] for i in x.abstract]), doc="""
        A set of explicitly defined tags in this rule.  The implicit default
        ``'other'`` rules is not part of this set unless there is an explicit
        rule for it.""")

    def __getstate__(self):
        return self.abstract

    def __setstate__(self, abstract):
        self.abstract = abstract

    def __call__(self, n):
        if not hasattr(self, '_func'):
            self._func = to_python(self)
        return self._func(n)


def to_javascript(rule):
    """Convert a list/dict of rules or a `PluralRule` object into a JavaScript
    function.  This function depends on no external library:

    >>> to_javascript({'one': 'n is 1'})
    "(function(n) { return (n == 1) ? 'one' : 'other'; })"

    Implementation detail: The function generated will probably evaluate
    expressions involved into range operations multiple times.  This has the
    advantage that external helper functions are not required and is not a
    big performance hit for these simple calculations.

    :param rule: the rules as list or dict, or a `PluralRule` object
    :raise RuleError: if the expression is malformed
    """
    to_js = _JavaScriptCompiler().compile
    result = ['(function(n) { return ']
    for tag, ast in PluralRule.parse(rule).abstract:
        result.append('%s ? %r : ' % (to_js(ast), tag))
    result.append('%r; })' % _fallback_tag)
    return ''.join(result)


def to_python(rule):
    """Convert a list/dict of rules or a `PluralRule` object into a regular
    Python function.  This is useful in situations where you need a real
    function and don't are about the actual rule object:

    >>> func = to_python({'one': 'n is 1', 'few': 'n in 2..4'})
    >>> func(1)
    'one'
    >>> func(3)
    'few'
    >>> func = to_python({'one': 'n in 1,11', 'few': 'n in 3..10,13..19'})
    >>> func(11)
    'one'
    >>> func(15)
    'few'

    :param rule: the rules as list or dict, or a `PluralRule` object
    :raise RuleError: if the expression is malformed
    """
    namespace = {
        'IN':       in_range_list,
        'WITHIN':   within_range_list,
        'MOD':      cldr_modulo
    }
    to_python = _PythonCompiler().compile
    result = ['def evaluate(n):']
    for tag, ast in PluralRule.parse(rule).abstract:
        # the str() call is to coerce the tag to the native string.  It's
        # a limited ascii restricted set of tags anyways so that is fine.
        result.append(' if (%s): return %r' % (to_python(ast), str(tag)))
    result.append(' return %r' % _fallback_tag)
    code = compile('\n'.join(result), '<rule>', 'exec')
    eval(code, namespace)
    return namespace['evaluate']


def to_gettext(rule):
    """The plural rule as gettext expression.  The gettext expression is
    technically limited to integers and returns indices rather than tags.

    >>> to_gettext({'one': 'n is 1', 'two': 'n is 2'})
    'nplurals=3; plural=((n == 1) ? 0 : (n == 2) ? 1 : 2)'

    :param rule: the rules as list or dict, or a `PluralRule` object
    :raise RuleError: if the expression is malformed
    """
    rule = PluralRule.parse(rule)

    used_tags = rule.tags | set([_fallback_tag])
    _compile = _GettextCompiler().compile
    _get_index = [tag for tag in _plural_tags if tag in used_tags].index

    result = ['nplurals=%d; plural=(' % len(used_tags)]
    for tag, ast in rule.abstract:
        result.append('%s ? %d : ' % (_compile(ast), _get_index(tag)))
    result.append('%d)' % _get_index(_fallback_tag))
    return ''.join(result)


def in_range_list(num, range_list):
    """Integer range list test.  This is the callback for the "in" operator
    of the UTS #35 pluralization rule language:

    >>> in_range_list(1, [(1, 3)])
    True
    >>> in_range_list(3, [(1, 3)])
    True
    >>> in_range_list(3, [(1, 3), (5, 8)])
    True
    >>> in_range_list(1.2, [(1, 4)])
    False
    >>> in_range_list(10, [(1, 4)])
    False
    >>> in_range_list(10, [(1, 4), (6, 8)])
    False
    """
    return num == int(num) and within_range_list(num, range_list)


def within_range_list(num, range_list):
    """Float range test.  This is the callback for the "within" operator
    of the UTS #35 pluralization rule language:

    >>> within_range_list(1, [(1, 3)])
    True
    >>> within_range_list(1.0, [(1, 3)])
    True
    >>> within_range_list(1.2, [(1, 4)])
    True
    >>> within_range_list(8.8, [(1, 4), (7, 15)])
    True
    >>> within_range_list(10, [(1, 4)])
    False
    >>> within_range_list(10.5, [(1, 4), (20, 30)])
    False
    """
    return any(num >= min_ and num <= max_ for min_, max_ in range_list)


def cldr_modulo(a, b):
    """Javaish modulo.  This modulo operator returns the value with the sign
    of the dividend rather than the divisor like Python does:

    >>> cldr_modulo(-3, 5)
    -3
    >>> cldr_modulo(-3, -5)
    -3
    >>> cldr_modulo(3, 5)
    3
    """
    reverse = 0
    if a < 0:
        a *= -1
        reverse = 1
    if b < 0:
        b *= -1
    rv = a % b
    if reverse:
        rv *= -1
    return rv


class RuleError(Exception):
    """Raised if a rule is malformed."""


class _Parser(object):
    """Internal parser.  This class can translate a single rule into an abstract
    tree of tuples. It implements the following grammar::

        condition     = and_condition ('or' and_condition)*
        and_condition = relation ('and' relation)*
        relation      = is_relation | in_relation | within_relation | 'n' <EOL>
        is_relation   = expr 'is' ('not')? value
        in_relation   = expr ('not')? 'in' range_list
        within_relation = expr ('not')? 'within' range_list
        expr          = 'n' ('mod' value)?
        range_list    = (range | value) (',' range_list)*
        value         = digit+
        digit         = 0|1|2|3|4|5|6|7|8|9
        range         = value'..'value

    - Whitespace can occur between or around any of the above tokens.
    - Rules should be mutually exclusive; for a given numeric value, only one
      rule should apply (i.e. the condition should only be true for one of
      the plural rule elements).
    - The in and within relations can take comma-separated lists, such as:
      'n in 3,5,7..15'.

    The translator parses the expression on instanciation into an attribute
    called `ast`.
    """

    _rules = [
        (None, re.compile(r'\s+(?u)')),
        ('word', re.compile(r'\b(and|or|is|(?:with)?in|not|mod|n)\b')),
        ('value', re.compile(r'\d+')),
        ('comma', re.compile(r',')),
        ('ellipsis', re.compile(r'\.\.'))
    ]

    def __init__(self, string):
        string = string.lower()
        result = []
        pos = 0
        end = len(string)
        while pos < end:
            for tok, rule in self._rules:
                match = rule.match(string, pos)
                if match is not None:
                    pos = match.end()
                    if tok:
                        result.append((tok, match.group()))
                    break
            else:
                raise RuleError('malformed CLDR pluralization rule.  '
                                'Got unexpected %r' % string[pos])
        self.tokens = result[::-1]

        self.ast = self.condition()
        if self.tokens:
            raise RuleError('Expected end of rule, got %r' %
                            self.tokens[-1][1])

    def test(self, type, value=None):
        return self.tokens and self.tokens[-1][0] == type and \
               (value is None or self.tokens[-1][1] == value)

    def skip(self, type, value=None):
        if self.test(type, value):
            return self.tokens.pop()

    def expect(self, type, value=None, term=None):
        token = self.skip(type, value)
        if token is not None:
            return token
        if term is None:
            term = repr(value is None and type or value)
        if not self.tokens:
            raise RuleError('expected %s but end of rule reached' % term)
        raise RuleError('expected %s but got %r' % (term, self.tokens[-1][1]))

    def condition(self):
        op = self.and_condition()
        while self.skip('word', 'or'):
            op = 'or', (op, self.and_condition())
        return op

    def and_condition(self):
        op = self.relation()
        while self.skip('word', 'and'):
            op = 'and', (op, self.relation())
        return op

    def relation(self):
        left = self.expr()
        if self.skip('word', 'is'):
            return self.skip('word', 'not') and 'isnot' or 'is', \
                   (left, self.value())
        negated = self.skip('word', 'not')
        method = 'in'
        if self.skip('word', 'within'):
            method = 'within'
        else:
            self.expect('word', 'in', term="'within' or 'in'")
        rv = 'relation', (method, left, self.range_list())
        if negated:
            rv = 'not', (rv,)
        return rv

    def range_or_value(self):
        left = self.value()
        if self.skip('ellipsis'):
            return((left, self.value()))
        else:
            return((left, left))

    def range_list(self):
        range_list = [self.range_or_value()]
        while self.skip('comma'):
            range_list.append(self.range_or_value())
        return 'range_list', range_list

    def expr(self):
        self.expect('word', 'n')
        if self.skip('word', 'mod'):
            return 'mod', (('n', ()), self.value())
        return 'n', ()

    def value(self):
        return 'value', (int(self.expect('value')[1]),)


def _binary_compiler(tmpl):
    """Compiler factory for the `_Compiler`."""
    return lambda self, l, r: tmpl % (self.compile(l), self.compile(r))


def _unary_compiler(tmpl):
    """Compiler factory for the `_Compiler`."""
    return lambda self, x: tmpl % self.compile(x)


class _Compiler(object):
    """The compilers are able to transform the expressions into multiple
    output formats.
    """

    def compile(self, arg):
        op, args = arg
        return getattr(self, 'compile_' + op)(*args)

    compile_n = lambda x: 'n'
    compile_value = lambda x, v: str(v)
    compile_and = _binary_compiler('(%s && %s)')
    compile_or = _binary_compiler('(%s || %s)')
    compile_not = _unary_compiler('(!%s)')
    compile_mod = _binary_compiler('(%s %% %s)')
    compile_is = _binary_compiler('(%s == %s)')
    compile_isnot = _binary_compiler('(%s != %s)')

    def compile_relation(self, method, expr, range_list):
        raise NotImplementedError()


class _PythonCompiler(_Compiler):
    """Compiles an expression to Python."""

    compile_and = _binary_compiler('(%s and %s)')
    compile_or = _binary_compiler('(%s or %s)')
    compile_not = _unary_compiler('(not %s)')
    compile_mod = _binary_compiler('MOD(%s, %s)')

    def compile_relation(self, method, expr, range_list):
        compile_range_list = '[%s]' % ','.join(
            ['(%s, %s)' % tuple(map(self.compile, range_))
             for range_ in range_list[1]])
        return '%s(%s, %s)' % (method.upper(), self.compile(expr),
                               compile_range_list)


class _GettextCompiler(_Compiler):
    """Compile into a gettext plural expression."""

    def compile_relation(self, method, expr, range_list):
        rv = []
        expr = self.compile(expr)
        for item in range_list[1]:
            if item[0] == item[1]:
                rv.append('(%s == %s)' % (
                    expr,
                    self.compile(item[0])
                ))
            else:
                min, max = map(self.compile, item)
                rv.append('(%s >= %s && %s <= %s)' % (
                    expr,
                    min,
                    expr,
                    max
                ))
        return '(%s)' % ' || '.join(rv)


class _JavaScriptCompiler(_GettextCompiler):
    """Compiles the expression to plain of JavaScript."""

    def compile_relation(self, method, expr, range_list):
        code = _GettextCompiler.compile_relation(
            self, method, expr, range_list)
        if method == 'in':
            expr = self.compile(expr)
            code = '(parseInt(%s) == %s && %s)' % (expr, expr, code)
        return code


class _UnicodeCompiler(_Compiler):
    """Returns a unicode pluralization rule again."""

    compile_is = _binary_compiler('%s is %s')
    compile_isnot = _binary_compiler('%s is not %s')
    compile_and = _binary_compiler('%s and %s')
    compile_or = _binary_compiler('%s or %s')
    compile_mod = _binary_compiler('%s mod %s')

    def compile_not(self, relation):
        return self.compile_relation(negated=True, *relation[1])

    def compile_relation(self, method, expr, range_list, negated=False):
        ranges = []
        for item in range_list[1]:
            if item[0] == item[1]:
                ranges.append(self.compile(item[0]))
            else:
                ranges.append('%s..%s' % tuple(map(self.compile, item)))
        return '%s%s %s %s' % (
            self.compile(expr), negated and ' not' or '',
            method, ','.join(ranges)
        )
