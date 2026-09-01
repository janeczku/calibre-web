# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2024 Calibre-Web contributors
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

"""Render tests for the hierarchy Jinja macros.

Guards the `breadcrumbs` data shape contract: the macro expects a *list of
trails*, where each trail is a list of (name, path) tuples. Regression test
for the "too many values to unpack" 500 errors.
"""

import os
import unittest

from jinja2 import Environment, FileSystemLoader

TEMPLATE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir)
# Forward slashes are mandatory: Jinja treats "\t" in a template name as a tab
MACROS = 'cps/themes/standard/templates/macros/hierarchy.html'


def fake_url_for(endpoint, **kwargs):
    parts = [endpoint] + ['%s=%s' % (k, v) for k, v in sorted(kwargs.items())]
    return '/' + '/'.join(parts)


def render_breadcrumbs(trails, col_id=1):
    env = Environment(loader=FileSystemLoader(TEMPLATE_ROOT))
    env.globals['url_for'] = fake_url_for
    tpl = env.from_string(
        "{%% from '%s' import hierarchy_breadcrumbs %%}"
        "{{ hierarchy_breadcrumbs(breadcrumbs, col_id) }}" % MACROS)
    return tpl.render(breadcrumbs=trails, col_id=col_id)


class TestBreadcrumbMacro(unittest.TestCase):

    def test_single_trail_wrapped_in_list(self):
        """Shape used by web.render_cc_category(): [[...one trail...]]"""
        html = render_breadcrumbs([[('Genre', ''), ('Computers', 'Computers')]])
        self.assertEqual(html.count('<nav'), 1)
        self.assertIn('>Genre</a>', html)
        self.assertIn('>Computers</a>', html)
        # root crumb links to the column root (category_path='')
        self.assertIn('category_path=', html)

    def test_multiple_trails(self):
        """Shape used for books with several hierarchical values."""
        trails = [
            [('Genre', ''), ('Computers', 'Computers')],
            [('Genre', ''), ('Fiction', 'Fiction')],
        ]
        html = render_breadcrumbs(trails)
        self.assertEqual(html.count('<nav'), 2)

    def test_bare_pairs_degrade_gracefully(self):
        """A bare list of (name, path) pairs (wrong shape) must not raise;
        the macro degrades to rendering each pair as a single-crumb trail."""
        html = render_breadcrumbs([('Genre', ''), ('Computers', 'Computers')])
        self.assertIn('>Genre</a>', html)
        self.assertIn('>Computers</a>', html)


if __name__ == '__main__':
    unittest.main()
