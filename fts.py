import sqlite3

con = sqlite3.connect("/code/calibre-web/bin/full-text-search.db")
con.enable_load_extension(True)

# https://github.com/kovidgoyal/calibre/blob/master/src/calibre/library/sqlite.py#L237-L249
con.load_extension("/code/calibre-web/bin/sqlite_custom")

# https://github.com/kovidgoyal/calibre/blob/master/src/calibre/library/sqlite.py#L273
con.load_extension("/code/calibre-web/bin/sqlite_extension")

con.enable_load_extension(False)

res = con.execute("SELECT count(*) FROM books_fts WHERE books_fts MATCH 'airflow'").fetchone()

print(res)

# LD_LIBRARY_PATH=/code/calibre-web/bin/lib:$LD_LIBRARY_PATH uv run --no-project fts.py
