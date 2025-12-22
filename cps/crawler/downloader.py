# cps/crawler/downloader.py

import requests

class Downloader:
    @staticmethod
    def download(url: str) -> bytes:
        """
        下载电子书并返回二进制内容
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (CalibreWebCrawler)"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.content
