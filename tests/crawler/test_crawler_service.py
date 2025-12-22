# tests/crawler/test_crawler_service.py

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import importlib.util

# 将项目根目录添加到 sys.path
path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, path)

# 在导入 cps 模块之前，模拟 Flask 和其他依赖项
sys.modules['flask'] = MagicMock()
sys.modules['flask_principal'] = MagicMock()
# 在加载模块之前，先 mock requests 模块（downloader 和 gutenberg_popular 需要）
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

# 首先加载依赖项（它们使用相对导入）
crawler_dir = os.path.join(path, "cps", "crawler")

# 加载 gutenberg_fetcher
spec_fetcher = importlib.util.spec_from_file_location(
    "cps.crawler.gutenberg_fetcher",
    os.path.join(crawler_dir, "gutenberg_fetcher.py")
)
fetcher_module = importlib.util.module_from_spec(spec_fetcher)
fetcher_module.__package__ = 'cps.crawler'
sys.modules['cps.crawler.gutenberg_fetcher'] = fetcher_module
spec_fetcher.loader.exec_module(fetcher_module)
# 将模块添加到 crawler 模块的属性中
sys.modules['cps.crawler'].gutenberg_fetcher = fetcher_module

# 加载 downloader
spec_downloader = importlib.util.spec_from_file_location(
    "cps.crawler.downloader",
    os.path.join(crawler_dir, "downloader.py")
)
downloader_module = importlib.util.module_from_spec(spec_downloader)
downloader_module.__package__ = 'cps.crawler'
sys.modules['cps.crawler.downloader'] = downloader_module
spec_downloader.loader.exec_module(downloader_module)
# 将模块添加到 crawler 模块的属性中
sys.modules['cps.crawler'].downloader = downloader_module

# 加载 saver
spec_saver = importlib.util.spec_from_file_location(
    "cps.crawler.saver",
    os.path.join(crawler_dir, "saver.py")
)
saver_module = importlib.util.module_from_spec(spec_saver)
saver_module.__package__ = 'cps.crawler'
sys.modules['cps.crawler.saver'] = saver_module
spec_saver.loader.exec_module(saver_module)
# 将模块添加到 crawler 模块的属性中
sys.modules['cps.crawler'].saver = saver_module

# 加载 gutenberg_popular
spec_popular = importlib.util.spec_from_file_location(
    "cps.crawler.gutenberg_popular",
    os.path.join(crawler_dir, "gutenberg_popular.py")
)
popular_module = importlib.util.module_from_spec(spec_popular)
popular_module.__package__ = 'cps.crawler'
sys.modules['cps.crawler.gutenberg_popular'] = popular_module
spec_popular.loader.exec_module(popular_module)
# 将模块添加到 crawler 模块的属性中
sys.modules['cps.crawler'].gutenberg_popular = popular_module

# 现在加载 crawler_service（它依赖于上述模块）
spec = importlib.util.spec_from_file_location(
    "cps.crawler.crawler_service",
    os.path.join(crawler_dir, "crawler_service.py")
)
crawler_service_module = importlib.util.module_from_spec(spec)
crawler_service_module.__package__ = 'cps.crawler'
sys.modules['cps.crawler.crawler_service'] = crawler_service_module
spec.loader.exec_module(crawler_service_module)
# 将模块添加到 crawler 模块的属性中
sys.modules['cps.crawler'].crawler_service = crawler_service_module

CrawlerService = crawler_service_module.CrawlerService


class TestCrawlerService(unittest.TestCase):

    @patch("cps.crawler.crawler_service.GutenbergPopular.fetch_top_book_ids")
    @patch("cps.crawler.crawler_service.GutenbergFetcher.get_download_url")
    @patch("cps.crawler.crawler_service.Downloader.download")
    @patch("cps.crawler.crawler_service.Saver.save")
    def test_import_books(
        self,
        mock_save,
        mock_download,
        mock_get_url,
        mock_get_ids
    ):
        mock_get_ids.return_value = [1, 2]
        mock_get_url.side_effect = lambda x: f"http://example.com/{x}.epub"
        mock_download.return_value = b"data"
        mock_save.return_value = "library/test.epub"

        results = CrawlerService.import_books(limit=2)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["status"], "success")


if __name__ == "__main__":
    unittest.main()
