##About

Calibre Web is a Python web app providing a clean interface for browsing, reading and downloading e-books from a Calibre e-book database.

This was originally forked from [calibreserver](https://bitbucket.org/raphaelmutschler/calibreserver) and now includes additional features as well as many bugfixes.

Also available as [Docker image](https://registry.hub.docker.com/u/janeczku/calibre-web/).

![screenshot](https://raw.githubusercontent.com/janeczku/docker-calibre-web/master/screenshot.png)

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
- Support for public user registration
- Send eBooks to Kindle devices with the click of a button
- Support for reading eBooks directly in the browser
- Upload new books in PDF format

## Quick start

1. Rename `config.ini.example` to `config.ini` and set DB_ROOT to the path of the folder where your Calibre library (metadata.db) lives
2. To enable public user registration set PUBLIC_REG to 1
3. To enable uploading of PDF books set UPLOADING to 1
4. Execute the command: `python cps.py`
5. Point your browser to `http://localhost:8083` or `http://localhost:8083/feed` for the OPDS catalog 

**Default admin login:**    
*Username:* admin   
*Password:* admin123

## Requirements

Python 2.7+
     
Optionally, to enable on-the-fly conversion from EPUB to MOBI when using the send-to-kindle feature:     

1. Create a `vendor` folder in the app root
2. [Download](http://www.amazon.com/gp/feature.html?docId=1000765211) Amazon's KindleGen tool for your platform and place the binary named as `kindlegen` in this folder. 
