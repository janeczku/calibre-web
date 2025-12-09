# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
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
Telegram Bot integration for searching and downloading books
"""

import requests
import os
import tempfile
from flask_babel import gettext as _
from . import logger

log = logger.create()


class TelegramBot:
    """Helper class for interacting with Telegram Bot API"""

    def __init__(self, bot_token, bot_username):
        self.bot_token = bot_token
        self.bot_username = bot_username
        self.api_base_url = f"https://api.telegram.org/bot{bot_token}"

    def search_books(self, query):
        """
        Search for books by sending a message to the bot and getting results
        Returns a list of book results with file information
        """
        try:
            # Get bot information to verify connection
            response = requests.get(f"{self.api_base_url}/getMe", timeout=10)
            if response.status_code != 200:
                log.error(f"Error connecting to Telegram bot: {response.text}")
                return []

            bot_info = response.json()
            if not bot_info.get('ok'):
                log.error(f"Telegram bot error: {bot_info}")
                return []

            # Search using inline query to the bot
            # Note: This requires the bot to support inline queries
            search_url = f"{self.api_base_url}/answerInlineQuery"

            # Alternative: Send message and parse response
            # This is a simplified implementation
            # In production, you might want to use a more sophisticated approach
            # with webhooks or long polling to get responses

            log.info(f"Searching Telegram bot @{self.bot_username} for: {query}")

            # For now, return empty list
            # Real implementation would depend on specific bot's API
            return []

        except requests.RequestException as e:
            log.error(f"Error searching Telegram bot: {str(e)}")
            return []

    def get_bot_info(self):
        """Get information about the bot"""
        try:
            response = requests.get(f"{self.api_base_url}/getMe", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    return data.get('result')
            return None
        except requests.RequestException as e:
            log.error(f"Error getting bot info: {str(e)}")
            return None

    def download_file(self, file_id, destination_path):
        """Download a file from Telegram"""
        try:
            # Get file path
            response = requests.get(
                f"{self.api_base_url}/getFile",
                params={'file_id': file_id},
                timeout=10
            )

            if response.status_code != 200:
                log.error(f"Error getting file info: {response.text}")
                return False

            file_data = response.json()
            if not file_data.get('ok'):
                log.error(f"Telegram file error: {file_data}")
                return False

            file_path = file_data['result']['file_path']
            download_url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"

            # Download the file
            response = requests.get(download_url, stream=True, timeout=60)
            if response.status_code == 200:
                with open(destination_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                log.info(f"File downloaded successfully to {destination_path}")
                return True
            else:
                log.error(f"Error downloading file: {response.text}")
                return False

        except requests.RequestException as e:
            log.error(f"Error downloading file from Telegram: {str(e)}")
            return False

    def send_message(self, chat_id, text):
        """Send a message to a specific chat"""
        try:
            response = requests.post(
                f"{self.api_base_url}/sendMessage",
                json={'chat_id': chat_id, 'text': text},
                timeout=10
            )
            return response.status_code == 200
        except requests.RequestException as e:
            log.error(f"Error sending message: {str(e)}")
            return False


def test_telegram_connection(bot_token, bot_username):
    """Test if the Telegram bot configuration is valid"""
    try:
        bot = TelegramBot(bot_token, bot_username)
        bot_info = bot.get_bot_info()
        if bot_info:
            return True, _('Successfully connected to bot: %(name)s', name=bot_info.get('first_name', 'Unknown'))
        else:
            return False, _('Could not connect to Telegram bot')
    except Exception as e:
        log.error(f"Error testing Telegram connection: {str(e)}")
        return False, str(e)
