# cps/crawler/crawler_service.py

from .gutenberg_fetcher import GutenbergFetcher
from .downloader import Downloader
from .saver import Saver
from .gutenberg_popular import GutenbergPopular


class CrawlerService:
    @staticmethod
    def import_books(book_ids=None, limit=10):
        results = []

        # 1️⃣ 如果没传 book_ids，自动抓热门书籍
        if not book_ids:
            book_ids = GutenbergPopular.fetch_top_book_ids(limit=limit)

        for book_id in book_ids:
            try:
                url = GutenbergFetcher.get_download_url(book_id)
                data = Downloader.download(url)
                filename = f"gutenberg_{book_id}.epub"
                path = Saver.save(data, filename)

                results.append({
                    "book_id": book_id,
                    "status": "success",
                    "path": path,
                    "message": "已下载，请使用 Calibre 桌面版导入"
                })

            except Exception as e:
                results.append({
                    "book_id": book_id,
                    "status": "failed",
                    "error": str(e)
                })

        return results
