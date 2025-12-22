# tests/api/test_crawler_api.py

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import importlib.util

# 添加项目根目录
path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, path)


class TestCrawlerAPIMock(unittest.TestCase):
    """
    Mock 版接口测试
    测试 /crawler/gutenberg/import 路由逻辑
    不执行真实爬虫、不访问网络
    """

    def setUp(self):
        try:
            import cps
        except Exception:
            pass

        import types
        gstub = types.ModuleType('cps.gdriveutils')
        def _f(*args, **kwargs):
            return None
        gstub.getFileFromEbooksFolder = _f
        gstub.do_gdrive_download = _f
        sys.modules['cps.gdriveutils'] = gstub

        # 加载 web.py
        web_path = os.path.join(path, "cps", "web.py")
        spec = importlib.util.spec_from_file_location("cps.web", web_path)
        web_module = importlib.util.module_from_spec(spec)
        web_module.__package__ = 'cps'
        sys.modules['cps.web'] = web_module
        spec.loader.exec_module(web_module)

        sys.modules['cps'].web = web_module

        self.web = web_module

    @patch("cps.web.CrawlerService.import_books")
    def test_gutenberg_import_api_mock(self, mock_import_books):
        """
        Mock 接口测试：
        - 模拟 Service 返回
        - 验证接口返回 JSON 结构
        """

        # Mock Service 返回结果
        mock_import_books.return_value = [
            {"book_id": 1, "status": "success", "path": "library/1.epub"},
            {"book_id": 2, "status": "success", "path": "library/2.epub"},
        ]

        # 模拟 Flask request.args
        fake_request = MagicMock()
        fake_request.args.get.return_value = 2

        with patch("cps.web.request", fake_request), patch("cps.web.jsonify", lambda payload: payload):
            response = self.web.import_gutenberg_books.__wrapped__()

        # 接口返回的是 (json, status_code) 或 Response
        self.assertIsInstance(response, dict)
        self.assertEqual(response["status"], "success")
        self.assertEqual(len(response["results"]), 2)

        # 验证 Service 被正确调用
        mock_import_books.assert_called_once_with(limit=2)


if __name__ == "__main__":
    unittest.main()
