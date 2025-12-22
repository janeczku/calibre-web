# tests/crawler/test_saver.py

import os
import sys
import unittest
import shutil
import tempfile
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
    "cps.crawler.saver",
    os.path.join(path, "cps", "crawler", "saver.py")
)
saver_module = importlib.util.module_from_spec(spec)
saver_module.__package__ = 'cps.crawler'
sys.modules['cps.crawler.saver'] = saver_module
spec.loader.exec_module(saver_module)

Saver = saver_module.Saver


class TestSaver(unittest.TestCase):

    def setUp(self):
        # 创建临时目录用于测试
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_save_file(self):
        data = b"test epub content"
        filename = "test.epub"

        # 注意：Saver.save 不接受 base_dir 参数
        # 它会保存到 saver.py 中定义的 library 目录
        path = Saver.save(data, filename)

        self.assertTrue(os.path.exists(path))
        self.assertEqual(os.path.basename(path), filename)


if __name__ == "__main__":
    unittest.main()
