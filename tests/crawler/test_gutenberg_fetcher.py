# tests/crawler/test_gutenberg_fetcher.py

import os
import sys
import unittest
import importlib.util

# 将项目根目录添加到 sys.path
path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, path)

# 创建 cps.crawler 包结构
if 'cps' not in sys.modules:
    cps_module = type(sys)('cps')
    cps_module.__path__ = [os.path.join(path, "cps")]
    sys.modules['cps'] = cps_module

if 'cps.crawler' not in sys.modules:
    crawler_module = type(sys)('cps.crawler')
    crawler_module.__path__ = [os.path.join(path, "cps", "crawler")]
    crawler_module.__package__ = 'cps.crawler'
    sys.modules['cps.crawler'] = crawler_module

# 直接导入模块以避免加载 cps/__init__.py
spec = importlib.util.spec_from_file_location(
    "cps.crawler.gutenberg_fetcher",
    os.path.join(path, "cps", "crawler", "gutenberg_fetcher.py")
)
gutenberg_fetcher_module = importlib.util.module_from_spec(spec)
gutenberg_fetcher_module.__package__ = 'cps.crawler'
sys.modules['cps.crawler.gutenberg_fetcher'] = gutenberg_fetcher_module
spec.loader.exec_module(gutenberg_fetcher_module)

GutenbergFetcher = gutenberg_fetcher_module.GutenbergFetcher


class TestGutenbergFetcher(unittest.TestCase):

    def test_get_download_url(self):
        book_id = 1342
        url = GutenbergFetcher.get_download_url(book_id)

        self.assertIsInstance(url, str)
        self.assertIn(str(book_id), url)
        self.assertTrue(url.endswith(".epub.noimages"))


if __name__ == "__main__":
    unittest.main()
