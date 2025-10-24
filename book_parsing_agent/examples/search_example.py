#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Search Example - Demonstrate search capabilities

This script shows how to search for content within books and chapters.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import BookParsingAgent


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
    print("SEARCH EXAMPLE - BOOK PARSING AGENT")
    print("="*70)

    # Initialize agent
    print(f"\nLoading book: {book_path}\n")
    agent = BookParsingAgent(book_path)

    # Example 1: Basic search
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Content Search")
    print("="*70)
    query = "growth"
    print(f"Searching for: '{query}'\n")

    matches = agent.search_content(query)
    for i, match in enumerate(matches, 1):
        print(f"{i}. Found in Chapter {match['chapter_index']}: {match['chapter_title']}")
        print(f"   Context: ...{match['context']}...")
        print()

    # Example 2: Find chapters with keyword
    print("\n" + "="*70)
    print("EXAMPLE 2: Find Chapters Containing Keyword")
    print("="*70)
    keyword = "table"
    print(f"Finding chapters with keyword: '{keyword}'\n")

    chapters_with_keyword = agent.find_chapters_with_keyword(keyword)
    for chapter_info in chapters_with_keyword:
        print(f"- Chapter {chapter_info['index']}: {chapter_info['title']}")
        print(f"  Occurrences: {chapter_info['occurrences']}")
        print()

    # Example 3: Search in specific chapter
    print("\n" + "="*70)
    print("EXAMPLE 3: Search Within Specific Chapter")
    print("="*70)
    chapter_idx = 1  # Chapter 2 (0-indexed)
    search_term = "revenue"
    print(f"Searching for '{search_term}' in chapter {chapter_idx}\n")

    result = agent.search_in_chapter(chapter_idx, search_term)
    if result and result.get('found'):
        print(f"Found in: {result['chapter']}")
        print(f"Chapter text preview:")
        print("-" * 70)
        print(result['text'][:500] + "...")
        print("-" * 70)
    else:
        print("Not found in this chapter")

    # Example 4: Find all tables
    print("\n" + "="*70)
    print("EXAMPLE 4: Extract All Tables")
    print("="*70)

    tables = agent.get_all_tables()
    print(f"Found {len(tables)} tables in the book\n")

    for i, table_info in enumerate(tables, 1):
        print(f"{i}. Chapter {table_info['chapter_index']}: {table_info['chapter_title']}")
        table = table_info['table']
        if table['caption']:
            print(f"   Caption: {table['caption']}")
        print(f"   Rows: {len(table['rows'])}, Columns: {len(table['rows'][0]) if table['rows'] else 0}")

        # Show table content
        if table['rows']:
            print(f"\n   Table content:")
            for row_idx, row in enumerate(table['rows'][:5], 1):  # Show first 5 rows
                print(f"     {row}")
            if len(table['rows']) > 5:
                print(f"     ... and {len(table['rows']) - 5} more rows")
        print()

    # Example 5: Chapter-by-chapter analysis
    print("\n" + "="*70)
    print("EXAMPLE 5: Chapter Analysis")
    print("="*70)

    for idx in range(len(agent.book_data['chapters'])):
        analysis = agent.analyze_chapter(idx)
        if 'error' not in analysis:
            print(f"\nChapter {analysis['chapter_index']}: {analysis['title']}")
            print(f"  Words: {analysis['word_count']}")
            print(f"  Tables: {analysis['table_count']}")
            print(f"  Images: {analysis['image_count']}")
            print(f"  Charts: {analysis['chart_count']}")

            if analysis['top_words']:
                print(f"  Top 5 words:")
                for word, count in analysis['top_words'][:5]:
                    print(f"    - {word}: {count}")

    # Example 6: Get chapter by title
    print("\n" + "="*70)
    print("EXAMPLE 6: Find Chapter by Title")
    print("="*70)
    title_query = "conclusion"
    print(f"Searching for chapter with title containing: '{title_query}'\n")

    chapter = agent.get_chapter_by_title(title_query)
    if chapter:
        print(f"Found: Chapter {chapter['index']}: {chapter['title']}")
        print(f"Word count: {len(chapter['text'].split())}")
        print(f"Tables: {len(chapter['tables'])}")
        print(f"\nFirst 200 characters:")
        print(chapter['text'][:200] + "...")
    else:
        print("Chapter not found")

    # Example 7: Book summary
    print("\n" + "="*70)
    print("EXAMPLE 7: Book Summary")
    print("="*70)

    summary = agent.summarize_book()
    print(f"\nTitle: {summary['title']}")
    print(f"Author: {summary['author']}")
    print(f"Total chapters: {summary['total_chapters']}")
    print(f"Total words: {summary['total_words']:,}")
    print(f"Total tables: {summary['total_tables']}")
    print(f"Total images: {summary['total_images']}")
    print(f"Total charts: {summary['total_charts']}")
    print(f"Has TOC: {summary['has_toc']}")

    print("\n" + "="*70)
    print("Search examples completed successfully!")
    print("="*70)


if __name__ == '__main__':
    main()
