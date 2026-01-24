import sqlite3
from pprint import pprint

fts = sqlite3.connect("full-text-search.db")
fts.enable_load_extension(True)

# https://github.com/kovidgoyal/calibre/blob/master/src/calibre/library/sqlite.py#L273
fts.load_extension("bin/calibre/calibre-extensions/sqlite_extension")
fts.enable_load_extension(False)

#res = con.execute("SELECT * FROM books_fts WHERE books_fts MATCH 'airflow'").fetchone()

sql = """
SELECT
  books_text.id, books_text.book, books_text.format,
  bm25(books_fts) AS rank
FROM books_fts
JOIN books_text ON books_text.id = books_fts.rowid
WHERE books_fts MATCH 'airflow'
ORDER BY rank
LIMIT 10
"""

pprint(fts.execute(sql).fetchall())

# LD_LIBRARY_PATH=bin/calibre/lib:$LD_LIBRARY_PATH uv run --no-project --python 3.11 fts.py
