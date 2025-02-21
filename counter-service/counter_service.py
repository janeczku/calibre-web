import sqlite3
import os

# Path to the existing Calibre-Web database
DB_PATH = os.path.join(os.getcwd(), "library", "metadata.db")

def custom_title_sort(s):
    """ Dummy function to replace Calibre's missing SQLite title_sort """
    return s.lower() if s else ""

def get_db_connection():
    """ Create SQLite connection and register custom functions """
    conn = sqlite3.connect(DB_PATH)
    conn.create_function("title_sort", 1, custom_title_sort)  # Register custom function
    return conn

def init_db():
    """Ensure the 'download_count' column exists in the 'books' table."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(books)")
    columns = [col[1] for col in cursor.fetchall()]

    if "download_count" not in columns:
        cursor.execute("ALTER TABLE books ADD COLUMN download_count INTEGER DEFAULT 0")
        conn.commit()

    conn.close()

init_db()  # Run this when the microservice starts

from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.post("/increment_download/{book_id}")
def increment_download_count(book_id: int):
    """Increase the download count for a book."""
    conn = get_db_connection()  # Get connection with custom functions
    cursor = conn.cursor()

    # Check if the book exists
    cursor.execute("SELECT id FROM books WHERE id = ?", (book_id,))
    book = cursor.fetchone()

    if not book:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Book with ID {book_id} does not exist.")

    cursor.execute(
        "UPDATE books SET download_count = COALESCE(download_count, 0) + 1 WHERE id = ?",
        (book_id,)
    )
    conn.commit()
    conn.close()

    return {"message": f"Download count incremented for book {book_id}"}

@app.get("/download_count/{book_id}")
def get_download_count(book_id: int):
    """Retrieve the download count for a book."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT download_count FROM books WHERE id = ?", (book_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Book with ID {book_id} does not exist.")

    return {"book_id": book_id, "download_count": row[0]}
