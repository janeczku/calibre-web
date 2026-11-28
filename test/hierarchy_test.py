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

"""Unit tests for cps/hierarchy.py (no Flask/DB required).

The module is loaded directly from its file path so the test can run even in
environments where the optional Calibre-Web dependencies (Flask etc.) are not
installed and ``cps/__init__.py`` cannot be imported.
"""

import importlib.util
import os
import unittest

try:
    from cps import hierarchy
except ImportError:  # pragma: no cover - depends on environment
    _spec = importlib.util.spec_from_file_location(
        'hierarchy',
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     os.pardir, 'cps', 'hierarchy.py'))
    hierarchy = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(hierarchy)


class TestParseTagHierarchy(unittest.TestCase):

    def test_basic_tree(self):
        tree = hierarchy.parse_tag_hierarchy(
            ['Computers.DB.Oracle', 'Computers.DB', 'Fiction'])
        self.assertEqual(len(tree), 2)
        computers = tree[0]
        fiction = tree[1]
        # sorted case-insensitively: Computers < Fiction
        self.assertEqual(computers['name'], 'Computers')
        self.assertEqual(fiction['name'], 'Fiction')
        self.assertEqual(computers['path'], 'Computers')
        self.assertEqual(computers['count'], 0)          # no direct hits
        self.assertEqual(computers['total_count'], 2)    # DB + DB.Oracle
        db_node = computers['children'][0]
        self.assertEqual(db_node['name'], 'DB')
        self.assertEqual(db_node['path'], 'Computers.DB')
        self.assertEqual(db_node['count'], 1)
        oracle = db_node['children'][0]
        self.assertEqual(oracle['path'], 'Computers.DB.Oracle')
        self.assertEqual(oracle['children'], [])

    def test_empty_and_blank_values(self):
        self.assertEqual(hierarchy.parse_tag_hierarchy([]), [])
        self.assertEqual(hierarchy.parse_tag_hierarchy(['', None, '   ']), [])

    def test_whitespace_is_stripped(self):
        tree = hierarchy.parse_tag_hierarchy([' A . B '])
        self.assertEqual(tree[0]['name'], 'A')
        self.assertEqual(tree[0]['children'][0]['name'], 'B')

    def test_duplicate_values_aggregate_counts(self):
        tree = hierarchy.parse_tag_hierarchy(['X.Y', 'X.Y', 'X'])
        x = tree[0]
        self.assertEqual(x['count'], 1)
        self.assertEqual(x['total_count'], 3)
        self.assertEqual(x['children'][0]['count'], 2)

    def test_sorting_case_insensitive(self):
        tree = hierarchy.parse_tag_hierarchy(['banana', 'Apple', 'cherry'])
        names = [n['name'] for n in tree]
        self.assertEqual(names, ['Apple', 'banana', 'cherry'])


class TestGetNodeByPath(unittest.TestCase):

    def setUp(self):
        self.tree = hierarchy.parse_tag_hierarchy(
            ['Computers.DB.Oracle', 'Fiction'])

    def test_existing_path(self):
        node = hierarchy.get_node_by_path(self.tree, 'Computers.DB')
        self.assertIsNotNone(node)
        self.assertEqual(node['name'], 'DB')

    def test_root_level(self):
        node = hierarchy.get_node_by_path(self.tree, 'Fiction')
        self.assertIsNotNone(node)

    def test_missing_branch_returns_none(self):
        self.assertIsNone(hierarchy.get_node_by_path(self.tree, 'Computers.Bogus'))
        self.assertIsNone(hierarchy.get_node_by_path(self.tree, 'Bogus'))
        self.assertIsNone(hierarchy.get_node_by_path(self.tree, ''))


class TestBreadcrumbTrail(unittest.TestCase):

    def test_trail(self):
        self.assertEqual(
            hierarchy.breadcrumb_trail('Computers.DB'),
            [('Computers', 'Computers'), ('DB', 'Computers.DB')])

    def test_single_element(self):
        self.assertEqual(hierarchy.breadcrumb_trail('Fiction'),
                         [('Fiction', 'Fiction')])


class TestIsHierarchicalValueSet(unittest.TestCase):

    def test_true_hierarchy_detected(self):
        self.assertTrue(hierarchy.is_hierarchical_value_set(
            ['Computers', 'Computers.DB', 'Computers.DB.Oracle', 'Fiction']))

    def test_dot_but_flat_not_hierarchical(self):
        # Dewey/LCC-style values contain dots but no prefix relations
        self.assertFalse(hierarchy.is_hierarchical_value_set(
            ['778.3', '775', '891.73', 'QA76.76.C68']))

    def test_empty_and_single_values(self):
        self.assertFalse(hierarchy.is_hierarchical_value_set([]))
        self.assertFalse(hierarchy.is_hierarchical_value_set(['Computers']))
        self.assertFalse(hierarchy.is_hierarchical_value_set([None, '']))

    def test_prefix_collision_is_not_hierarchy(self):
        # 'ComputersX' does not make 'Computers' a hierarchy root
        self.assertFalse(hierarchy.is_hierarchical_value_set(
            ['Computers', 'ComputersX']))


class TestLikeEscaping(unittest.TestCase):

    def test_escape_like_wildcards(self):
        self.assertEqual(hierarchy.escape_like('100%'), r'100\%')
        self.assertEqual(hierarchy.escape_like('a_b'), r'a\_b')
        self.assertEqual(hierarchy.escape_like(r'a\b'), r'a\\b')

    def test_like_pattern_guards_prefix_collisions(self):
        # '.' is not a LIKE wildcard, so no escaping required; the trailing
        # dot guards against 'ComputersX' matching prefix 'Computers'.
        pattern = hierarchy.like_pattern('Computers')
        self.assertEqual(pattern, 'Computers.%')
        self.assertNotEqual(pattern, 'ComputersX%')

    def test_like_pattern_escapes_wildcards_in_path(self):
        # A node literally named '100%' must not match '1000...'
        self.assertEqual(hierarchy.like_pattern('100%'), r'100\%.%')


if __name__ == '__main__':
    unittest.main()
