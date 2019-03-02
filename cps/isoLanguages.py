#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from iso639 import languages, __version__
    get = languages.get
except ImportError:
    from pycountry import languages as pyc_languages
    try:
        import pkg_resources
        __version__ = pkg_resources.get_distribution('pycountry').version + ' (PyCountry)'
        del pkg_resources
    except:
        __version__ = "? (PyCountry)"

    def _copy_fields(l):
        l.part1 = l.alpha_2
        l.part3 = l.alpha_3
        return l

    def get(name=None, part1=None, part3=None):
        if (part3 is not None):
            return _copy_fields(pyc_languages.get(alpha_3=part3))
        if (part1 is not None):
            return _copy_fields(pyc_languages.get(alpha_2=part1))
        if (name is not None):
            return _copy_fields(pyc_languages.get(name=name))
