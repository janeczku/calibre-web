# Quick Start Guide

Get started with the Book Parsing Agent in 5 minutes!

## Installation

```bash
cd book_parsing_agent
pip install -r requirements.txt
```

## Run Examples

### 1. Quick Demo (Fastest way to see it in action)
```bash
python examples/quickstart.py
```

### 2. Basic Usage Example
```bash
python examples/basic_usage.py
```

### 3. Search Example
```bash
python examples/search_example.py
```

### 4. Interactive Agent
```bash
python agent.py sample_books/test_book.epub
```

## Basic Code Examples

### Parse a Book
```python
from book_parser import BookParser

parser = BookParser("path/to/your/book.epub")
book = parser.parse()

# Get metadata
print(f"Title: {book['metadata']['title']}")
print(f"Author: {book['metadata']['author']}")

# List chapters
for chapter in book['chapters']:
    print(f"{chapter['index']}: {chapter['title']}")
```

### Search in Book
```python
from book_parser import BookParser

parser = BookParser("path/to/your/book.epub")
matches = parser.search("python programming")

for match in matches:
    print(f"Found in: {match['chapter_title']}")
    print(f"Context: {match['context']}")
```

### Use the Agent
```python
from agent import BookParsingAgent

agent = BookParsingAgent("path/to/your/book.epub")

# Get summary
summary = agent.summarize_book()
print(f"Total words: {summary['total_words']}")
print(f"Total chapters: {summary['total_chapters']}")

# Find all tables
tables = agent.get_all_tables()
for table_info in tables:
    print(f"Table in {table_info['chapter_title']}")
    for row in table_info['table']['rows']:
        print(row)
```

### Extract Specific Chapter
```python
from agent import BookParsingAgent

agent = BookParsingAgent("book.epub")

# Get chapter 3
chapter = agent.get_chapter_content(2)  # 0-indexed

print(f"Title: {chapter['title']}")
print(f"Text: {chapter['text'][:500]}...")
print(f"Tables: {len(chapter['tables'])}")
```

### Interactive Mode
```python
from agent import BookParsingAgent

agent = BookParsingAgent("book.epub")
agent.interactive_query()  # Start interactive CLI
```

## Module Structure

```
book_parsing_agent/
├── README.md              # Full documentation
├── QUICKSTART.md          # This file
├── requirements.txt       # Dependencies
├── book_parser.py         # Core parsing module
├── agent.py              # Agent with analysis features
├── examples/
│   ├── quickstart.py     # Quick demo
│   ├── basic_usage.py    # Basic usage examples
│   └── search_example.py # Search examples
├── sample_books/
│   └── test_book.epub    # Sample EPUB for testing
└── tests/                # Tests directory
```

## What You Can Extract

- **Metadata**: Title, author, description, ISBN, tags, series, publisher, date
- **Table of Contents**: Full TOC with chapter titles and links
- **Chapters**: Full HTML content with structure preserved
- **Tables**: Data tables with rows and columns
- **Images**: Image references with metadata
- **Charts**: SVG charts and diagrams
- **Text**: Clean text extraction for search and analysis

## Common Use Cases

### 1. Build a Q&A System
```python
agent = BookParsingAgent("textbook.epub")

# User asks: "What chapter discusses neural networks?"
chapters = agent.find_chapters_with_keyword("neural networks")
# Feed chapter content to your LLM
```

### 2. Extract All Data
```python
agent = BookParsingAgent("research.epub")
tables = agent.get_all_tables()

# Convert to pandas DataFrame
import pandas as pd
for table_info in tables:
    df = pd.DataFrame(
        table_info['table']['rows'][1:],
        columns=table_info['table']['rows'][0]
    )
```

### 3. Search Specific Chapters
```python
agent = BookParsingAgent("manual.epub")
chapter = agent.get_chapter_by_title("Installation")

if "docker" in chapter['text'].lower():
    print("Found Docker installation instructions")
```

## Next Steps

1. Read the full [README.md](README.md) for complete API reference
2. Try parsing your own EPUB files
3. Integrate with your AI/LLM for intelligent book analysis
4. Export data to JSON for further processing

## Support

For issues or questions, see the main README.md file.
