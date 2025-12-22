# cps/crawler/gutenberg_fetcher.py

class GutenbergFetcher:
    BASE_URL = "https://www.gutenberg.org/ebooks"

    @staticmethod
    def get_download_url(book_id: int) -> str:
        """
        构造 Project Gutenberg EPUB 下载地址
        """
        return f"{GutenbergFetcher.BASE_URL}/{book_id}.epub.noimages"
