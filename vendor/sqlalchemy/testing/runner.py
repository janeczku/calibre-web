#!/usr/bin/env python
"""
Nose test runner module.

This script is a front-end to "nosetests" which
installs SQLAlchemy's testing plugin into the local environment.

The script is intended to be used by third-party dialects and extensions
that run within SQLAlchemy's testing framework.    The runner can
be invoked via::

    python -m sqlalchemy.testing.runner

The script is then essentially the same as the "nosetests" script, including
all of the usual Nose options.   The test environment requires that a
setup.cfg is locally present including various required options.

Note that when using this runner, Nose's "coverage" plugin will not be
able to provide coverage for SQLAlchemy itself, since SQLAlchemy is
imported into sys.modules before coverage is started.   The special
script sqla_nose.py is provided as a top-level script which loads the
plugin in a special (somewhat hacky) way so that coverage against
SQLAlchemy itself is possible.

"""

from sqlalchemy.testing.plugin.noseplugin import NoseSQLAlchemy

import nose


def main():
    nose.main(addplugins=[NoseSQLAlchemy()])

def setup_py_test():
    """Runner to use for the 'test_suite' entry of your setup.py.

    Prevents any name clash shenanigans from the command line
    argument "test" that the "setup.py test" command sends
    to nose.

    """
    nose.main(addplugins=[NoseSQLAlchemy()], argv=['runner'])
