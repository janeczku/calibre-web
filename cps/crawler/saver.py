# cps/crawler/saver.py

import os

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

LIBRARY_DIR = os.path.join(BASE_DIR, "library")


class Saver:
    @staticmethod
    def save(file_bytes: bytes, filename: str) -> str:
        """
        保存电子书到 calibre-web/library 目录
        """
        os.makedirs(LIBRARY_DIR, exist_ok=True)

        file_path = os.path.join(LIBRARY_DIR, filename)

        with open(file_path, "wb") as f:
            f.write(file_bytes)

        return file_path
