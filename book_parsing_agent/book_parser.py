#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Book Parser Module - Extract structured content from EPUB and PDF files

This module provides functionality to parse books and extract:
- Metadata (title, author, description, etc.)
- Table of Contents (TOC)
- Chapter content with structure preservation
- Tables, images, and charts
"""

import os
import zipfile
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from lxml import etree


@dataclass
class BookMetadata:
    """Container for book metadata"""
    title: str
    author: str
    description: str = ""
    language: str = ""
    publisher: str = ""
    publication_date: str = ""
    isbn: str = ""
    tags: List[str] = None
    series: str = ""
    series_index: str = ""

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class TableContent:
    """Container for table data"""
    html: str
    rows: List[List[str]]
    caption: str = ""


@dataclass
class ImageContent:
    """Container for image data"""
    src: str
    alt: str = ""
    title: str = ""
    caption: str = ""


@dataclass
class ChapterContent:
    """Container for chapter content"""
    index: int
    file: str
    title: Optional[str]
    html: str
    text: str
    tables: List[TableContent]
    images: List[ImageContent]
    charts: List[str]  # SVG content

    def to_dict(self) -> Dict:
        return {
            'index': self.index,
            'file': self.file,
            'title': self.title,
            'html': self.html,
            'text': self.text,
            'tables': [{'html': t.html, 'rows': t.rows, 'caption': t.caption} for t in self.tables],
            'images': [{'src': i.src, 'alt': i.alt, 'title': i.title, 'caption': i.caption} for i in self.images],
            'charts': self.charts
        }


class EPUBParser:
    """Parser for EPUB files with full structure preservation"""

    # XML Namespaces used in EPUB files
    NS = {
        'n': 'urn:oasis:names:tc:opendocument:xmlns:container',
        'pkg': 'http://www.idpf.org/2007/opf',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'ncx': 'http://www.daisy.org/z3986/2005/ncx/',
        'epub': 'http://www.idpf.org/2007/ops'
    }

    def __init__(self, file_path: str):
        """
        Initialize EPUB parser

        Args:
            file_path: Path to the EPUB file
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"EPUB file not found: {file_path}")

        self.file_path = file_path
        self.epub_zip = zipfile.ZipFile(file_path)
        self.tree, self.opf_path = self._get_content_opf()
        self.content_dir = os.path.dirname(self.opf_path)

    def _get_content_opf(self):
        """
        Extract the OPF (Open Package Format) file from EPUB

        The OPF file contains all metadata and structure information
        """
        try:
            txt = self.epub_zip.read('META-INF/container.xml')
            tree = etree.fromstring(txt)
            opf_path = tree.xpath('n:rootfiles/n:rootfile/@full-path', namespaces=self.NS)[0]
            opf_content = self.epub_zip.read(opf_path)
            return etree.fromstring(opf_content), opf_path
        except Exception as e:
            raise ValueError(f"Failed to parse EPUB structure: {e}")

    def extract_metadata(self) -> BookMetadata:
        """
        Extract metadata from EPUB

        Returns:
            BookMetadata object with all available metadata
        """
        metadata_elem = self.tree.xpath('/pkg:package/pkg:metadata', namespaces=self.NS)[0]

        def get_text(xpath: str, default: str = "Unknown") -> str:
            """Helper to extract text from XPath"""
            result = metadata_elem.xpath(xpath, namespaces=self.NS)
            return result[0].strip() if result else default

        def get_text_list(xpath: str) -> List[str]:
            """Helper to extract text list from XPath"""
            return [r.strip() for r in metadata_elem.xpath(xpath, namespaces=self.NS)]

        # Extract basic metadata
        title = get_text('dc:title/text()')

        # Handle multiple authors
        authors = get_text_list('dc:creator/text()')
        author = ' & '.join(authors) if authors else "Unknown"

        description = get_text('dc:description/text()', "")
        language = get_text('dc:language/text()', "")
        publisher = get_text('dc:publisher/text()', "")
        pub_date = get_text('dc:date/text()', "")

        # Extract tags/subjects
        tags = get_text_list('dc:subject/text()')

        # Extract identifiers (ISBN, etc.)
        isbn = ""
        identifiers = metadata_elem.xpath('dc:identifier', namespaces=self.NS)
        for identifier in identifiers:
            id_type = identifier.get('id', '').lower()
            if 'isbn' in id_type:
                isbn = identifier.text
                break

        # Extract series information (Calibre metadata)
        series = get_text("pkg:meta[@name='calibre:series']/@content", "")
        series_index = get_text("pkg:meta[@name='calibre:series_index']/@content", "")

        # Clean up date (take only YYYY-MM-DD)
        if pub_date and len(pub_date) > 10:
            pub_date = pub_date[:10]

        return BookMetadata(
            title=title,
            author=author,
            description=description,
            language=language,
            publisher=publisher,
            publication_date=pub_date,
            isbn=isbn,
            tags=tags,
            series=series,
            series_index=series_index
        )

    def extract_toc(self) -> List[Dict[str, str]]:
        """
        Extract Table of Contents

        Supports both EPUB3 (NAV) and EPUB2 (NCX) formats

        Returns:
            List of TOC entries with title and href
        """
        toc = []

        # Try EPUB3 NAV first
        toc = self._extract_nav_toc()
        if toc:
            return toc

        # Fallback to EPUB2 NCX
        toc = self._extract_ncx_toc()
        return toc

    def _extract_nav_toc(self) -> List[Dict[str, str]]:
        """Extract TOC from EPUB3 NAV document"""
        try:
            nav_items = self.tree.xpath(
                '/pkg:package/pkg:manifest/pkg:item[@properties="nav"]',
                namespaces=self.NS
            )

            if not nav_items:
                return []

            nav_href = nav_items[0].get('href')
            nav_path = os.path.join(self.content_dir, nav_href)
            nav_content = self.epub_zip.read(nav_path)

            # Parse NAV HTML
            nav_tree = etree.HTML(nav_content)

            toc = []
            # Look for <nav epub:type="toc">
            for link in nav_tree.xpath('//nav[@*="toc"]//a'):
                title = ''.join(link.xpath('.//text()')).strip()
                href = link.get('href', '')
                if title and href:
                    toc.append({'title': title, 'href': href})

            return toc
        except Exception as e:
            print(f"Warning: Failed to extract NAV TOC: {e}")
            return []

    def _extract_ncx_toc(self) -> List[Dict[str, str]]:
        """Extract TOC from EPUB2 NCX document"""
        try:
            ncx_items = self.tree.xpath(
                '/pkg:package/pkg:manifest/pkg:item[@media-type="application/x-dtbncx+xml"]',
                namespaces=self.NS
            )

            if not ncx_items:
                return []

            ncx_href = ncx_items[0].get('href')
            ncx_path = os.path.join(self.content_dir, ncx_href)
            ncx_content = self.epub_zip.read(ncx_path)
            ncx_tree = etree.fromstring(ncx_content)

            toc = []
            for nav in ncx_tree.xpath('//ncx:navPoint', namespaces=self.NS):
                title_elem = nav.xpath('.//ncx:text/text()', namespaces=self.NS)
                src_elem = nav.xpath('.//ncx:content/@src', namespaces=self.NS)

                if title_elem and src_elem:
                    toc.append({
                        'title': title_elem[0].strip(),
                        'href': src_elem[0]
                    })

            return toc
        except Exception as e:
            print(f"Warning: Failed to extract NCX TOC: {e}")
            return []

    def extract_chapters(self) -> List[ChapterContent]:
        """
        Extract all chapters with full content preservation

        Returns:
            List of ChapterContent objects
        """
        # Get reading order from spine
        spine_items = self.tree.xpath('/pkg:package/pkg:spine/pkg:itemref', namespaces=self.NS)

        # Get TOC for chapter titles
        toc = self.extract_toc()

        chapters = []
        for idx, itemref in enumerate(spine_items):
            idref = itemref.get('idref')

            # Find the corresponding file in manifest
            href_list = self.tree.xpath(
                f'/pkg:package/pkg:manifest/pkg:item[@id="{idref}"]/@href',
                namespaces=self.NS
            )

            if not href_list:
                continue

            href = href_list[0]

            try:
                # Read chapter content
                chapter_path = os.path.join(self.content_dir, href)
                chapter_bytes = self.epub_zip.read(chapter_path)
                chapter_html = chapter_bytes.decode('utf-8', errors='ignore')

                # Parse chapter (use HTML parser which handles namespaces and declarations)
                parser = etree.HTMLParser()
                chapter_tree = etree.fromstring(chapter_bytes, parser)

                # Extract structured content
                chapter = ChapterContent(
                    index=idx,
                    file=href,
                    title=self._get_chapter_title(href, toc),
                    html=chapter_html,
                    text=self._extract_text(chapter_tree),
                    tables=self._extract_tables(chapter_tree),
                    images=self._extract_images(chapter_tree),
                    charts=self._extract_charts(chapter_tree)
                )

                chapters.append(chapter)
            except Exception as e:
                print(f"Warning: Failed to parse chapter {href}: {e}")
                continue

        return chapters

    def _get_chapter_title(self, href: str, toc: List[Dict]) -> Optional[str]:
        """Match chapter file to TOC entry to get title"""
        base_href = href.split('#')[0]
        for entry in toc:
            if entry['href'].startswith(base_href):
                return entry['title']
        return None

    def _extract_text(self, tree) -> str:
        """Extract all text content from chapter"""
        return ' '.join(tree.xpath('//text()')).strip()

    def _extract_tables(self, tree) -> List[TableContent]:
        """Extract all tables with structure preserved"""
        tables = []
        for table_elem in tree.xpath('//table'):
            # Get caption if exists
            caption_elem = table_elem.xpath('.//caption/text()')
            caption = caption_elem[0].strip() if caption_elem else ""

            # Extract rows
            rows = []
            for row in table_elem.xpath('.//tr'):
                cells = [
                    ' '.join(cell.xpath('.//text()')).strip()
                    for cell in row.xpath('.//td | .//th')
                ]
                if cells:  # Only add non-empty rows
                    rows.append(cells)

            # Get HTML representation
            table_html = etree.tostring(table_elem, encoding='unicode', method='html')

            tables.append(TableContent(
                html=table_html,
                rows=rows,
                caption=caption
            ))

        return tables

    def _extract_images(self, tree) -> List[ImageContent]:
        """Extract all images with metadata"""
        images = []
        for img in tree.xpath('//img'):
            src = img.get('src', '')

            # Try to find caption from parent figure element
            caption = ""
            figure = img.xpath('ancestor::figure[1]//figcaption/text()')
            if figure:
                caption = figure[0].strip()

            images.append(ImageContent(
                src=src,
                alt=img.get('alt', ''),
                title=img.get('title', ''),
                caption=caption
            ))

        return images

    def _extract_charts(self, tree) -> List[str]:
        """Extract SVG charts"""
        charts = []
        for svg in tree.xpath('//svg'):
            svg_content = etree.tostring(svg, encoding='unicode', method='html')
            charts.append(svg_content)

        return charts

    def get_image_data(self, image_path: str) -> bytes:
        """
        Extract image binary data from EPUB

        Args:
            image_path: Relative path to image within EPUB

        Returns:
            Binary image data
        """
        full_path = os.path.join(self.content_dir, image_path)
        return self.epub_zip.read(full_path)

    def close(self):
        """Close the EPUB file"""
        self.epub_zip.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class BookParser:
    """
    Main interface for parsing books of different formats

    Currently supports:
    - EPUB (.epub, .kepub)
    """

    SUPPORTED_FORMATS = {'.epub', '.kepub'}

    def __init__(self, file_path: str):
        """
        Initialize book parser

        Args:
            file_path: Path to the book file
        """
        self.file_path = file_path
        self.format = os.path.splitext(file_path)[1].lower()

        if self.format not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported format: {self.format}. "
                f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
            )

    def parse(self) -> Dict[str, Any]:
        """
        Parse the book and extract all content

        Returns:
            Dictionary with metadata, toc, and chapters
        """
        if self.format in ['.epub', '.kepub']:
            return self._parse_epub()
        else:
            raise ValueError(f"Unsupported format: {self.format}")

    def _parse_epub(self) -> Dict[str, Any]:
        """Parse EPUB file"""
        with EPUBParser(self.file_path) as parser:
            metadata = parser.extract_metadata()
            toc = parser.extract_toc()
            chapters = parser.extract_chapters()

            return {
                'metadata': metadata.to_dict(),
                'toc': toc,
                'chapters': [ch.to_dict() for ch in chapters],
                'format': 'epub',
                'file_path': self.file_path
            }

    def search(self, query: str, case_sensitive: bool = False) -> List[Dict]:
        """
        Search for text across all chapters

        Args:
            query: Text to search for
            case_sensitive: Whether search should be case-sensitive

        Returns:
            List of matches with chapter info and context
        """
        book_data = self.parse()
        matches = []

        search_query = query if case_sensitive else query.lower()

        for chapter in book_data['chapters']:
            chapter_text = chapter['text'] if case_sensitive else chapter['text'].lower()

            if search_query in chapter_text:
                # Find context around match
                idx = chapter_text.find(search_query)
                start = max(0, idx - 100)
                end = min(len(chapter_text), idx + len(search_query) + 100)
                context = chapter['text'][start:end]

                matches.append({
                    'chapter_index': chapter['index'],
                    'chapter_title': chapter['title'],
                    'context': context,
                    'full_html': chapter['html']
                })

        return matches

    def get_chapter(self, chapter_index: int) -> Optional[Dict]:
        """
        Get a specific chapter by index

        Args:
            chapter_index: Index of the chapter (0-based)

        Returns:
            Chapter data or None if not found
        """
        book_data = self.parse()

        for chapter in book_data['chapters']:
            if chapter['index'] == chapter_index:
                return chapter

        return None
