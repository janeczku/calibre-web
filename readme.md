# About

Calibre-Web is a web app providing a clean interface for browsing, reading and downloading eBooks using an existing [Calibre](https://calibre-ebook.com) database.

*This software is a fork of [library](https://github.com/mutschler/calibreserver) and licensed under the GPL v3 License.*

![Main screen](../../wiki/images/main_screen.png)

## Features

- Bootstrap 3 HTML5 interface
- full graphical setup
- User management with fine grained per-user permissions
- Admin interface
- User Interface in dutch, english, french, german, hungarian, italian, japanese, khmer, polish, russian, simplified chinese, spanish, swedish, ukrainian
- OPDS feed for eBook reader apps 
- Filter and search by titles, authors, tags, series and language
- Create custom book collection (shelves)
- Support for editing eBook metadata and deleting eBooks from Calibre library
- Support for converting eBooks through Calibre binaries
- Restrict eBook download to logged-in users
- Support for public user registration
- Send eBooks to Kindle devices with the click of a button
- Support for reading eBooks directly in the browser (.txt, .epub, .pdf, .cbr, .cbt, .cbz)
- Upload new books in many formats
- Support for Calibre custom columns
- Ability to hide content based on categories for certain users
- Self update capability
- "Magic Link" login to make it easy to log on eReaders

## Quick start

1. Install dependencies by running `pip install --target vendor -r requirements.txt`.
2. Execute the command: `python cps.py` (or `nohup python cps.py` - recommended if you want to exit the terminal window)
3. Point your browser to `http://localhost:8083` or `http://localhost:8083/opds` for the OPDS catalog
4. Set `Location of Calibre database` to the path of the folder where your Calibre library (metadata.db) lives, push "submit" button\
   Optionally a Google Drive can be used to host the calibre library [-> Using Google Drive integration](https://github.com/janeczku/calibre-web/wiki/Configuration#using-google-drive-integration)
5. Go to Login page

**Default admin login:**\
*Username:* admin\
*Password:* admin123

**Issues with Ubuntu:**
Please note that running the above install command can fail on some versions of Ubuntu, saying `"can't combine user with prefix"`. This is a [known bug](https://github.com/pypa/pip/issues/3826) and can be remedied by using the command `pip install --system --target vendor -r requirements.txt` instead.

## Requirements

Python 2.7+, python 3.x+

Optionally, to enable on-the-fly conversion from one ebook format to another when using the send-to-kindle feature, or during editing of ebooks metadata:

[Download and install](https://calibre-ebook.com/download) the Calibre desktop program for your platform and enter the folder including programm name (normally /opt/calibre/ebook-convert, or C:\Program Files\calibre\ebook-convert.exe) in the field "calibre's converter tool" on the setup page.

\*** DEPRECATED \*** Support will be removed in future releases

[Download](http://www.amazon.com/gp/feature.html?docId=1000765211) Amazon's KindleGen tool for your platform and place the binary named as `kindlegen` in the `vendor` folder.

## Docker images

Pre-built Docker images based on Alpine Linux are available in these Docker Hub repositories:

**x64**
+ **technosoft2000** at [technosoft2000/calibre-web](https://hub.docker.com/r/technosoft2000/calibre-web/). If you want the option to convert/download ebooks in multiple formats, use this image as it includes Calibre's ebook-convert binary. The "path to convertertool" should be set to /opt/calibre/ebook-convert.
+ **linuxserver.io** at [linuxserver/calibre-web](https://hub.docker.com/r/linuxserver/calibre-web/). Cannot convert between ebook formats.

**armhf**
+ **linuxserver.io** at [lsioarmhf/calibre-web](https://hub.docker.com/r/lsioarmhf/calibre-web/)

**aarch64**
+ **linuxserver.io** at [lsioarmhf/calibre-web-aarch64](https://hub.docker.com/r/lsioarmhf/calibre-web-aarch64)

# Wiki

For further informations, How To's and FAQ please check the ![Wiki](../../wiki)
