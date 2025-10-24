#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Basic Usage Example - Book Parser

This script demonstrates basic usage of the book parser module.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from book_parser import BookParser


def main():
    # Path to sample book
    book_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'sample_books',
        'test_book.epub'
    )

    if not os.path.exists(book_path):
        print(f"Error: Book not found at {book_path}")
        sys.exit(1)

    print("="*70)
    print("BASIC USAGE EXAMPLE - BOOK PARSER")
    print("="*70)

    # Initialize parser
    print(f"\n1. Initializing parser for: {book_path}\n")
    parser = BookParser(book_path)

    # Parse the book
    print("2. Parsing book...\n")
    book_data = parser.parse()

    # Display metadata
    print("="*70)
    print("METADATA")
    print("="*70)
    metadata = book_data['metadata']
    print(f"Title:            {metadata['title']}")
    print(f"Author:           {metadata['author']}")
    print(f"Description:      {metadata['description']}")
    print(f"Language:         {metadata['language']}")
    print(f"Publisher:        {metadata['publisher']}")
    print(f"Publication Date: {metadata['publication_date']}")
    print(f"ISBN:             {metadata['isbn']}")
    print(f"Tags:             {', '.join(metadata['tags'])}")
    if metadata['series']:
        print(f"Series:           {metadata['series']} #{metadata['series_index']}")

    # Display Table of Contents
    print("\n" + "="*70)
    print("TABLE OF CONTENTS")
    print("="*70)
    toc = book_data['toc']
    for i, entry in enumerate(toc, 1):
        print(f"{i}. {entry['title']}")
        print(f"   File: {entry['href']}")

    # Display chapter information
    print("\n" + "="*70)
    print("CHAPTERS")
    print("="*70)
    chapters = book_data['chapters']
    print(f"Total chapters: {len(chapters)}\n")

    for chapter in chapters:
        print(f"Chapter {chapter['index']}: {chapter['title'] or 'Untitled'}")
        print(f"  File: {chapter['file']}")
        print(f"  Word count: {len(chapter['text'].split())}")
        print(f"  Tables: {len(chapter['tables'])}")
        print(f"  Images: {len(chapter['images'])}")
        print(f"  Charts: {len(chapter['charts'])}")
        print()

    # Show first chapter content preview
    print("="*70)
    print("FIRST CHAPTER PREVIEW")
    print("="*70)
    if chapters:
        first_chapter = chapters[0]
        print(f"Title: {first_chapter['title']}")
        print(f"\nFirst 300 characters of text:")
        print("-" * 70)
        print(first_chapter['text'][:300] + "...")
        print("-" * 70)

    # Display tables if any
    print("\n" + "="*70)
    print("TABLES IN BOOK")
    print("="*70)
    total_tables = 0
    for chapter in chapters:
        if chapter['tables']:
            total_tables += len(chapter['tables'])
            print(f"\nChapter {chapter['index']}: {chapter['title']}")
            for i, table in enumerate(chapter['tables'], 1):
                print(f"\n  Table {i}:")
                if table['caption']:
                    print(f"    Caption: {table['caption']}")
                print(f"    Rows: {len(table['rows'])}")
                print(f"    Columns: {len(table['rows'][0]) if table['rows'] else 0}")

                # Show table data
                if table['rows']:
                    print(f"\n    Data preview:")
                    for row_idx, row in enumerate(table['rows'][:3]):  # Show first 3 rows
                        print(f"      Row {row_idx + 1}: {row}")
                    if len(table['rows']) > 3:
                        print(f"      ... and {len(table['rows']) - 3} more rows")

    if total_tables == 0:
        print("No tables found in this book.")

    # Search example
    print("\n" + "="*70)
    print("SEARCH EXAMPLE")
    print("="*70)
    search_query = "data"
    print(f"Searching for: '{search_query}'\n")

    matches = parser.search(search_query, case_sensitive=False)
    print(f"Found {len(matches)} matches\n")

    for i, match in enumerate(matches[:3], 1):  # Show first 3 matches
        print(f"{i}. Chapter {match['chapter_index']}: {match['chapter_title']}")
        print(f"   Context: ...{match['context']}...")
        print()

    print("="*70)
    print("Example completed successfully!")
    print("="*70)


if __name__ == '__main__':
    main()
