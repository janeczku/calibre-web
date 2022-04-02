# About

Calibre-Web is a web app providing a clean interface for browsing, reading and downloading eBooks using a valid [Calibre](https://calibre-ebook.com) database.

[![GitHub License](https://img.shields.io/github/license/janeczku/calibre-web?style=flat-square)](https://github.com/janeczku/calibre-web/blob/master/LICENSE)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/w/janeczku/calibre-web?logo=github&style=flat-square&label=commits)]()
[![GitHub all releases](https://img.shields.io/github/downloads/janeczku/calibre-web/total?logo=github&style=flat-square)](https://github.com/janeczku/calibre-web/releases)
[![PyPI](https://img.shields.io/pypi/v/calibreweb?logo=pypi&logoColor=fff&style=flat-square)](https://pypi.org/project/calibreweb/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/calibreweb?logo=pypi&logoColor=fff&style=flat-square)](https://pypi.org/project/calibreweb/)
[![Discord](https://img.shields.io/discord/838810113564344381?label=Discord&logo=discord&style=flat-square)](https://discord.gg/h2VsJ2NEfB)

*This software is a fork of [library](https://github.com/mutschler/calibreserver) and licensed under the GPL v3 License.*

![Main screen](https://github.com/janeczku/calibre-web/wiki/images/main_screen.png)

## Features

- Bootstrap 3 HTML5 interface
- full graphical setup
- User management with fine-grained per-user permissions
- Admin interface
- User Interface in brazilian, czech, dutch, english, finnish, french, german, greek, hungarian, italian, japanese, khmer, korean, polish, russian, simplified and traditional chinese, spanish, swedish, turkish, ukrainian
- OPDS feed for eBook reader apps 
- Filter and search by titles, authors, tags, series and language
- Create a custom book collection (shelves)
- Support for editing eBook metadata and deleting eBooks from Calibre library
- Support for converting eBooks through Calibre binaries
- Restrict eBook download to logged-in users
- Support for public user registration
- Send eBooks to Kindle devices with the click of a button
- Sync your Kobo devices through Calibre-Web with your Calibre library
- Support for reading eBooks directly in the browser (.txt, .epub, .pdf, .cbr, .cbt, .cbz, .djvu)
- Upload new books in many formats, including audio formats (.mp3, .m4a, .m4b)
- Support for Calibre Custom Columns
- Ability to hide content based on categories and Custom Column content per user
- Self-update capability
- "Magic Link" login to make it easy to log on eReaders
- Login via LDAP, google/github oauth and via proxy authentication

## Installation

#### Installation via pip (recommended)
1. To avoid problems with already installed python dependencies, it's recommended to create a virtual environment for Calibre-Web
2. Install Calibre-Web via pip with the command `pip install calibreweb` (Depending on your OS and or distro the command could also be `pip3`). 
3. Optional features can also be installed via pip, please refer to [this page](https://github.com/janeczku/calibre-web/wiki/Dependencies-in-Calibre-Web-Linux-Windows) for details 
4. Calibre-Web can be started afterwards by typing `cps` 

In the Wiki there are also examples for: a [manual installation](https://github.com/janeczku/calibre-web/wiki/Manual-installation), [installation on Linux Mint](https://github.com/janeczku/calibre-web/wiki/How-To:Install-Calibre-Web-in-Linux-Mint-19-or-20), [installation on a Cloud Provider](https://github.com/janeczku/calibre-web/wiki/How-To:-Install-Calibre-Web-on-a-Cloud-Provider).

## Quick start

Point your browser to `http://localhost:8083` or `http://localhost:8083/opds` for the OPDS catalog
Set `Location of Calibre database` to the path of the folder where your Calibre library (metadata.db) lives, push "submit" button\
Optionally a Google Drive can be used to host the calibre library [-> Using Google Drive integration](https://github.com/janeczku/calibre-web/wiki/Configuration#using-google-drive-integration)
Go to Login page

#### Default admin login:
*Username:* admin\
*Password:* admin123


## Requirements

python 3.5+

Optionally, to enable on-the-fly conversion from one ebook format to another when using the send-to-kindle feature, or during editing of ebooks metadata:

[Download and install](https://calibre-ebook.com/download) the Calibre desktop program for your platform and enter the folder including program name (normally /opt/calibre/ebook-convert, or C:\Program Files\calibre\ebook-convert.exe) in the field "calibre's converter tool" on the setup page.

[Download](https://github.com/pgaskin/kepubify/releases/latest) Kepubify tool for your platform and place the binary starting with `kepubify` in Linux: `\opt\kepubify` Windows: `C:\Program Files\kepubify`.

## Docker Images

A pre-built Docker image is available in these Docker Hub repository (maintained by the LinuxServer team):

#### **LinuxServer - x64, armhf, aarch64**
+ Docker Hub - [https://hub.docker.com/r/linuxserver/calibre-web](https://hub.docker.com/r/linuxserver/calibre-web)
+ Github - [https://github.com/linuxserver/docker-calibre-web](https://github.com/linuxserver/docker-calibre-web)
+ Github - (Optional Calibre layer) - [https://github.com/linuxserver/docker-calibre-web/tree/calibre](https://github.com/linuxserver/docker-calibre-web/tree/calibre) 

   This image has the option to pull in an extra docker manifest layer to include the Calibre `ebook-convert` binary.  Just include the environmental variable `DOCKER_MODS=linuxserver/calibre-web:calibre` in your docker run/docker compose file. **(x64 only)**
  
   If you do not need this functionality then this can be omitted, keeping the image as lightweight as possible.
    
   Both the Calibre-Web and Calibre-Mod images are rebuilt automatically on new releases of Calibre-Web and Calibre respectively, and on updates to any included base image packages on a weekly basis if required.
   + The "path to convertertool" should be set to `/usr/bin/ebook-convert`
   + The "path to unrar" should be set to `/usr/bin/unrar`

# Contact

Just reach us out on [Discord](https://discord.gg/h2VsJ2NEfB)

For further information, How To's and FAQ please check the [Wiki](https://github.com/janeczku/calibre-web/wiki)

# Contributing to Calibre-Web

Please have a look at our [Contributing Guidelines](https://github.com/janeczku/calibre-web/blob/master/CONTRIBUTING.md) 
