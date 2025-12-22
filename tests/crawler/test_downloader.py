# tests/crawler/test_downloader.py

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
    "cps.crawler.downloader",
    os.path.join(path, "cps", "crawler", "downloader.py")
)
downloader_module = importlib.util.module_from_spec(spec)
downloader_module.__package__ = 'cps.crawler'
sys.modules['cps.crawler.downloader'] = downloader_module
spec.loader.exec_module(downloader_module)
# 将模块添加到 crawler 模块的属性中
sys.modules['cps.crawler'].downloader = downloader_module

Downloader = downloader_module.Downloader


class TestDownloader(unittest.TestCase):

    @patch("cps.crawler.downloader.requests.get")
    def test_download(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = b"fake epub data"

        data = Downloader.download("http://example.com/test.epub")

        self.assertEqual(data, b"fake epub data")


if __name__ == "__main__":
    unittest.main()
