# cps/crawler/gutenberg_popular.py

import re
import requests


class GutenbergPopular:
    TOP_URL = "https://www.gutenberg.org/browse/scores/top"

    @staticmethod
    def fetch_top_book_ids(limit=10):
        """
        从 Gutenberg 热门榜单页面获取书籍 ID
        """
        resp = requests.get(GutenbergPopular.TOP_URL, timeout=10)
        resp.raise_for_status()

        html = resp.text

        # 匹配 /ebooks/1342 这样的链接
        ids = re.findall(r"/ebooks/(\d+)", html)

        # 去重 + 保持顺序
        seen = set()
        book_ids = []
        for i in ids:
            if i not in seen:
                seen.add(i)
                book_ids.append(int(i))
            if len(book_ids) >= limit:
                break

        return book_ids
