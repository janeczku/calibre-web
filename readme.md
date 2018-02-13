# About

Calibre Web is a web app providing a clean interface for browsing, reading and downloading eBooks using an existing [Calibre](https://calibre-ebook.com) database.

*This software is a fork of [library](https://github.com/mutschler/calibreserver) and licensed under the GPL v3 License.*

![screenshot](https://raw.githubusercontent.com/janeczku/docker-calibre-web/master/screenshot.png)

## Features

- Bootstrap 3 HTML5 interface
- full graphical setup
- User management with fine grained per-user permissions
- Admin interface
- User Interface in dutch, english, french, german, italian, japanese, polish, russian, simplified chinese, spanish
- OPDS feed for eBook reader apps 
- Filter and search by titles, authors, tags, series and language
- Create custom book collection (shelves)
- Support for editing eBook metadata and deleting eBooks from Calibre library
- Support for converting eBooks from EPUB to Kindle format (mobi/azw)
- Restrict eBook download to logged-in users
- Support for public user registration
- Send eBooks to Kindle devices with the click of a button
- Support for reading eBooks directly in the browser (.txt, .epub, .pdf, .cbr, .cbt, .cbz)
- Upload new books in PDF, epub, fb2 format
- Support for Calibre custom columns
- Ability to hide content based on categories for certain users
- Self update capability
- "Magic Link" login to make it easy to log on eReaders

## Quick start

1. Install dependencies by running `pip install --target vendor -r requirements.txt`. 
2. Execute the command: `python cps.py` (or `nohup python cps.py` - recommended if you want to exit the terminal window)
3. Point your browser to `http://localhost:8083` or `http://localhost:8083/opds` for the OPDS catalog
4. Set `Location of Calibre database` to the path of the folder where your Calibre library (metadata.db) lives, push "submit" button
   optionally a google drive can be used to host the calibre library (-> Using Google Drive integration)
5. Go to Login page

**Default admin login:**
*Username:* admin
*Password:* admin123

## Runtime Configuration Options

The configuration can be changed as admin in the admin panel under "Configuration"

Server Port:
Changes the port Calibre-Web is listening, changes take effect after pressing submit button

Enable public registration:    
Tick to enable public user registration.

Enable anonymous browsing:    
Tick to allow not logged in users to browse the catalog, anonymous user permissions can be set as admin ("Guest" user)

Enable uploading:
Tick to enable uploading of PDF, epub, FB2. This requires the imagemagick library to be installed.    

Enable remote login ("magic link"):
Tick to enable remote login, i.e. a link that allows user to log in via a different device.

## Requirements

Python 2.7+

Optionally, to enable on-the-fly conversion from EPUB to MOBI when using the send-to-kindle feature:

[Download](http://www.amazon.com/gp/feature.html?docId=1000765211) Amazon's KindleGen tool for your platform and place the binary named as `kindlegen` in the `vendor` folder.

## Using Google Drive integration

Calibre Calibre library (metadata.db) can be located on a Google Drive. Additional optional dependencys are necessary to get this work. Please install all optional  requirements by executing `pip install --target vendor -r optional-requirements.txt`

To use google drive integration, you have to use the google developer console to create a new app. https://console.developers.google.com

Once a project has been created, we need to create a client ID and a client secret that will be used to enable the OAuth request with google, and enable the Drive API. To do this, follow the steps below: -

1. Open project in developer console
2. Click Enable API, and enable google drive
3. Now on the sidebar, click Credentials
4. Click Create Credentials and OAuth Client ID
5. Select Web Application and then next
6. Give the Credentials a name and enter your callback, which will be CALIBRE_WEB_URL/gdrive/callback
7. Finally click save

The Drive API should now be setup and ready to use, so we need to integrate it into Calibre-Web. This is done as below: -

1. Open config page
2. Enter the location that will be used to store the metadata.db file, and to temporary store uploaded books and other temporary files for upload
2. Tick Use Google Drive
3. Enter Client Secret and Client Key as provided via previous steps
4. Enter the folder that is the root of your calibre library
5. Enter base URL for calibre (used for google callbacks)
6. Now select Authenticate Google Drive
7. This should redirect you to google to allow it top use your Drive, and then redirect you back to the config page
8. Google Drive should now be connected and be used to get images and download Epubs. The metadata.db is stored in the calibre library location

### Optional
If your calibre web is using https, it is possible to add a "watch" to the drive. This will inform us if the metadata.db file is updated and allow us to update our calibre library accordingly.

9. Click enable watch of metadata.db
10. Note that this expires after a week, so will need to be manually refresh 

## Docker image

Calibre Web can be run as Docker container. Pre-built Docker images based on Alpine Linux are available in this Docker Hub repository: [technosoft2000/calibre-web](https://hub.docker.com/r/technosoft2000/calibre-web/).

## Reverse Proxy

Reverse proxy configuration examples for apache and nginx to use Calibre-Web:

nginx configuration for a local server listening on port 8080, mapping calibre web to /calibre:

```
http {
    upstream calibre {
        server  127.0.0.1:8083;
    }
    server {
            location /calibre-web {
                proxy_bind              $server_addr;
                proxy_pass              http://127.0.0.1:8083;
                proxy_set_header        Host            $http_host;
                proxy_set_header        X-Forwarded-For $proxy_add_x_forwarded_for;
                proxy_set_header        X-Scheme        $scheme;
                proxy_set_header        X-Script-Name   /calibre-web;
        }
    }
}
```

Apache 2.4 configuration for a local server listening on port 443, mapping calibre web to /calibre-web:

The following modules have to be activated: headers, proxy, rewrite.
```
Listen 443

<VirtualHost *:443>
    SSLEngine on
    SSLProxyEngine on
    SSLCipherSuite ALL:!ADH:!EXPORT56:RC4+RSA:+HIGH:+MEDIUM:+LOW:+SSLv2:+EXP:+eNULL
    SSLCertificateFile "C:\Apache24\conf\ssl\test.crt"
    SSLCertificateKeyFile "C:\Apache24\conf\ssl\test.key"
    
    <Location "/calibre-web" >
        RequestHeader set X-SCRIPT-NAME /calibre-web
        RequestHeader set X-SCHEME https
        ProxyPass http://localhost:8083/
        ProxyPassReverse http://localhost:8083/
    </Location>
</VirtualHost>
```

## Start Calibre-Web as service under Linux

Create a file "cps.service" as root in the folder /etc/systemd/system with the following content:

```[Unit]
Description=Calibre-Web

[Service]
Type=simple
User=[Username]
ExecStart=[path to python] [/PATH/TO/cps.py]

[Install]
WantedBy=multi-user.target
```

Replace the user and ExecStart with your user and foldernames.

`sudo systemctl enable cps.service`

enables the service.

## Command line options

Starting the script with `-h` lists all supported command line options
Currently supported are 2 options, which are both useful for running multiple instances of Calibre-Web

`"-p path"` allows to specify the location of the settings database 
`"-p path"` allows to specify the location of the google-drive database 

