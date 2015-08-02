[![Donate](https://www.paypalobjects.com/de_DE/DE/i/btn/btn_donate_LG.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=Y459WGRLDTQJS) 

library aka CPS
=====

*library befindet sich noch in der alpha phase.*

library ist der versuch einen rein python basierenden eBook Server für alle Geräte zu entwickeln. Die offzielle Server app bietet wesentlich mehr funktionen, diese Version ist lediglich dazu gedacht die mit Calibre verwalteten Bücher (dynamisch) aufzulisten. Es handelt sich also nur um einen reinen Content Server. Ich betreibe CalibreServer auf einer Synology DS211j und als Portable version auf einem Raspberry Pi, diese war auch der Grund wieso ich mit der entwicklung angefangen habe. Der ofizielle Server läuft nur mit vielen Anpassungen auf der DS, ich wollte eine Lösung die einfach funktioniert ohne viele Umstände.

Help translate library aka CPS to your Language:
Hilf bei der Übersetzung in andere Sprachen:
https://www.transifex.com/projects/p/library-aka-calibreserver/

## Features:
- Einlesen der Calibre Datenbank
- HTML Interface
- OPDS Feed support
- User Management
- Admin Interface (neue user anlegen/verwalten)
- Download nur für angemeldete User
- epub to mobi converter (braucht kindlegen: http://www.amazon.com/gp/feature.html?docId=1000765211)
- send to kindle
- Buch online lesen

## ToDo:
- Setup vereinfachen (setup über webinterface)

## Setup:
1. Alle dateien herunterladen
2. Tool mit "python cps.py" starten (beendet automatisch)
3. config.ini bearbeiten (siehe unten)
4. create_admin.py aufrufen
5. Tool mit "python cps.py" starten

## config.ini
[General]
hier muss bei DB_ROOT  der absolute Pfad zum Ordner der Calibre Datenbank eingetragen werden
Alles andere kann vernachlässigt werden bzw sollte bereits stimmen

[Mail]
Hier sollten eure SMTP Zugangsdaten für die email die ihr zum versenden nutzen wollt eingetragen werden


## Anforderungen

Python 2.7+