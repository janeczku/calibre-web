#!/bin/sh
if [[ $PVERSION = 2 ]]; then
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
fi
if [[ $PVERSION = 3 ]]; then
python3.6 -m py_compile cps.py
python3.6 -m py_compile cps/book_formats.py
python3.6 -m py_compile cps/db.py
python3.6 -m py_compile cps/epub.py
python3.6 -m py_compile cps/fb2.py
python3.6 -m py_compile cps/helper.py
python3.6 -m py_compile cps/ub.py
python3.6 -m py_compile cps/uploader.py
python3.6 -m py_compile cps/web.py
python3.6 -m py_compile cps.py 
fi
  
