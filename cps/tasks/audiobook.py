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

import os
import re
from time import time
from flask_babel import lazy_gettext as N_, gettext as _
from sqlalchemy.exc import SQLAlchemyError

from cps.services.worker import CalibreTask
from cps import db, app, logger, config
from cps.subproc_wrapper import process_open
from cps.ub import init_db_thread
from cps.file_helper import get_temp_dir

log = logger.create()


class TaskGenerateAudiobook(CalibreTask):
    """
    Background task to generate an audiobook from a book's text using macOS 'say' command.
    The audiobook is split into multiple parts for easier handling.
    """

    def __init__(self, book_id, book_format, voice='Alex', words_per_part=5000, user=None):
        """
        Initialize the audiobook generation task.

        Args:
            book_id: ID of the book to convert
            book_format: Format of the book (EPUB, PDF, TXT, etc.)
            voice: macOS voice to use (default: Alex)
            words_per_part: Number of words per audio file part (default: 5000)
            user: User who requested the generation
        """
        super(TaskGenerateAudiobook, self).__init__(N_("Generating audiobook"))
        self.book_id = book_id
        self.book_format = book_format.upper()
        self.voice = voice
        self.words_per_part = words_per_part
        self.user = user
        self.title = ""
        self.worker_thread = None

    def run(self, worker_thread):
        """Execute the audiobook generation task"""
        self.worker_thread = worker_thread

        try:
            # Initialize database connection for this thread
            init_db_thread()

            with app.app_context():
                worker_db = db.CalibreDB(app)
                book = worker_db.get_book(self.book_id)

                if not book:
                    return self._handleError(N_("Book not found"))

                self.title = book.title
                self.message = N_("Generating audiobook for '%(title)s'", title=self.title)

                log.info(f"Starting audiobook generation for '{self.title}' - Voice: {self.voice}, Words per part: {self.words_per_part}")

                # Get the book file data
                book_data = worker_db.get_book_format(self.book_id, self.book_format)
                if not book_data:
                    return self._handleError(N_("Format %(format)s not found for book", format=self.book_format))

                # Build the file path
                book_path = os.path.join(config.config_calibre_dir, book.path)
                book_file = os.path.join(book_path, book_data.name + "." + self.book_format.lower())

                if not os.path.exists(book_file):
                    return self._handleError(N_("Book file not found: %(file)s", file=book_file))

                # Extract text from the book
                self.progress = 0.1
                self.message = N_("Extracting text from '%(title)s'...", title=self.title)

                text = self._extract_text(book_file, self.book_format)
                if not text:
                    return self._handleError(N_("Could not extract text from book"))

                # Split text into parts
                self.progress = 0.2
                self.message = N_("Splitting text into parts...")

                text_parts = self._split_text(text, self.words_per_part)
                total_parts = len(text_parts)

                log.info(f"Generating {total_parts} audio parts for book '{self.title}'")

                # Generate audio for each part
                audio_files = []
                for i, part_text in enumerate(text_parts, 1):
                    progress = 0.2 + (0.7 * i / total_parts)  # 20% to 90%
                    self.progress = progress
                    self.message = N_("Generating audio part %(current)d of %(total)d...",
                                    current=i, total=total_parts)

                    audio_file = self._generate_audio_part(part_text, book_path, book_data.name, i)
                    if audio_file:
                        audio_files.append(audio_file)
                    else:
                        return self._handleError(N_("Failed to generate audio part %(part)d", part=i))

                # Register audio files in database
                self.progress = 0.95
                self.message = N_("Registering audiobook files in database...")

                for audio_file in audio_files:
                    self._register_audio_file(worker_db, book, audio_file)

                self.progress = 1.0
                self.message = N_("Audiobook generated successfully: %(parts)d parts", parts=total_parts)

                return f"Generated {total_parts} audio files"

        except Exception as e:
            log.error(f"Error generating audiobook for book {self.book_id}: {str(e)}")
            return self._handleError(N_("Error generating audiobook: %(error)s", error=str(e)))

    def _extract_text(self, book_file, book_format):
        """Extract text content from the book file"""
        try:
            if book_format == "TXT":
                # Simple text file
                with open(book_file, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()

            elif book_format == "EPUB":
                # Extract from EPUB using ebooklib
                try:
                    import ebooklib
                    from ebooklib import epub
                    from bs4 import BeautifulSoup

                    book = epub.read_epub(book_file)
                    text_parts = []

                    for item in book.get_items():
                        if item.get_type() == ebooklib.ITEM_DOCUMENT:
                            soup = BeautifulSoup(item.get_content(), 'html.parser')
                            text_parts.append(soup.get_text())

                    return '\n\n'.join(text_parts)

                except ImportError:
                    log.warning("ebooklib not installed, trying alternative method")
                    # Alternative: use ebook-convert if available
                    return self._extract_with_calibre(book_file)

            elif book_format == "PDF":
                # Extract from PDF using PyPDF2 or pdfplumber
                try:
                    import pdfplumber

                    text_parts = []
                    with pdfplumber.open(book_file) as pdf:
                        for page in pdf.pages:
                            text = page.extract_text()
                            if text:
                                text_parts.append(text)

                    return '\n\n'.join(text_parts)

                except ImportError:
                    log.warning("pdfplumber not installed, trying PyPDF2")
                    try:
                        import PyPDF2

                        text_parts = []
                        with open(book_file, 'rb') as f:
                            pdf_reader = PyPDF2.PdfReader(f)
                            for page in pdf_reader.pages:
                                text = page.extract_text()
                                if text:
                                    text_parts.append(text)

                        return '\n\n'.join(text_parts)

                    except ImportError:
                        log.error("Neither pdfplumber nor PyPDF2 installed")
                        return None

            else:
                log.error(f"Unsupported format for text extraction: {book_format}")
                return None

        except Exception as e:
            log.error(f"Error extracting text: {str(e)}")
            return None

    def _extract_with_calibre(self, book_file):
        """Extract text using Calibre's ebook-convert tool"""
        try:
            temp_dir = get_temp_dir()
            txt_file = os.path.join(temp_dir, f"temp_{self.book_id}.txt")

            # Use ebook-convert to convert to TXT
            command = [
                config.config_converterpath or 'ebook-convert',
                book_file,
                txt_file
            ]

            p = process_open(command)
            p.wait()

            if p.returncode == 0 and os.path.exists(txt_file):
                with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
                os.remove(txt_file)
                return text
            else:
                log.error(f"ebook-convert failed with code {p.returncode}")
                return None

        except Exception as e:
            log.error(f"Error using ebook-convert: {str(e)}")
            return None

    def _split_text(self, text, words_per_part):
        """Split text into parts based on word count"""
        # Clean the text
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = text.strip()

        # Split into words
        words = text.split()

        # Split into parts
        parts = []
        for i in range(0, len(words), words_per_part):
            part_words = words[i:i + words_per_part]
            part_text = ' '.join(part_words)
            parts.append(part_text)

        return parts

    def _generate_audio_part(self, text, book_path, base_name, part_number):
        """Generate audio file for a text part using Node.js TTS"""
        try:
            # Create output filename - use MP3 format for smaller file size
            audio_filename = f"{base_name}_part{part_number:03d}.mp3"
            audio_path = os.path.join(book_path, audio_filename)

            # Get path to the Node.js TTS script
            tts_script = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'static', 'js', 'tts-generator.js'
            )

            if not os.path.exists(tts_script):
                log.error(f"TTS script not found: {tts_script}")
                return None

            # Escape text for command line (write to temp file instead)
            temp_dir = get_temp_dir()
            temp_text_file = os.path.join(temp_dir, f"text_part{part_number}.txt")

            with open(temp_text_file, 'w', encoding='utf-8') as f:
                f.write(text)

            # Use Node.js with 'say' library to generate audio
            # Read text from file to avoid command line length limits
            command = [
                'node',
                tts_script,
                f"@{temp_text_file}",  # @ prefix means read from file
                audio_path,
                self.voice,
                '1.0'  # speed
            ]

            # Alternative: pass text directly if not too long
            if len(text) < 5000:  # Safe limit for command line
                command = [
                    'node',
                    tts_script,
                    text,
                    audio_path,
                    self.voice,
                    '1.0'
                ]

            log.info(f"Generating audio part {part_number}: {audio_filename} with voice '{self.voice}'")
            log.debug(f"TTS command: {' '.join(command)}")

            calibre_web_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            p = process_open(command, cwd=calibre_web_dir)
            stdout, stderr = p.communicate(timeout=600)  # 10 minute timeout

            # Log output for debugging
            if stdout:
                stdout_msg = stdout.decode('utf-8') if isinstance(stdout, bytes) else stdout
                log.debug(f"TTS stdout: {stdout_msg}")
            if stderr:
                stderr_msg = stderr.decode('utf-8') if isinstance(stderr, bytes) else stderr
                log.debug(f"TTS stderr: {stderr_msg}")

            # Clean up temp file
            if os.path.exists(temp_text_file):
                try:
                    os.remove(temp_text_file)
                except:
                    pass

            if p.returncode == 0 and os.path.exists(audio_path):
                log.info(f"Successfully generated {audio_filename}")
                return audio_path
            else:
                log.error(f"Node.js TTS failed with code {p.returncode}")
                if stderr:
                    # stderr might be bytes or str depending on process_open implementation
                    error_msg = stderr.decode('utf-8') if isinstance(stderr, bytes) else stderr
                    log.error(f"Error output: {error_msg}")
                return None

        except Exception as e:
            log.error(f"Error generating audio part {part_number}: {str(e)}")
            return None

    def _register_audio_file(self, worker_db, book, audio_file):
        """Register the generated audio file in the database"""
        try:
            # Get filename without path and extension
            filename = os.path.basename(audio_file)
            name_without_ext = os.path.splitext(filename)[0]

            # Determine format from file extension
            file_ext = os.path.splitext(filename)[1].upper().replace('.', '')

            # Check if this audio file already exists in database
            existing_data = worker_db.session.query(db.Data).filter(
                db.Data.book == book.id,
                db.Data.format == file_ext,
                db.Data.name == name_without_ext
            ).first()

            if existing_data:
                # Update file size
                existing_data.uncompressed_size = os.path.getsize(audio_file)
                log.info(f"Updated existing audio file entry: {name_without_ext}")
            else:
                # Create new database entry
                new_data = db.Data(
                    book=book.id,
                    format=file_ext,
                    uncompressed_size=os.path.getsize(audio_file),
                    name=name_without_ext
                )
                worker_db.session.add(new_data)
                log.info(f"Added new audio file entry: {name_without_ext}")

            worker_db.session.commit()

        except SQLAlchemyError as e:
            log.error(f"Database error registering audio file: {str(e)}")
            worker_db.session.rollback()
        except Exception as e:
            log.error(f"Error registering audio file: {str(e)}")

    def _handleError(self, error_message):
        """Handle errors and update task status"""
        log.error(error_message)
        self.stat = 1  # STAT_FAIL
        self.progress = 1
        self.error = error_message
        return error_message

    @property
    def name(self):
        return f"Audiobook: {self.title if self.title else self.book_id}"

    def is_cancellable(self):
        return False  # Cannot cancel once started (audio generation is atomic)
