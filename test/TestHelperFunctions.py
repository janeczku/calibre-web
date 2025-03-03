import unittest
from unittest.mock import patch, MagicMock

from cps.file_helper import get_mimetype
from cps.string_helper import strip_whitespaces
from cps.subproc_wrapper import process_wait


class TestHelperFunctions(unittest.TestCase):

    def test_strip_whitespaces(self):
        self.assertEqual(strip_whitespaces("   hello   "), "hello")
        self.assertEqual(strip_whitespaces("\u200Bhello\u200B"), "hello")



    def test_get_mimetype(self):
        self.assertEqual(get_mimetype(".fb2"), "text/xml")
        self.assertEqual(get_mimetype(".cbz"), "application/zip")
        self.assertEqual(get_mimetype(".cbr"), "application/x-rar")

    @patch('cps.subproc_wrapper.process_open')
    def test_process_wait(self, mock_process_open):
        mock_process = MagicMock()
        mock_process.stdout.readlines.return_value = ["calibre 5.33.2"]
        mock_process.wait.return_value = None
        mock_process_open.return_value = mock_process

        result = process_wait(["calibre", "--version"], pattern="calibre (.*)")
        self.assertIsNotNone(result)
        self.assertEqual(result.group(1), "5.33.2")


if __name__ == "__main__":
    unittest.main()
