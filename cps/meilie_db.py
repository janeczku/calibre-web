from . import logger
from datetime import datetime
from typing import Optional, List, Tuple, Dict
import meilisearch

log = logger.create()

def convert_sql_datetime_to_datetime(text: str) -> Optional[datetime]:
    if not text or type(text) != str:
        return None
    date_time_convert = None
    list_token: List[Tuple[str, str]] = [
        (".", "%Y-%m-%d %H:%M:%S"),
        ("+", "%Y-%m-%dT%H:%M:%S"),
        ("+", "%Y-%m-%dT%H:%M:%SZ"),
    ]
    for token, date_format in list_token:
        try:
            text = text.split(token)[0]
            date_time_convert = datetime.strptime(text, date_format)
            break
        except ValueError:
            pass

    return date_time_convert

class BookSearch:
    def __init__(self) -> None:
        self._client = meilisearch.Client("http://localhost:7700")

        self.index = self._client.index("books")

    def search(self, term, config):
        result = self.index.search(term)
        log.debug("%s search took: %f", term, result["processingTimeMs"])
        hits = result["hits"]
        for item in hits:
            item["last_modified"] = convert_sql_datetime_to_datetime(item["last_modified"])
        return hits

    def insert_book(self, db_book: Dict):
        self.index.add_documents([db_book])

    def delete_book(self, book_id: str):
        self.index.delete_document(book_id)
