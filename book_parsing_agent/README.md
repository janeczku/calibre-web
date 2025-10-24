# Book Parsing Agent

A powerful, standalone Python module for parsing and analyzing EPUB books. Extract metadata, table of contents, chapter content, tables, images, and charts with full structure preservation.

## Features

- **Metadata Extraction**: Title, author, description, ISBN, tags, series, publisher, and more
- **Table of Contents**: Support for both EPUB2 (NCX) and EPUB3 (NAV) formats
- **Chapter Content**: Full HTML content preservation with structure
- **Tables**: Extract tables with data and captions
- **Images**: Extract image references with metadata
- **Charts**: Extract SVG charts and diagrams
- **Search**: Full-text search across chapters
- **Structure Preservation**: Maintain book structure for chapter-specific analysis

## Installation

### Requirements

- Python 3.7+
- lxml (for XML/HTML parsing)

### Setup

1. Clone or download this module:
```bash
cd book_parsing_agent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install lxml>=4.9.1
```

## Quick Start

The fastest way to get started:

```bash
python examples/quickstart.py
```

This will demonstrate the key features using the included sample book.

## Usage

### Basic Usage - Book Parser

```python
from book_parser import BookParser

# Initialize parser
parser = BookParser("path/to/book.epub")

# Parse the book
book_data = parser.parse()

# Access metadata
print(book_data['metadata']['title'])
print(book_data['metadata']['author'])

# Access table of contents
for entry in book_data['toc']:
    print(f"{entry['title']} -> {entry['href']}")

# Access chapters
for chapter in book_data['chapters']:
    print(f"Chapter {chapter['index']}: {chapter['title']}")
    print(f"  Word count: {len(chapter['text'].split())}")
    print(f"  Tables: {len(chapter['tables'])}")
    print(f"  Images: {len(chapter['images'])}")

# Search across the book
matches = parser.search("algorithm")
for match in matches:
    print(f"Found in: {match['chapter_title']}")
    print(f"Context: {match['context']}")
```

### Agent Usage - Book Parsing Agent

The agent provides higher-level functionality for book analysis:

```python
from agent import BookParsingAgent

# Initialize agent
agent = BookParsingAgent("path/to/book.epub")

# Get book summary
summary = agent.summarize_book()
print(f"Total words: {summary['total_words']}")
print(f"Total tables: {summary['total_tables']}")

# Search for content
matches = agent.search_content("machine learning")

# Get all tables
tables = agent.get_all_tables()
for table_info in tables:
    table = table_info['table']
    print(f"Table in {table_info['chapter_title']}")
    print(f"Rows: {len(table['rows'])}")

# Analyze specific chapter
analysis = agent.analyze_chapter(2)
print(f"Chapter: {analysis['title']}")
print(f"Top words: {analysis['top_words'][:5]}")

# Find chapters with keyword
chapters = agent.find_chapters_with_keyword("introduction")

# Interactive mode
agent.interactive_query()
```

## Examples

Run the included examples to see all features:

### 1. Basic Usage Example
```bash
python examples/basic_usage.py
```

Shows:
- Metadata extraction
- Table of contents
- Chapter information
- Table extraction
- Basic search

### 2. Search Example
```bash
python examples/search_example.py
```

Demonstrates:
- Full-text search
- Chapter-specific search
- Finding chapters by keyword
- Extracting all tables
- Chapter analysis
- Finding chapters by title

### 3. Interactive Agent
```bash
python agent.py sample_books/test_book.epub
```

Provides:
- Interactive CLI interface
- Search content
- View chapters
- Find tables and images
- Book summary
- Chapter analysis

## API Reference

### BookParser Class

#### `__init__(file_path: str)`
Initialize parser with EPUB file path.

#### `parse() -> Dict[str, Any]`
Parse the book and return complete data structure.

Returns:
```python
{
    'metadata': {...},      # Book metadata
    'toc': [...],          # Table of contents
    'chapters': [...],     # All chapters with content
    'format': 'epub',      # Book format
    'file_path': '...'     # Path to file
}
```

#### `search(query: str, case_sensitive: bool = False) -> List[Dict]`
Search for text across all chapters.

#### `get_chapter(chapter_index: int) -> Optional[Dict]`
Get specific chapter by index.

### BookParsingAgent Class

#### `__init__(book_path: str)`
Initialize agent with book file.

#### `get_metadata() -> Dict[str, Any]`
Get book metadata.

#### `get_table_of_contents() -> List[Dict[str, str]]`
Get table of contents.

#### `search_content(query: str, case_sensitive: bool = False) -> List[Dict]`
Search across entire book.

#### `search_in_chapter(chapter_index: int, query: str) -> Optional[Dict]`
Search within specific chapter.

#### `get_chapter_content(chapter_index: int) -> Optional[Dict]`
Get full chapter content.

#### `get_all_tables() -> List[Dict]`
Extract all tables from the book.

#### `get_all_images() -> List[Dict]`
Extract all images from the book.

#### `summarize_book() -> Dict[str, Any]`
Generate book summary with statistics.

#### `analyze_chapter(chapter_index: int) -> Dict[str, Any]`
Analyze specific chapter (word count, top words, etc.).

#### `find_chapters_with_keyword(keyword: str) -> List[Dict]`
Find chapters containing keyword.

#### `export_to_json(output_path: str, include_html: bool = False)`
Export book data to JSON.

#### `get_chapter_by_title(title_query: str) -> Optional[Dict]`
Get chapter by searching title.

#### `interactive_query()`
Start interactive CLI mode.

## Data Structures

### Metadata
```python
{
    'title': str,
    'author': str,
    'description': str,
    'language': str,
    'publisher': str,
    'publication_date': str,
    'isbn': str,
    'tags': List[str],
    'series': str,
    'series_index': str
}
```

### Chapter
```python
{
    'index': int,
    'file': str,
    'title': Optional[str],
    'html': str,              # Full HTML content
    'text': str,              # Extracted text
    'tables': List[Table],
    'images': List[Image],
    'charts': List[str]       # SVG content
}
```

### Table
```python
{
    'html': str,              # Full table HTML
    'rows': List[List[str]],  # Table data as 2D array
    'caption': str
}
```

### Image
```python
{
    'src': str,               # Image file path
    'alt': str,
    'title': str,
    'caption': str
}
```

## Use Cases

### 1. Build a Question-Answering Agent

```python
from agent import BookParsingAgent

agent = BookParsingAgent("textbook.epub")

# User asks: "What chapter discusses neural networks?"
chapters = agent.find_chapters_with_keyword("neural networks")
for ch in chapters:
    print(f"Chapter {ch['index']}: {ch['title']}")
    content = agent.get_chapter_content(ch['index'])
    # Feed content['text'] to your LLM for answering
```

### 2. Extract All Data Tables

```python
from agent import BookParsingAgent

agent = BookParsingAgent("research_paper.epub")

# Get all tables
tables = agent.get_all_tables()
for table_info in tables:
    table = table_info['table']
    # Process table['rows'] for data analysis
    import pandas as pd
    df = pd.DataFrame(table['rows'][1:], columns=table['rows'][0])
    print(df)
```

### 3. Chapter-Specific Search

```python
from agent import BookParsingAgent

agent = BookParsingAgent("manual.epub")

# Search only in "Installation" chapter
install_chapter = agent.get_chapter_by_title("Installation")
if install_chapter:
    if "docker" in install_chapter['text'].lower():
        print("This book covers Docker installation")
        # Extract relevant section
```

### 4. Export for LLM Context

```python
from book_parser import BookParser

parser = BookParser("book.epub")
book_data = parser.parse()

# Get specific chapter for LLM context
chapter = book_data['chapters'][3]

context = f"""
Book: {book_data['metadata']['title']}
Chapter: {chapter['title']}

Content:
{chapter['text']}

Tables in this chapter: {len(chapter['tables'])}
"""

# Feed context to your LLM
```

## Architecture

The module consists of two main components:

1. **book_parser.py**: Low-level parser for EPUB files
   - `EPUBParser`: Handles EPUB file structure
   - `BookParser`: Main interface for parsing books
   - Data classes: `BookMetadata`, `ChapterContent`, `TableContent`, `ImageContent`

2. **agent.py**: High-level agent for book analysis
   - `BookParsingAgent`: Intelligent wrapper with analysis capabilities
   - Search, summarization, and extraction features
   - Interactive CLI mode

## Supported Formats

Currently supports:
- EPUB (.epub)
- KEPUB (.kepub) - Kobo EPUB format

Future support planned for:
- PDF (.pdf) - with text extraction
- MOBI (.mobi)
- AZW3 (.azw3)

## How It Works

1. **EPUB Structure**: EPUB files are ZIP archives containing XHTML/HTML files
2. **OPF Parsing**: Extracts metadata and structure from OPF (Open Package Format) file
3. **TOC Extraction**: Parses NCX (EPUB2) or NAV (EPUB3) for table of contents
4. **Chapter Reading**: Reads each XHTML file in spine order
5. **Content Extraction**: Uses lxml to parse HTML and extract structured data
6. **Structure Preservation**: Maintains original HTML for tables, images, and formatting

## Limitations

- Currently only supports EPUB format
- PDF support is planned but not yet implemented
- Does not handle DRM-protected books
- Large books (>1000 chapters) may require memory optimization
- SVG chart extraction is basic (full SVG content only, no rasterization)

## Contributing

Contributions welcome! Areas for improvement:

- Add PDF support with text extraction
- Improve chart/diagram extraction
- Add support for MOBI/AZW3 formats
- Optimize memory usage for large books
- Add chapter segmentation for very long chapters
- Improve table parsing for complex layouts

## Testing

Test with the included sample book:

```bash
# Quick test
python examples/quickstart.py

# Full test suite
python examples/basic_usage.py
python examples/search_example.py
python agent.py sample_books/test_book.epub
```

## License

This module is part of the Calibre-Web project and follows the same license.

## Credits

Based on the book parsing functionality from [Calibre-Web](https://github.com/janeczku/calibre-web).

## Troubleshooting

### lxml installation fails
On Ubuntu/Debian:
```bash
sudo apt-get install libxml2-dev libxslt-dev python3-dev
pip install lxml
```

On macOS:
```bash
brew install libxml2 libxslt
pip install lxml
```

### "Failed to parse EPUB structure" error
- Ensure the EPUB file is valid (not corrupted)
- Check that it's not DRM-protected
- Verify the file is actually EPUB format (not renamed PDF)

### Memory issues with large books
- Process chapters one at a time instead of parsing entire book
- Use `get_chapter()` method to load chapters on demand
- Consider implementing pagination for very large chapters

## Contact

For issues and questions, please refer to the main Calibre-Web project.
