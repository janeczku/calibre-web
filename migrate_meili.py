import sqlite3
import meilisearch


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

conn = sqlite3.connect('/Users/hai/Calibre Library/metadata.db')
conn.row_factory = dict_factory
cur = conn.cursor()



client = meilisearch.Client('http://localhost:7700')
index = client.index('books')
index.update_settings({
  'searchableAttributes': [
      'title',
      'author_sort'
]})

data = cur.execute("select * from books;").fetchall()

index.add_documents(data)