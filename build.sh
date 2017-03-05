#!/bin/sh
set -x
 
python -m py_compile cps.py
python -m py_compile cps/book_formats.py
python -m py_compile cps/db.py
python -m py_compile cps/epub.py
python -m py_compile cps/fb2.py
python -m py_compile cps/helper.py
python -m py_compile cps/ub.py
python -m py_compile cps/uploader.py
python -m py_compile cps/web.py
python -m py_compile cps.py 
