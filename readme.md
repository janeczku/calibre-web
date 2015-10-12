This is an in-progress fork of [calibreserver](https://bitbucket.org/raphaelmutschler/calibreserver)  by Raphael Mutschler.

A working Docker image is available here: [janeczku/calibre-web](https://registry.hub.docker.com/u/janeczku/calibre-web/).

##About

Calibre Web is a Python web app providing a clean interface for browsing, reading and downloading e-books from a Calibre e-book database.

##Features
- Bootstrap 3 HTML5 interface
- User management
- Admin interface
- OPDS feed for eBook reader apps
- Filter and search by titles, authors, tags, series and language
- Create custom book collection (shelves)
- Support for editing eBook metadata
- Support for converting eBooks from EPUB to Kindle format (mobi/azw)
- Restrict eBook download to logged-in users
- Send eBooks to Kindle devices with the click of a button
- Support for reading eBooks directly in the browser

## Quick start

1. Execute the command: `python cps.py` (it will throw an error)
2. Edit config.ini and set DB_ROOT to the path of the folder where your Calibre library (metadata.db) lives
3. Execute the command: `python cps.py`
4. Point your browser to `http://localhost:8083`

**Default admin login:**    
*Username:* admin   
*Password:* admin123

## Requirements

Python 2.7+