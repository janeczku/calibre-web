# Minerva Calibre-web

## Docker

  1; Make directories needed:
  
  ``` bash
  mkdir config
  mkdir books
  ```

  2; Copy empty database from library to books directory:

   ``` bash
  cp ./library/metadata.db ./books/
  ```

  3; Build the Docker image:

  ``` bash
  docker build . -t minerva-calibre
  ```

  4; Deploy the docker compose

  ``` bash
  docker compose up -d
  ```

- This process takes about 2-3 minutes.
- The application will be available at `http://localhost/`

### Default Admin Login:
- **Username:** admin
- **Password:** admin123

### Set Database
The application at the begining ask you for the database. choose the database you copy into books folder.

