#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

base_path = os.path.dirname(os.path.abspath(__file__))
# Insert local directories into path
sys.path.append(base_path)
sys.path.append(os.path.join(base_path, 'cps'))
sys.path.append(os.path.join(base_path, 'vendor'))

from cps.server import Server

if __name__ == '__main__':
    Server.startServer()





