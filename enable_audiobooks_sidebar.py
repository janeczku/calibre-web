#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script to enable Audiobooks sidebar for all existing users
Run this once after upgrading to the version with audiobooks feature
"""

import os
import sys

# Add the calibre-web directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cps import constants, ub

def enable_audiobooks_sidebar():
    """Enable the audiobooks sidebar option for all users"""
    print("Enabling Audiobooks sidebar for all users...")

    try:
        # Get all users
        users = ub.session.query(ub.User).all()

        updated_count = 0
        for user in users:
            # Check if user already has audiobooks enabled
            if not constants.has_flag(user.sidebar_view, constants.SIDEBAR_AUDIOBOOKS):
                # Add the audiobooks flag
                user.sidebar_view = user.sidebar_view | constants.SIDEBAR_AUDIOBOOKS
                updated_count += 1
                print(f"  ✓ Enabled for user: {user.name}")
            else:
                print(f"  - Already enabled for user: {user.name}")

        # Commit changes
        if updated_count > 0:
            ub.session.commit()
            print(f"\n✓ Successfully enabled Audiobooks sidebar for {updated_count} user(s)")
        else:
            print("\n✓ All users already have Audiobooks sidebar enabled")

        return True

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        ub.session.rollback()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Audiobooks Sidebar Migration Script")
    print("=" * 60)
    print()

    success = enable_audiobooks_sidebar()

    print()
    print("=" * 60)
    if success:
        print("Migration completed successfully!")
        print("Please restart Calibre-Web to see the changes.")
    else:
        print("Migration failed. Please check the error above.")
    print("=" * 60)

    sys.exit(0 if success else 1)
