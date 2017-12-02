#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os

parser = argparse.ArgumentParser(description='Calibre Web is a web app'
                    ' providing a interface for browsing, reading and downloading eBooks\n', prog='cps.py')
parser.add_argument('-p', metavar='path', help='path and name to settings db, e.g. /opt/cw.db')
parser.add_argument('-g', metavar='path', help='path and name to gdrive db, e.g. /opt/gd.db')
args = parser.parse_args()

generalPath = os.path.normpath(os.getenv("CALIBRE_DBPATH",
                        os.path.dirname(os.path.realpath(__file__)) + os.sep + ".." + os.sep))
if args.p:
    settingspath = args.p
else:
    settingspath = os.path.join(generalPath, "app.db")

if args.g:
    gdpath = args.g
else:
    gdpath = os.path.join(generalPath, "gdrive.db")

