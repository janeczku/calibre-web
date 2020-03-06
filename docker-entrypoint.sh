#!/bin/bash

echo "Creating calibre user"
groupadd -g $PGROUP calibre
useradd -M -N -u $PUSER -g $PGROUP calibre

echo "Changing application owner"
chown -R $PUSER:$PGROUP /calibre-web/app
gosu calibre test -w /calibre-web/app
if [[ $? -ne 0 ]]
then
  echo "Error: Was not able to write in application folder"
  exit 1
fi

if [[ ! -r /config/app.db ]]
then
  echo "Initialize application configuration"
  cp /calibre-web/app/dockerinit/app.db /config/app.db
fi
if [[ ! -r /config/gdrive.db ]]
then
  echo "Initialize gdrive configuration"
  cp /calibre-web/app/dockerinit/gdrive.db /config/gdrive.db
fi
echo "Changing configuration owner"
chown -R $PUSER:$PGROUP /config
gosu calibre test -w /config/app.db -a -w /config/gdrive.db
if [[ $? -ne 0 ]]
then
  echo "Error: Was not able to write config databases"
  exit 1
fi

if [[ ! -r /books/metadata.db ]]
then
  echo "Initialize Library"
  cp /calibre-web/app/dockerinit/metadata.db /books/metadata.db
  chown $PUSER:$PGROUP /books/metadata.db
fi
if [[ ! -r /books/metadata_db_prefs_backup.json ]]
then
  echo "Initialize Library configuration"
  cp /calibre-web/app/dockerinit/metadata_db_prefs_backup.json /books/metadata_db_prefs_backup.json
  chown $PUSER:$PGROUP /books/metadata_db_prefs_backup.json
fi

gosu calibre test -w /books/metadata.db -a -w /books/metadata_db_prefs_backup.json
if [[ $? -ne 0 ]]
then
  echo "Error: Was not able to write application databases"
  exit 1
fi

echo "Starting Calibre Web"
gosu $PUSER:$PGROUP bash -c "python /calibre-web/app/cps.py -p /config/app.db -g /config/gdrive.db"
