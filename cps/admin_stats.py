# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2025
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

"""
Module for calculating and displaying admin statistics and KPIs
With caching and automatic updates
"""

import json
import os
from datetime import datetime, timedelta
from sqlalchemy import func, extract, and_
from sqlalchemy.sql import text

from . import db, ub, calibre_db, logger, config

log = logger.create()

# Cache configuration
CACHE_FILE = 'admin_stats_cache.json'
CACHE_DURATION_MINUTES = 15  # Update stats every 15 minutes


def get_cache_path():
    """Get the path to the cache file"""
    cache_dir = config.config_calibre_dir or os.getcwd()
    return os.path.join(cache_dir, CACHE_FILE)


def load_cached_stats():
    """Load statistics from cache file"""
    try:
        cache_path = get_cache_path()
        if not os.path.exists(cache_path):
            return None

        with open(cache_path, 'r', encoding='utf-8') as f:
            cached_data = json.load(f)

        # Check if cache is still valid
        cache_time = datetime.fromisoformat(cached_data.get('generated_at_iso', '2000-01-01'))
        age_minutes = (datetime.now() - cache_time).total_seconds() / 60

        if age_minutes < CACHE_DURATION_MINUTES:
            log.debug(f"Using cached stats (age: {age_minutes:.1f} minutes)")
            return cached_data
        else:
            log.debug(f"Cache expired (age: {age_minutes:.1f} minutes)")
            return None

    except Exception as e:
        log.error(f"Error loading cached stats: {e}")
        return None


def save_cached_stats(stats):
    """Save statistics to cache file"""
    try:
        cache_path = get_cache_path()

        # Add ISO timestamp for easier parsing
        stats['generated_at_iso'] = datetime.now().isoformat()

        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)

        log.debug(f"Stats cached to {cache_path}")
        return True

    except Exception as e:
        log.error(f"Error saving cached stats: {e}")
        return False


def get_library_stats():
    """Get basic library statistics"""
    try:
        stats = {
            'total_books': calibre_db.session.query(db.Books).count(),
            'total_authors': calibre_db.session.query(db.Authors).count(),
            'total_publishers': calibre_db.session.query(db.Publishers).count(),
            'total_series': calibre_db.session.query(db.Series).count(),
            'total_tags': calibre_db.session.query(db.Tags).count(),
            'total_languages': calibre_db.session.query(db.Languages).count(),
        }

        # Get total file size
        total_size = calibre_db.session.query(
            func.sum(db.Data.uncompressed_size)
        ).scalar() or 0

        stats['total_size_mb'] = round(total_size / (1024 * 1024), 2)
        stats['total_size_gb'] = round(total_size / (1024 * 1024 * 1024), 2)

        # Get format distribution
        formats = calibre_db.session.query(
            db.Data.format,
            func.count(db.Data.format).label('count')
        ).group_by(db.Data.format).order_by(text('count DESC')).limit(10).all()

        stats['top_formats'] = [{'format': f.format, 'count': f.count} for f in formats]

        return stats
    except Exception as e:
        log.error(f"Error getting library stats: {e}")
        return {}


def get_user_stats():
    """Get user statistics"""
    try:
        total_users = ub.session.query(ub.User).count()

        stats = {
            'total_users': total_users,
            'active_users_week': 0,
            'active_users_month': 0,
        }

        # Get active users based on downloads
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        # Count active users based on sessions
        now_timestamp = int(datetime.now().timestamp())
        week_ago_timestamp = int((datetime.now() - timedelta(days=7)).timestamp())
        month_ago_timestamp = int((datetime.now() - timedelta(days=30)).timestamp())

        # Users with active sessions in the last week
        active_week = ub.session.query(
            func.count(func.distinct(ub.User_Sessions.user_id))
        ).filter(ub.User_Sessions.expiry >= week_ago_timestamp).scalar() or 0

        # Users with active sessions in the last month
        active_month = ub.session.query(
            func.count(func.distinct(ub.User_Sessions.user_id))
        ).filter(ub.User_Sessions.expiry >= month_ago_timestamp).scalar() or 0

        stats['active_users_week'] = active_week
        stats['active_users_month'] = active_month

        # Get list of active users this week with their last activity
        active_users_list = ub.session.query(
            ub.User.name,
            func.max(ub.User_Sessions.expiry).label('last_activity')
        ).join(
            ub.User_Sessions, ub.User.id == ub.User_Sessions.user_id
        ).filter(
            ub.User_Sessions.expiry >= week_ago_timestamp
        ).group_by(ub.User.name).order_by(text('last_activity DESC')).all()

        stats['active_users_list'] = [
            {
                'name': user[0],
                'last_activity': datetime.fromtimestamp(user[1]).strftime('%Y-%m-%d %H:%M:%S') if user[1] else 'Unknown'
            }
            for user in active_users_list
        ]

        return stats
    except Exception as e:
        log.error(f"Error getting user stats: {e}")
        return {}


def get_download_stats():
    """Get download statistics"""
    try:
        stats = {
            'total_downloads': ub.session.query(ub.Downloads).count(),
            'downloads_week': 0,
            'downloads_month': 0,
            'downloads_year': 0,
        }

        # Get most downloaded books
        most_downloaded = ub.session.query(
            ub.Downloads.book_id,
            func.count(ub.Downloads.id).label('download_count')
        ).group_by(ub.Downloads.book_id).order_by(text('download_count DESC')).limit(10).all()

        stats['most_downloaded'] = []
        for book_id, count in most_downloaded:
            try:
                book = calibre_db.get_book(book_id)
                if book:
                    stats['most_downloaded'].append({
                        'book_id': book_id,
                        'title': book.title,
                        'author': book.authors[0].name if book.authors else 'Unknown',
                        'downloads': count
                    })
            except Exception as e:
                log.debug(f"Error getting book {book_id}: {e}")
                continue

        # Get most active users (by downloads)
        most_active_users = ub.session.query(
            ub.Downloads.user_id,
            func.count(ub.Downloads.id).label('download_count')
        ).group_by(ub.Downloads.user_id).order_by(text('download_count DESC')).limit(10).all()

        stats['most_active_users'] = []
        for user_id, count in most_active_users:
            try:
                user = ub.session.query(ub.User).filter(ub.User.id == user_id).first()
                if user:
                    stats['most_active_users'].append({
                        'user_id': user_id,
                        'username': user.name,
                        'downloads': count
                    })
            except Exception as e:
                log.debug(f"Error getting user {user_id}: {e}")
                continue

        return stats
    except Exception as e:
        log.error(f"Error getting download stats: {e}")
        return {}


def get_reading_stats():
    """Get reading statistics"""
    try:
        stats = {
            'total_read_books': ub.session.query(ub.ReadBook).filter(
                ub.ReadBook.read_status == ub.ReadBook.STATUS_FINISHED
            ).count(),
            'currently_reading': ub.session.query(ub.ReadBook).filter(
                ub.ReadBook.read_status == ub.ReadBook.STATUS_IN_PROGRESS
            ).count(),
            'books_in_shelves': ub.session.query(ub.BookShelf).count(),
        }

        # Most read books
        most_read = ub.session.query(
            ub.ReadBook.book_id,
            func.count(ub.ReadBook.id).label('read_count')
        ).filter(
            ub.ReadBook.read_status == ub.ReadBook.STATUS_FINISHED
        ).group_by(ub.ReadBook.book_id).order_by(text('read_count DESC')).limit(10).all()

        stats['most_read'] = []
        for book_id, count in most_read:
            try:
                book = calibre_db.get_book(book_id)
                if book:
                    stats['most_read'].append({
                        'book_id': book_id,
                        'title': book.title,
                        'author': book.authors[0].name if book.authors else 'Unknown',
                        'reads': count
                    })
            except Exception as e:
                log.debug(f"Error getting book {book_id}: {e}")
                continue

        return stats
    except Exception as e:
        log.error(f"Error getting reading stats: {e}")
        return {}


def calculate_all_stats():
    """Calculate all statistics (without cache)"""
    try:
        log.info("Calculating statistics...")
        return {
            'library': get_library_stats(),
            'users': get_user_stats(),
            'downloads': get_download_stats(),
            'reading': get_reading_stats(),
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        log.error(f"Error calculating stats: {e}")
        return {
            'library': {},
            'users': {},
            'downloads': {},
            'reading': {},
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'error': str(e)
        }


def get_all_stats(force_refresh=False):
    """
    Get all statistics for admin dashboard
    Uses cache if available and not expired, otherwise recalculates
    """
    # Try to load from cache first
    if not force_refresh:
        cached = load_cached_stats()
        if cached:
            return cached

    # Calculate fresh stats
    stats = calculate_all_stats()

    # Save to cache
    save_cached_stats(stats)

    return stats


def update_stats_cache():
    """
    Update the statistics cache
    This function is meant to be called by a scheduled task
    """
    try:
        log.info("Updating statistics cache...")
        stats = calculate_all_stats()
        save_cached_stats(stats)
        log.info("Statistics cache updated successfully")
        return True
    except Exception as e:
        log.error(f"Error updating statistics cache: {e}")
        return False


def clear_stats_cache():
    """Clear the statistics cache"""
    try:
        cache_path = get_cache_path()
        if os.path.exists(cache_path):
            os.remove(cache_path)
            log.info("Statistics cache cleared")
            return True
        return False
    except Exception as e:
        log.error(f"Error clearing cache: {e}")
        return False


# Initialize cache on first import if it doesn't exist
def initialize_cache():
    """Initialize cache on startup if it doesn't exist"""
    try:
        cache_path = get_cache_path()
        if not os.path.exists(cache_path):
            log.info("Initializing statistics cache on startup...")
            update_stats_cache()
    except Exception as e:
        log.warning(f"Could not initialize statistics cache: {e}")


# Auto-initialize on import (will run when the module is first loaded)
try:
    initialize_cache()
except:
    pass  # Don't fail if initialization fails
