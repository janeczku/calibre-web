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

from datetime import datetime, timezone
from . import logger, ub, db
from flask_babel import gettext as _

log = logger.create()

# Definiciones de logros predefinidos (estilo Apple Fitness)
ACHIEVEMENT_DEFINITIONS = [
    # Logros de libros leídos
    {
        'name': 'first_book',
        'description': _('Read your first book'),
        'category': 'books_read',
        'level': 1,
        'threshold': 1,
        'icon': '📖',
        'color': '#4CAF50'
    },
    {
        'name': 'bookworm_bronze',
        'description': _('Read 10 books'),
        'category': 'books_read',
        'level': 2,
        'threshold': 10,
        'icon': '🥉',
        'color': '#CD7F32'
    },
    {
        'name': 'bookworm_silver',
        'description': _('Read 25 books'),
        'category': 'books_read',
        'level': 3,
        'threshold': 25,
        'icon': '🥈',
        'color': '#C0C0C0'
    },
    {
        'name': 'bookworm_gold',
        'description': _('Read 50 books'),
        'category': 'books_read',
        'level': 4,
        'threshold': 50,
        'icon': '🥇',
        'color': '#FFD700'
    },
    {
        'name': 'bookworm_platinum',
        'description': _('Read 100 books'),
        'category': 'books_read',
        'level': 5,
        'threshold': 100,
        'icon': '💎',
        'color': '#E5E4E2'
    },
    {
        'name': 'bookworm_legend',
        'description': _('Read 250 books'),
        'category': 'books_read',
        'level': 6,
        'threshold': 250,
        'icon': '👑',
        'color': '#9C27B0'
    },

    # Logros de series
    {
        'name': 'series_starter',
        'description': _('Complete your first series'),
        'category': 'series',
        'level': 1,
        'threshold': 1,
        'icon': '📚',
        'color': '#2196F3'
    },
    {
        'name': 'series_master',
        'description': _('Complete 5 series'),
        'category': 'series',
        'level': 2,
        'threshold': 5,
        'icon': '📚✨',
        'color': '#3F51B5'
    },

    # Logros de descargas
    {
        'name': 'downloader_bronze',
        'description': _('Download 25 books'),
        'category': 'downloads',
        'level': 1,
        'threshold': 25,
        'icon': '⬇️',
        'color': '#FF5722'
    },
    {
        'name': 'downloader_silver',
        'description': _('Download 50 books'),
        'category': 'downloads',
        'level': 2,
        'threshold': 50,
        'icon': '⬇️⬇️',
        'color': '#FF9800'
    },

    # Logros de géneros
    {
        'name': 'genre_explorer',
        'description': _('Read books from 5 different genres'),
        'category': 'genres',
        'level': 1,
        'threshold': 5,
        'icon': '🗺️',
        'color': '#009688'
    },
    {
        'name': 'genre_master',
        'description': _('Read books from 10 different genres'),
        'category': 'genres',
        'level': 2,
        'threshold': 10,
        'icon': '🌍',
        'color': '#00BCD4'
    },

    # Logros de tiempo de lectura
    {
        'name': 'reading_time_10h',
        'description': _('Spend 10 hours reading'),
        'category': 'reading_time',
        'level': 1,
        'threshold': 600,  # minutos
        'icon': '⏱️',
        'color': '#FFC107'
    },
    {
        'name': 'reading_time_50h',
        'description': _('Spend 50 hours reading'),
        'category': 'reading_time',
        'level': 2,
        'threshold': 3000,
        'icon': '⏰',
        'color': '#FFEB3B'
    },

    # Logros anuales
    {
        'name': 'yearly_reader_12',
        'description': _('Read 12 books in a year (1 per month)'),
        'category': 'yearly',
        'level': 1,
        'threshold': 12,
        'icon': '📅',
        'color': '#8BC34A'
    },
    {
        'name': 'yearly_reader_25',
        'description': _('Read 25 books in a year'),
        'category': 'yearly',
        'level': 2,
        'threshold': 25,
        'icon': '📆',
        'color': '#CDDC39'
    },
    {
        'name': 'yearly_reader_52',
        'description': _('Read 52 books in a year (1 per week)'),
        'category': 'yearly',
        'level': 3,
        'threshold': 52,
        'icon': '🎯',
        'color': '#FF6F00'
    }
]


def initialize_achievements():
    """Inicializa los logros predefinidos en la base de datos"""
    try:
        for achievement_data in ACHIEVEMENT_DEFINITIONS:
            # Verificar si ya existe
            existing = ub.session.query(ub.AchievementDefinition).filter(
                ub.AchievementDefinition.name == achievement_data['name']
            ).first()

            if not existing:
                achievement = ub.AchievementDefinition(
                    name=achievement_data['name'],
                    description=achievement_data['description'],
                    category=achievement_data['category'],
                    level=achievement_data['level'],
                    threshold=achievement_data['threshold'],
                    icon=achievement_data['icon'],
                    color=achievement_data['color']
                )
                ub.session.add(achievement)

        ub.session.commit()
        log.info("Logros inicializados correctamente")
    except Exception as e:
        log.error(f"Error inicializando logros: {str(e)}")
        ub.session.rollback()


def check_and_unlock_achievements(user_id):
    """Verifica y desbloquea logros para un usuario"""
    try:
        # Obtener estadísticas del usuario
        books_read = ub.session.query(ub.ReadBook).filter(
            ub.ReadBook.user_id == user_id,
            ub.ReadBook.read_status == ub.ReadBook.STATUS_FINISHED
        ).count()

        books_downloaded = ub.session.query(ub.Downloads).filter(
            ub.Downloads.user_id == user_id
        ).count()

        # Verificar logros de libros leídos
        _check_category_achievements(user_id, 'books_read', books_read)

        # Verificar logros de descargas
        _check_category_achievements(user_id, 'downloads', books_downloaded)

        # Verificar logros de series completadas
        completed_series = ub.session.query(ub.UserSeriesProgress).filter(
            ub.UserSeriesProgress.user_id == user_id,
            ub.UserSeriesProgress.is_completed == True
        ).count()
        _check_category_achievements(user_id, 'series', completed_series)

        # Verificar logros de géneros
        genres_read = ub.session.query(ub.UserGenreStats).filter(
            ub.UserGenreStats.user_id == user_id,
            ub.UserGenreStats.books_read > 0
        ).count()
        _check_category_achievements(user_id, 'genres', genres_read)

        # Verificar logros de tiempo de lectura
        total_reading_time = ub.session.query(
            ub.func.sum(ub.KoboStatistics.spent_reading_minutes)
        ).join(ub.KoboReadingState).filter(
            ub.KoboReadingState.user_id == user_id
        ).scalar() or 0
        _check_category_achievements(user_id, 'reading_time', total_reading_time)

        # Verificar logros anuales
        current_year = datetime.now().year
        yearly_stats = ub.session.query(ub.ReadingYearlyStats).filter(
            ub.ReadingYearlyStats.user_id == user_id,
            ub.ReadingYearlyStats.year == current_year
        ).first()

        if yearly_stats:
            _check_category_achievements(user_id, 'yearly', yearly_stats.books_read)

        ub.session.commit()

    except Exception as e:
        log.error(f"Error verificando logros para usuario {user_id}: {str(e)}")
        ub.session.rollback()


def _check_category_achievements(user_id, category, current_value):
    """Verifica los logros de una categoría específica"""
    try:
        # Obtener todos los logros de esta categoría
        achievements = ub.session.query(ub.AchievementDefinition).filter(
            ub.AchievementDefinition.category == category
        ).order_by(ub.AchievementDefinition.threshold).all()

        for achievement in achievements:
            # Verificar si el usuario ya tiene este logro
            user_achievement = ub.session.query(ub.UserAchievement).filter(
                ub.UserAchievement.user_id == user_id,
                ub.UserAchievement.achievement_id == achievement.id
            ).first()

            if current_value >= achievement.threshold:
                # El usuario ha alcanzado el umbral
                if not user_achievement:
                    # Desbloquear el logro
                    new_achievement = ub.UserAchievement(
                        user_id=user_id,
                        achievement_id=achievement.id,
                        progress=current_value,
                        unlocked_at=datetime.now(timezone.utc)
                    )
                    ub.session.add(new_achievement)
                    log.info(f"Logro desbloqueado: {achievement.name} para usuario {user_id}")
                else:
                    # Actualizar el progreso
                    user_achievement.progress = current_value
            elif user_achievement:
                # Actualizar el progreso aunque no esté desbloqueado
                user_achievement.progress = current_value

    except Exception as e:
        log.error(f"Error verificando logros de categoría {category}: {str(e)}")


def update_reading_stats(user_id, book_id, status):
    """Actualiza las estadísticas de lectura cuando un usuario marca un libro como leído"""
    try:
        from . import calibre_db

        current_year = datetime.now().year

        # Actualizar estadísticas anuales
        yearly_stats = ub.session.query(ub.ReadingYearlyStats).filter(
            ub.ReadingYearlyStats.user_id == user_id,
            ub.ReadingYearlyStats.year == current_year
        ).first()

        if not yearly_stats:
            yearly_stats = ub.ReadingYearlyStats(
                user_id=user_id,
                year=current_year,
                books_read=0,
                books_downloaded=0
            )
            ub.session.add(yearly_stats)

        if status == ub.ReadBook.STATUS_FINISHED:
            yearly_stats.books_read += 1

        yearly_stats.updated_at = datetime.now(timezone.utc)

        # Actualizar estadísticas de géneros
        book = calibre_db.get_book(book_id)
        if book and book.tags:
            for tag in book.tags:
                genre_stats = ub.session.query(ub.UserGenreStats).filter(
                    ub.UserGenreStats.user_id == user_id,
                    ub.UserGenreStats.genre_id == tag.id
                ).first()

                if not genre_stats:
                    genre_stats = ub.UserGenreStats(
                        user_id=user_id,
                        genre_id=tag.id,
                        genre_name=tag.name,
                        books_read=0
                    )
                    ub.session.add(genre_stats)

                if status == ub.ReadBook.STATUS_FINISHED:
                    genre_stats.books_read += 1
                    genre_stats.last_read = datetime.now(timezone.utc)

        # Actualizar progreso de series
        if book and book.series:
            for series in book.series:
                series_progress = ub.session.query(ub.UserSeriesProgress).filter(
                    ub.UserSeriesProgress.user_id == user_id,
                    ub.UserSeriesProgress.series_id == series.id
                ).first()

                if not series_progress:
                    # Contar libros totales en la serie
                    total_books = calibre_db.session.query(db.books_series_link).filter(
                        db.books_series_link.c.series == series.id
                    ).count()

                    series_progress = ub.UserSeriesProgress(
                        user_id=user_id,
                        series_id=series.id,
                        series_name=series.name,
                        total_books=total_books,
                        books_read=0
                    )
                    ub.session.add(series_progress)

                if status == ub.ReadBook.STATUS_FINISHED:
                    series_progress.books_read += 1
                    series_progress.last_read_date = datetime.now(timezone.utc)

                    # Verificar si se completó la serie
                    if series_progress.books_read >= series_progress.total_books:
                        series_progress.is_completed = True

                series_progress.updated_at = datetime.now(timezone.utc)

        ub.session.commit()

        # Verificar logros
        check_and_unlock_achievements(user_id)

    except Exception as e:
        log.error(f"Error actualizando estadísticas de lectura: {str(e)}")
        ub.session.rollback()


def update_download_stats(user_id, book_id):
    """Actualiza las estadísticas cuando un usuario descarga un libro"""
    try:
        from . import calibre_db

        current_year = datetime.now().year

        # Actualizar estadísticas anuales
        yearly_stats = ub.session.query(ub.ReadingYearlyStats).filter(
            ub.ReadingYearlyStats.user_id == user_id,
            ub.ReadingYearlyStats.year == current_year
        ).first()

        if not yearly_stats:
            yearly_stats = ub.ReadingYearlyStats(
                user_id=user_id,
                year=current_year,
                books_read=0,
                books_downloaded=0
            )
            ub.session.add(yearly_stats)

        yearly_stats.books_downloaded += 1
        yearly_stats.updated_at = datetime.now(timezone.utc)

        # Actualizar estadísticas de géneros
        book = calibre_db.get_book(book_id)
        if book and book.tags:
            for tag in book.tags:
                genre_stats = ub.session.query(ub.UserGenreStats).filter(
                    ub.UserGenreStats.user_id == user_id,
                    ub.UserGenreStats.genre_id == tag.id
                ).first()

                if not genre_stats:
                    genre_stats = ub.UserGenreStats(
                        user_id=user_id,
                        genre_id=tag.id,
                        genre_name=tag.name,
                        books_downloaded=0
                    )
                    ub.session.add(genre_stats)

                genre_stats.books_downloaded += 1

        # Actualizar progreso de series
        if book and book.series:
            for series in book.series:
                series_progress = ub.session.query(ub.UserSeriesProgress).filter(
                    ub.UserSeriesProgress.user_id == user_id,
                    ub.UserSeriesProgress.series_id == series.id
                ).first()

                if not series_progress:
                    total_books = calibre_db.session.query(db.books_series_link).filter(
                        db.books_series_link.c.series == series.id
                    ).count()

                    series_progress = ub.UserSeriesProgress(
                        user_id=user_id,
                        series_id=series.id,
                        series_name=series.name,
                        total_books=total_books,
                        books_downloaded=0
                    )
                    ub.session.add(series_progress)

                series_progress.books_downloaded += 1
                series_progress.updated_at = datetime.now(timezone.utc)

        ub.session.commit()

        # Verificar logros
        check_and_unlock_achievements(user_id)

    except Exception as e:
        log.error(f"Error actualizando estadísticas de descarga: {str(e)}")
        ub.session.rollback()


def get_user_level(books_read):
    """Calcula el nivel del usuario basado en libros leídos (estilo Apple Fitness)"""
    if books_read >= 250:
        return {'level': 6, 'name': _('Legend'), 'icon': '👑', 'color': '#9C27B0'}
    elif books_read >= 100:
        return {'level': 5, 'name': _('Platinum'), 'icon': '💎', 'color': '#E5E4E2'}
    elif books_read >= 50:
        return {'level': 4, 'name': _('Gold'), 'icon': '🥇', 'color': '#FFD700'}
    elif books_read >= 25:
        return {'level': 3, 'name': _('Silver'), 'icon': '🥈', 'color': '#C0C0C0'}
    elif books_read >= 10:
        return {'level': 2, 'name': _('Bronze'), 'icon': '🥉', 'color': '#CD7F32'}
    elif books_read >= 1:
        return {'level': 1, 'name': _('Beginner'), 'icon': '📖', 'color': '#4CAF50'}
    else:
        return {'level': 0, 'name': _('New Reader'), 'icon': '🆕', 'color': '#9E9E9E'}


def get_reading_rings(user_id, year=None):
    """Obtiene los datos para los anillos de lectura (estilo Apple Fitness)"""
    try:
        if not year:
            year = datetime.now().year

        yearly_stats = ub.session.query(ub.ReadingYearlyStats).filter(
            ub.ReadingYearlyStats.user_id == user_id,
            ub.ReadingYearlyStats.year == year
        ).first()

        if not yearly_stats:
            return {
                'books_read': {'value': 0, 'goal': 52, 'percentage': 0},
                'books_downloaded': {'value': 0, 'goal': 100, 'percentage': 0},
                'reading_time': {'value': 0, 'goal': 3000, 'percentage': 0}  # 50 horas
            }

        # Calcular porcentajes
        books_goal = 52  # 1 libro por semana
        downloads_goal = 100
        reading_time_goal = 3000  # 50 horas en minutos

        return {
            'books_read': {
                'value': yearly_stats.books_read,
                'goal': books_goal,
                'percentage': min(100, (yearly_stats.books_read / books_goal) * 100)
            },
            'books_downloaded': {
                'value': yearly_stats.books_downloaded,
                'goal': downloads_goal,
                'percentage': min(100, (yearly_stats.books_downloaded / downloads_goal) * 100)
            },
            'reading_time': {
                'value': yearly_stats.reading_time_minutes,
                'goal': reading_time_goal,
                'percentage': min(100, (yearly_stats.reading_time_minutes / reading_time_goal) * 100)
            }
        }
    except Exception as e:
        log.error(f"Error obteniendo anillos de lectura: {str(e)}")
        return None
