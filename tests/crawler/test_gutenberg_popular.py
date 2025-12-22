# tests/crawler/test_gutenberg_popular.py

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import importlib.util

# 将项目根目录添加到 sys.path
path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, path)

# 在导入模块之前，先 mock requests 模块
sys.modules['requests'] = MagicMock()

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
    # 将 crawler 模块作为属性添加到 cps 模块，以便 @patch 装饰器可以访问
    sys.modules['cps'].crawler = crawler_module

# 直接导入模块以避免加载 cps/__init__.py
spec = importlib.util.spec_from_file_location(
    "cps.crawler.gutenberg_popular",
    os.path.join(path, "cps", "crawler", "gutenberg_popular.py")
)
gutenberg_popular_module = importlib.util.module_from_spec(spec)
gutenberg_popular_module.__package__ = 'cps.crawler'
sys.modules['cps.crawler.gutenberg_popular'] = gutenberg_popular_module
spec.loader.exec_module(gutenberg_popular_module)
# 将模块添加到 crawler 模块的属性中
sys.modules['cps.crawler'].gutenberg_popular = gutenberg_popular_module

GutenbergPopular = gutenberg_popular_module.GutenbergPopular


class TestGutenbergPopular(unittest.TestCase):

    @patch("cps.crawler.gutenberg_popular.requests.get")
    def test_fetch_top_book_ids(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = """
        <a href="/ebooks/1342">Book</a>
        <a href="/ebooks/11">Book</a>
        <a href="/ebooks/84">Book</a>
        """

        ids = GutenbergPopular.fetch_top_book_ids(limit=3)

        self.assertEqual(len(ids), 3)
        self.assertIn(1342, ids)
        self.assertIn(11, ids)
        self.assertIn(84, ids)


if __name__ == "__main__":
    unittest.main()
