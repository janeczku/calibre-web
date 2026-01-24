import sqlite3

con = sqlite3.connect("full-text-search.db")
con.enable_load_extension(True)

# https://github.com/kovidgoyal/calibre/blob/master/src/calibre/library/sqlite.py#L273
con.load_extension("bin/calibre/calibre-extensions/sqlite_extension")

con.enable_load_extension(False)

res = con.execute("SELECT count(*) FROM books_fts WHERE books_fts MATCH 'airflow'").fetchone()

print(res)

# LD_LIBRARY_PATH=bin/calibre/lib:$LD_LIBRARY_PATH uv run --no-project --python 3.11 fts.py
