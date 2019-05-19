#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os


# Insert local directories into path
sys.path.append(os.path.join(sys.path[0], 'vendor'))

from cps.server import Server

if __name__ == '__main__':
    Server.startServer()
