#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to update STABLE_VERSION in constants.py
Can be called from Dockerfile or CI/CD
"""

import sys
import re
import os

def update_version(version):
    """Update STABLE_VERSION in constants.py"""
    constants_file = os.path.join(os.path.dirname(__file__), 'cps', 'constants.py')

    if not os.path.exists(constants_file):
        print(f"Error: {constants_file} not found")
        return False

    with open(constants_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Update STABLE_VERSION
    pattern = r"STABLE_VERSION\s*=\s*['\"][\d\.]+['\"]"
    replacement = f"STABLE_VERSION =  '{version}'"

    new_content = re.sub(pattern, replacement, content)

    if new_content == content:
        print(f"Warning: STABLE_VERSION not found or already set to {version}")
        return False

    with open(constants_file, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"✓ Updated STABLE_VERSION to {version}")
    return True

if __name__ == '__main__':
    if len(sys.argv) > 1:
        version = sys.argv[1]
    else:
        version = '0.14.0'  # Default version

    success = update_version(version)
    sys.exit(0 if success else 1)
