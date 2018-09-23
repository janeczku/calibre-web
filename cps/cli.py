#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import sys

parser = argparse.ArgumentParser(description='Calibre Web is a web app'
                    ' providing a interface for browsing, reading and downloading eBooks\n', prog='cps.py')
parser.add_argument('-p', metavar='path', help='path and name to settings db, e.g. /opt/cw.db')
parser.add_argument('-g', metavar='path', help='path and name to gdrive db, e.g. /opt/gd.db')
parser.add_argument('-c', metavar='path', help='path and name to SSL certfile, e.g. /opt/test.cert, works only in combination with keyfile')
parser.add_argument('-k', metavar='path', help='path and name to SSL keyfile, e.g. /opt/test.key, works only in combination with certfile')
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

certfilepath = None
keyfilepath = None
if args.c:
    if os.path.isfile(args.c):
        certfilepath = args.c
    else:
        print("Certfilepath is invalid. Exiting...")
        sys.exit(1)

if args.c is "":
    certfilepath = ""

if args.k:
    if os.path.isfile(args.k):
        keyfilepath = args.k
    else:
        print("Keyfilepath is invalid. Exiting...")
        sys.exit(1)

if (args.k and not args.c) or (not args.k and args.c):
    print("Certfile and Keyfile have to be used together. Exiting...")
    sys.exit(1)

if args.k is "":
    keyfilepath = ""
