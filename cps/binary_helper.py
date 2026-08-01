# -*- coding: utf-8 -*-

import os
import sys

if sys.platform == "win32":
    SUPPORTED_UNRAR_BINARIES = ("unRAR.exe", "unrar.exe")
    SUPPORTED_KEPUBIFY_BINARIES = ("kepubify-windows-64Bit.exe",)
elif sys.platform.startswith("freebsd"):
    SUPPORTED_UNRAR_BINARIES = ("unrar",)
    SUPPORTED_KEPUBIFY_BINARIES = ("kepubify",)
else:
    SUPPORTED_UNRAR_BINARIES = ("unrar",)
    SUPPORTED_KEPUBIFY_BINARIES = ("kepubify-linux-64bit", "kepubify-linux-32bit")


def resolve_binary_path(configured_path, binary_names):
    if not configured_path:
        return ""

    allowed_names = {binary_name.lower() for binary_name in binary_names}
    if os.path.isfile(configured_path) and os.access(configured_path, os.X_OK):
        if os.path.basename(os.path.realpath(configured_path)).lower() in allowed_names:
            return configured_path
        return ""

    if os.path.isdir(configured_path):
        for binary_name in binary_names:
            binary_path = os.path.join(configured_path, binary_name)
            if os.path.isfile(binary_path) and os.access(binary_path, os.X_OK):
                return binary_path
    return ""
