#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Book Parsing Agent - Intelligent agent for analyzing and querying book content

This agent can:
- Answer questions about book content
- Search for specific information
- Extract structured data (tables, lists, etc.)
- Summarize chapters or sections
"""

import json
from typing import List, Dict, Optional, Any
from book_parser import BookParser


class BookParsingAgent:
    """
    Intelligent agent for book analysis and querying

    This is a simple example implementation that demonstrates how to use
    the book parser for various tasks. In a real implementation, you would
    integrate this with an LLM (like GPT, Claude, etc.) for more sophisticated
    natural language understanding.
    """

    def __init__(self, book_path: str):
        """
        Initialize the agent with a book

        Args:
            book_path: Path to the book file (EPUB)
        """
        self.parser = BookParser(book_path)
        self.book_data = None
        self._load_book()

    def _load_book(self):
        """Load and parse the book"""
        print("Loading book...")
        self.book_data = self.parser.parse()
        print(f"Book loaded: {self.book_data['metadata']['title']}")
        print(f"Author: {self.book_data['metadata']['author']}")
        print(f"Chapters: {len(self.book_data['chapters'])}")

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get book metadata

        Returns:
            Dictionary with all metadata fields
        """
        return self.book_data['metadata']

    def get_table_of_contents(self) -> List[Dict[str, str]]:
        """
        Get the table of contents

        Returns:
            List of TOC entries
        """
        return self.book_data['toc']

    def search_content(self, query: str, case_sensitive: bool = False) -> List[Dict]:
        """
        Search for text across the entire book

        Args:
            query: Search query
            case_sensitive: Whether to perform case-sensitive search

        Returns:
            List of matches with context
        """
        print(f"Searching for: '{query}'...")
        matches = self.parser.search(query, case_sensitive)
        print(f"Found {len(matches)} matches")
        return matches

    def search_in_chapter(self, chapter_index: int, query: str) -> Optional[Dict]:
        """
        Search within a specific chapter

        Args:
            chapter_index: Index of the chapter
            query: Search query

        Returns:
            Match information or None
        """
        chapter = self.book_data['chapters'][chapter_index]
        query_lower = query.lower()

        if query_lower in chapter['text'].lower():
            return {
                'found': True,
                'chapter': chapter['title'],
                'chapter_index': chapter_index,
                'text': chapter['text']
            }

        return None

    def get_chapter_content(self, chapter_index: int) -> Optional[Dict]:
        """
        Get full content of a specific chapter

        Args:
            chapter_index: Index of the chapter

        Returns:
            Chapter data with all content
        """
        if 0 <= chapter_index < len(self.book_data['chapters']):
            return self.book_data['chapters'][chapter_index]
        return None

    def get_all_tables(self) -> List[Dict]:
        """
        Extract all tables from the book

        Returns:
            List of tables with their location and content
        """
        all_tables = []

        for chapter in self.book_data['chapters']:
            if chapter['tables']:
                for table in chapter['tables']:
                    all_tables.append({
                        'chapter_index': chapter['index'],
                        'chapter_title': chapter['title'],
                        'table': table
                    })

        return all_tables

    def get_all_images(self) -> List[Dict]:
        """
        Extract all images from the book

        Returns:
            List of images with their location and metadata
        """
        all_images = []

        for chapter in self.book_data['chapters']:
            if chapter['images']:
                for image in chapter['images']:
                    all_images.append({
                        'chapter_index': chapter['index'],
                        'chapter_title': chapter['title'],
                        'image': image
                    })

        return all_images

    def summarize_book(self) -> Dict[str, Any]:
        """
        Generate a basic summary of the book structure

        Returns:
            Summary information
        """
        metadata = self.book_data['metadata']
        chapters = self.book_data['chapters']

        # Count content elements
        total_tables = sum(len(ch['tables']) for ch in chapters)
        total_images = sum(len(ch['images']) for ch in chapters)
        total_charts = sum(len(ch['charts']) for ch in chapters)

        # Calculate text statistics
        total_words = sum(len(ch['text'].split()) for ch in chapters)

        summary = {
            'title': metadata['title'],
            'author': metadata['author'],
            'total_chapters': len(chapters),
            'total_words': total_words,
            'total_tables': total_tables,
            'total_images': total_images,
            'total_charts': total_charts,
            'has_toc': len(self.book_data['toc']) > 0,
            'chapters': [
                {
                    'index': ch['index'],
                    'title': ch['title'],
                    'word_count': len(ch['text'].split()),
                    'table_count': len(ch['tables']),
                    'image_count': len(ch['images'])
                }
                for ch in chapters
            ]
        }

        return summary

    def analyze_chapter(self, chapter_index: int) -> Dict[str, Any]:
        """
        Analyze a specific chapter

        Args:
            chapter_index: Index of the chapter

        Returns:
            Analysis results
        """
        chapter = self.get_chapter_content(chapter_index)

        if not chapter:
            return {'error': 'Chapter not found'}

        words = chapter['text'].split()
        word_count = len(words)

        # Simple word frequency analysis
        word_freq = {}
        for word in words:
            word_lower = word.lower().strip('.,!?;:')
            if len(word_lower) > 3:  # Only count words longer than 3 chars
                word_freq[word_lower] = word_freq.get(word_lower, 0) + 1

        # Get top 10 most common words
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            'chapter_index': chapter_index,
            'title': chapter['title'],
            'word_count': word_count,
            'table_count': len(chapter['tables']),
            'image_count': len(chapter['images']),
            'chart_count': len(chapter['charts']),
            'top_words': top_words,
            'has_tables': len(chapter['tables']) > 0,
            'has_images': len(chapter['images']) > 0
        }

    def extract_tables_from_chapter(self, chapter_index: int) -> List[Dict]:
        """
        Extract all tables from a specific chapter

        Args:
            chapter_index: Index of the chapter

        Returns:
            List of tables with data
        """
        chapter = self.get_chapter_content(chapter_index)

        if not chapter:
            return []

        return chapter['tables']

    def find_chapters_with_keyword(self, keyword: str) -> List[Dict]:
        """
        Find all chapters containing a specific keyword

        Args:
            keyword: Keyword to search for

        Returns:
            List of chapters containing the keyword
        """
        keyword_lower = keyword.lower()
        matching_chapters = []

        for chapter in self.book_data['chapters']:
            if keyword_lower in chapter['text'].lower():
                matching_chapters.append({
                    'index': chapter['index'],
                    'title': chapter['title'],
                    'occurrences': chapter['text'].lower().count(keyword_lower)
                })

        return matching_chapters

    def export_to_json(self, output_path: str, include_html: bool = False):
        """
        Export book data to JSON

        Args:
            output_path: Path to output JSON file
            include_html: Whether to include full HTML content
        """
        export_data = self.book_data.copy()

        if not include_html:
            # Remove HTML to reduce file size
            for chapter in export_data['chapters']:
                chapter.pop('html', None)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        print(f"Book data exported to: {output_path}")

    def get_chapter_by_title(self, title_query: str) -> Optional[Dict]:
        """
        Get chapter by searching for title

        Args:
            title_query: Partial or full chapter title

        Returns:
            Chapter data or None
        """
        title_query_lower = title_query.lower()

        for chapter in self.book_data['chapters']:
            if chapter['title'] and title_query_lower in chapter['title'].lower():
                return chapter

        return None

    def interactive_query(self):
        """
        Interactive mode for querying the book

        This provides a simple CLI interface for exploring the book
        """
        print("\n" + "="*60)
        print("Book Parsing Agent - Interactive Mode")
        print("="*60)
        print(f"\nBook: {self.book_data['metadata']['title']}")
        print(f"Author: {self.book_data['metadata']['author']}\n")

        while True:
            print("\nAvailable commands:")
            print("  1. Search content")
            print("  2. List chapters")
            print("  3. View chapter")
            print("  4. Find tables")
            print("  5. Find images")
            print("  6. Book summary")
            print("  7. Analyze chapter")
            print("  8. Exit")

            choice = input("\nEnter command number: ").strip()

            if choice == '1':
                query = input("Enter search query: ")
                matches = self.search_content(query)
                for i, match in enumerate(matches[:5], 1):  # Show first 5
                    print(f"\n{i}. Chapter {match['chapter_index']}: {match['chapter_title']}")
                    print(f"   Context: ...{match['context']}...")
                if len(matches) > 5:
                    print(f"\n... and {len(matches) - 5} more matches")

            elif choice == '2':
                toc = self.get_table_of_contents()
                print("\nTable of Contents:")
                for i, entry in enumerate(toc, 1):
                    print(f"  {i}. {entry['title']}")

            elif choice == '3':
                idx = int(input("Enter chapter index: "))
                chapter = self.get_chapter_content(idx)
                if chapter:
                    print(f"\nChapter: {chapter['title']}")
                    print(f"Word count: {len(chapter['text'].split())}")
                    print(f"Tables: {len(chapter['tables'])}")
                    print(f"Images: {len(chapter['images'])}")
                    print(f"\nFirst 500 characters:\n{chapter['text'][:500]}...")
                else:
                    print("Chapter not found")

            elif choice == '4':
                tables = self.get_all_tables()
                print(f"\nFound {len(tables)} tables:")
                for i, table_info in enumerate(tables[:5], 1):
                    print(f"\n{i}. Chapter {table_info['chapter_index']}: {table_info['chapter_title']}")
                    print(f"   Rows: {len(table_info['table']['rows'])}")
                    if table_info['table']['caption']:
                        print(f"   Caption: {table_info['table']['caption']}")

            elif choice == '5':
                images = self.get_all_images()
                print(f"\nFound {len(images)} images:")
                for i, img_info in enumerate(images[:10], 1):
                    print(f"\n{i}. Chapter {img_info['chapter_index']}: {img_info['chapter_title']}")
                    print(f"   Source: {img_info['image']['src']}")
                    if img_info['image']['alt']:
                        print(f"   Alt: {img_info['image']['alt']}")

            elif choice == '6':
                summary = self.summarize_book()
                print("\nBook Summary:")
                print(f"  Title: {summary['title']}")
                print(f"  Author: {summary['author']}")
                print(f"  Chapters: {summary['total_chapters']}")
                print(f"  Total words: {summary['total_words']}")
                print(f"  Tables: {summary['total_tables']}")
                print(f"  Images: {summary['total_images']}")
                print(f"  Charts: {summary['total_charts']}")

            elif choice == '7':
                idx = int(input("Enter chapter index: "))
                analysis = self.analyze_chapter(idx)
                if 'error' not in analysis:
                    print(f"\nChapter Analysis:")
                    print(f"  Title: {analysis['title']}")
                    print(f"  Word count: {analysis['word_count']}")
                    print(f"  Tables: {analysis['table_count']}")
                    print(f"  Images: {analysis['image_count']}")
                    print(f"\n  Top words:")
                    for word, count in analysis['top_words']:
                        print(f"    {word}: {count}")
                else:
                    print("Chapter not found")

            elif choice == '8':
                print("\nGoodbye!")
                break

            else:
                print("Invalid command")


def main():
    """Example usage of the BookParsingAgent"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python agent.py <path_to_epub>")
        sys.exit(1)

    book_path = sys.argv[1]

    # Initialize agent
    agent = BookParsingAgent(book_path)

    # Example: Get book summary
    print("\n" + "="*60)
    print("BOOK SUMMARY")
    print("="*60)
    summary = agent.summarize_book()
    print(f"Title: {summary['title']}")
    print(f"Author: {summary['author']}")
    print(f"Chapters: {summary['total_chapters']}")
    print(f"Total words: {summary['total_words']:,}")
    print(f"Tables: {summary['total_tables']}")
    print(f"Images: {summary['total_images']}")

    # Example: Search
    print("\n" + "="*60)
    print("SEARCH EXAMPLE")
    print("="*60)
    query = input("Enter a word to search for (or press Enter to skip): ").strip()
    if query:
        matches = agent.search_content(query)
        if matches:
            print(f"\nFound '{query}' in {len(matches)} chapters:")
            for match in matches[:3]:
                print(f"\n- Chapter {match['chapter_index']}: {match['chapter_title']}")
                print(f"  ...{match['context']}...")
        else:
            print(f"\nNo matches found for '{query}'")

    # Start interactive mode
    print("\n")
    start_interactive = input("Start interactive mode? (y/n): ").strip().lower()
    if start_interactive == 'y':
        agent.interactive_query()


if __name__ == '__main__':
    main()
