#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick Start - Fastest way to get started with the book parser

Run this script to see a quick demonstration of the key features.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from book_parser import BookParser
from agent import BookParsingAgent


def demo_parser():
    """Demonstrate the basic parser"""
    print("\n" + "="*70)
    print("QUICK START: Book Parser")
    print("="*70 + "\n")

    # Get book path
    book_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'sample_books',
        'test_book.epub'
    )

    # Parse book
    parser = BookParser(book_path)
    book_data = parser.parse()

    # Show key information
    print(f"📚 Book: {book_data['metadata']['title']}")
    print(f"✍️  Author: {book_data['metadata']['author']}")
    print(f"📖 Chapters: {len(book_data['chapters'])}")
    print(f"📊 Tables: {sum(len(ch['tables']) for ch in book_data['chapters'])}")
    print(f"🖼️  Images: {sum(len(ch['images']) for ch in book_data['chapters'])}")

    # Show TOC
    print(f"\n📑 Table of Contents:")
    for i, entry in enumerate(book_data['toc'], 1):
        print(f"  {i}. {entry['title']}")

    # Quick search
    print(f"\n🔍 Search for 'data':")
    matches = parser.search("data")
    print(f"  Found in {len(matches)} chapters")

    # Show a table
    for chapter in book_data['chapters']:
        if chapter['tables']:
            table = chapter['tables'][0]
            print(f"\n📊 Sample table from '{chapter['title']}':")
            if table['caption']:
                print(f"  Caption: {table['caption']}")
            for i, row in enumerate(table['rows'][:3], 1):
                print(f"  {row}")
            break


def demo_agent():
    """Demonstrate the agent"""
    print("\n" + "="*70)
    print("QUICK START: Book Parsing Agent")
    print("="*70 + "\n")

    # Get book path
    book_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'sample_books',
        'test_book.epub'
    )

    # Initialize agent
    print("Initializing agent...\n")
    agent = BookParsingAgent(book_path)

    # Summary
    print("\n📊 Book Summary:")
    summary = agent.summarize_book()
    print(f"  Total words: {summary['total_words']:,}")
    print(f"  Total tables: {summary['total_tables']}")
    print(f"  Total images: {summary['total_images']}")

    # Chapter analysis
    print(f"\n📖 Chapter 2 Analysis:")
    analysis = agent.analyze_chapter(1)  # Index 1 = Chapter 2
    print(f"  Title: {analysis['title']}")
    print(f"  Words: {analysis['word_count']}")
    print(f"  Tables: {analysis['table_count']}")
    print(f"  Top 3 words:")
    for word, count in analysis['top_words'][:3]:
        print(f"    - {word}: {count}")


def main():
    """Run both demos"""
    print("\n" + "="*70)
    print("🚀 BOOK PARSING AGENT - QUICK START")
    print("="*70)

    try:
        demo_parser()
        demo_agent()

        print("\n" + "="*70)
        print("✅ Quick start completed!")
        print("="*70)
        print("\nNext steps:")
        print("  • Try: python examples/basic_usage.py")
        print("  • Try: python examples/search_example.py")
        print("  • Try: python agent.py sample_books/test_book.epub")
        print("="*70 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
