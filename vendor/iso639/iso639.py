# coding=utf-8
"""
Python library for ISO 639 standard

Copyright (c) 2014-2016 Mikael Karlsson (CSC - IT Center for Science Ltd.).
Licensed under AGPLv3.
"""

# Fix for Python 3.0 - 3.2
if not __package__:
    __package__ = __name__.split('.')[0]


def _fabtabular():
    """
    This function retrieves the ISO 639 and inverted names datasets as tsv files and returns them as lists.
    """
    import csv
    import sys
    from pkg_resources import resource_filename

    data = resource_filename(__package__, 'iso-639-3.tab')
    inverted = resource_filename(__package__, 'iso-639-3_Name_Index.tab')
    macro = resource_filename(__package__, 'iso-639-3-macrolanguages.tab')
    part5 = resource_filename(__package__, 'iso639-5.tsv')
    part2 = resource_filename(__package__, 'iso639-2.tsv')
    part1 = resource_filename(__package__, 'iso639-1.tsv')

    # if sys.version_info[0] == 2:
    #     from urllib2 import urlopen
    #     from contextlib import closing
    #     data_fo = closing(urlopen('http://www-01.sil.org/iso639-3/iso-639-3.tab'))
    #     inverted_fo = closing(urlopen('http://www-01.sil.org/iso639-3/iso-639-3_Name_Index.tab'))
    # else:
    #     from urllib.request import urlopen
    #     import io
    #     data_fo = io.StringIO(urlopen('http://www-01.sil.org/iso639-3/iso-639-3.tab').read().decode())
    #     inverted_fo = io.StringIO(urlopen('http://www-01.sil.org/iso639-3/iso-639-3_Name_Index.tab').read().decode())

    if sys.version_info[0] == 3:
        from functools import partial

        global open
        open = partial(open, encoding='utf-8')

    data_fo = open(data)
    inverted_fo = open(inverted)
    macro_fo = open(macro)
    part5_fo = open(part5)
    part2_fo = open(part2)
    part1_fo = open(part1)
    with data_fo as u:
        with inverted_fo as i:
            with macro_fo as m:
                with part5_fo as p5:
                    with part2_fo as p2:
                        with part1_fo as p1:
                            return (list(csv.reader(u, delimiter='\t'))[1:],
                                    list(csv.reader(i, delimiter='\t'))[1:],
                                    list(csv.reader(m, delimiter='\t'))[1:],
                                    list(csv.reader(p5, delimiter='\t'))[1:],
                                    list(csv.reader(p2, delimiter='\t'))[1:],
                                    list(csv.reader(p1, delimiter='\t'))[1:])


class _Language(object):
    """
    This class represents a language. It provides pycountry language class compatibility.
    """

    def __init__(self, part3, part2b, part2t, part1, name, inverted, macro, names, part5):
        self.part3 = part3
        self.part2b = part2b
        self.part2t = part2t
        self.part1 = part1
        self.name = name
        self.inverted = inverted
        self.macro = macro
        self.names = names
        self.part5 = part5

    def __getattr__(self, item):
        compat = {
            'alpha2': self.part1,
            'bibliographic': self.part2b,
            'terminology': self.part2t,
        }
        if item not in compat:
            raise AttributeError("'{o}' object has no attribute '{a}'".format(o=type(self).__name__, a=item))
        return compat[item]


class lazy_property(object):
    """
    Implements a lazy property decorator, that overwrites itself/property with value
    """

    def __init__(self, f):
        self.f = f
        self.name = f.__name__

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        val = self.f(instance)
        setattr(instance, self.name, val)
        return val


class Iso639(object):
    """
    This class is a close to drop-in replacement for pycountry.languages.
    But unlike pycountry.languages it also supports ISO 639-3.

    It implements the Singleton design pattern for performance reasons.
    Is uses lazy properties for faster import time.
    """

    def __new__(cls):
        if not hasattr(cls, '__instance'):
            setattr(cls, '__instance', super(cls, cls).__new__(cls))
        return getattr(cls, '__instance')

    def __len__(self):
        return len(self.languages)

    def __iter__(self):
        return iter(self.languages)

    def __getattr__(self, item):
        compat = {
            'alpha2': self.part1,
            'bibliographic': self.part2b,
            'terminology': self.part2t,
        }
        if item not in compat:
            raise AttributeError("'{o}' object has no attribute '{a}'".format(o=type(self).__name__, a=item))
        return compat[item]

    @lazy_property
    def languages(self):
        def generate():
            # All of part3 and matching part2
            for a, b, c, d, _, _, e, _ in l:
                inv = alt[a].pop(e)
                yield _Language(a, b, c,
                                d if d in p1c else '',  # Fixes 'sh'
                                e, inv,
                                m.get(a, [''])[0],
                                list(alt[a].items()),
                                '')
                p2.pop(b, None)
                p2.pop(c, None)

            # All of part5 and matching part2
            for _, a, b, _ in p5:
                yield _Language('',
                                a if a in p2 else '',
                                a if a in p2 else '',
                                p1n.get(b, ['', ''])[1],
                                b, '', '', '', a)
                p2.pop(a, None)

            # Rest of part2
            p2.pop('qaa-qtz', None)  # Is not a real code, but a range
            for _, a, b, _ in p2.values():
                n = [x.strip() for x in b.split('|')]
                yield _Language('', a, a,
                                p1n.get(b, ['', ''])[1],
                                n[0], '', '', zip(n[1:], n[1:]), '')

        import collections

        l, i, m, p5, p2, p1 = _fabtabular()
        alt = collections.defaultdict(dict)
        for x in i:
            alt[x[0]][x[1]] = x[2]
        m = dict((x[1], x) for x in m)
        p2 = dict((x[1], x) for x in p2)
        p1c = dict((x[1], x) for x in p1)
        p1n = dict((x[2].split('|')[0].strip(), x) for x in p1)
        return list(generate())

    @lazy_property
    def part3(self):
        return dict((x.part3, x) for x in self.languages if x.part3)

    @lazy_property
    def part2b(self):
        return dict((x.part2b, x) for x in self.languages if x.part2b)

    @lazy_property
    def part2t(self):
        return dict((x.part2t, x) for x in self.languages if x.part2t)

    @lazy_property
    def part1(self):
        return dict((x.part1, x) for x in self.languages if x.part1)

    @lazy_property
    def part5(self):
        return dict((x.part5, x) for x in self.languages if x.part5)

    @lazy_property
    def name(self):
        def gen():
            for x in self.languages:
                if x.name:
                    yield x.name, x
                for n in x.names:
                    yield n[0], x

        return dict(gen())

    @lazy_property
    def inverted(self):
        return dict((x.inverted, x) for x in self.languages if x.inverted)

    @lazy_property
    def macro(self):
        import collections

        m = collections.defaultdict(list)
        for x in self.languages:
            if x.macro:
                m[x.macro].append(x)
        return dict(m)

    @lazy_property
    def retired(self):
        """
        Function for generating retired languages. Returns a dict('code', (datetime, [language, ...], 'description')).
        """

        def gen():
            import csv
            import re
            from datetime import datetime
            from pkg_resources import resource_filename

            with open(resource_filename(__package__, 'iso-639-3_Retirements.tab')) as rf:
                rtd = list(csv.reader(rf, delimiter='\t'))[1:]
                rc = [r[0] for r in rtd]
                for i, _, _, m, s, d in rtd:
                    d = datetime.strptime(d, '%Y-%m-%d')
                    if not m:
                        m = re.findall('\[([a-z]{3})\]', s)
                    if m:
                        m = [m] if isinstance(m, str) else m
                        yield i, (d, [self.get(part3=x) for x in m if x not in rc], s)
                    else:
                        yield i, (d, [], s)

            yield 'sh', self.get(part3='hbs')  # Add 'sh' as deprecated

        return dict(gen())

    def get(self, **kwargs):
        """
        Simple getter function for languages. Takes 1 keyword/value and returns 1 language object.
        """
        if not len(kwargs) == 1:
            raise AttributeError('Only one keyword expected')
        key, value = kwargs.popitem()
        return getattr(self, key)[value]
