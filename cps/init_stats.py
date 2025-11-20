#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script to initialize statistics cache
Can be run as a standalone script or imported
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def init_stats():
    """Initialize statistics cache"""
    try:
        print("Initializing statistics cache...")

        # Import after path is set
        from cps import admin_stats

        # Force update of stats cache
        result = admin_stats.update_stats_cache()

        if result:
            print("✓ Statistics cache initialized successfully")
            return 0
        else:
            print("⚠ Statistics cache initialization had warnings")
            return 1

    except Exception as e:
        print(f"✗ Error initializing statistics: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(init_stats())
