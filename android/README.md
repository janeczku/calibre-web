# Calibre Reader — Android app

A native Android client for a [Calibre-Web](https://github.com/janeczku/calibre-web)
server. It mirrors the web app's offline-reading feature: browse your library,
download books to the device, and read them **offline** — with built-in
**EPUB** and **PDF** readers.

## Features

- **Connect** to any Calibre-Web server using its OPDS catalog (HTTP Basic auth), including HTTPS servers that require mTLS client certificates.
- **Browse & search** the library with cover thumbnails.
- **Make available offline**: download EPUB and PDF files (plus covers) to the
  device with a progress indicator.
- **Offline library**: a dedicated tab lists everything stored on the device and
  works with no network connection; shows storage used and reading progress.
- **EPUB reader**: chapter-by-chapter WebView renderer with pinch-zoom; remembers
  your place.
- **PDF reader**: continuous page view backed by Android's built-in `PdfRenderer`;
  remembers the last page.
- **Remove** downloads to free space.

## How it talks to the server

The app uses Calibre-Web's OPDS endpoints (no extra server changes required):

| Purpose        | Endpoint                                  |
|----------------|-------------------------------------------|
| Recent books   | `GET /opds/new`                           |
| Search         | `GET /opds/search?query=…`                |
| Cover          | `GET /opds/cover_240_240/<id>`            |
| Download       | `GET /opds/download/<id>/<format>/`       |

All requests are authenticated with HTTP Basic auth. For servers protected by mutual TLS, the app can also use an Android KeyChain client certificate for OPDS, cover, and download requests. Make sure **OPDS feeds are
enabled** for your Calibre-Web user (they are by default).

## Building

Requirements: Android Studio (Koala or newer) or the Android command-line SDK,
JDK 17, and an Android SDK with **API 34** installed. `minSdk` is 26 (Android 8.0).

```bash
cd android
# point the build at your SDK (or set ANDROID_HOME / use Android Studio):
echo "sdk.dir=/path/to/Android/sdk" > local.properties

./gradlew assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk
./gradlew installDebug   # to a connected device/emulator
```

Or just open the `android/` folder in Android Studio and press Run.

## First run

1. Launch the app → **Settings** tab.
2. Enter your server URL (e.g. `http://192.168.1.10:8083`), username, and
   password, then tap **Save & Connect**.
3. Browse or search, open a book, and tap **Download** for EPUB/PDF.
4. Switch to the **Offline** tab (or stay in Browse) and tap **Read**.

> Cleartext HTTP is enabled so LAN servers over `http://` work out of the box.
> For a server exposed to the internet, use HTTPS.

### mTLS / client certificates

If your Calibre-Web server requires mutual TLS:

1. Install your client certificate and private key on Android (for example, a `.p12`/`.pfx` file via Android's certificate installer).
2. Open the app → **Settings** → **Select client certificate** and choose the installed certificate.
3. Save and connect as usual. The selected Android KeyChain alias is stored in app settings; the private key remains managed by Android KeyChain.

## Architecture

Single-module app, no DI framework — the object graph is created in
`CalibreApp` and passed down.

```
data/
  SettingsStore       server URL + credentials (SharedPreferences)
  OpdsClient          OkHttp + streaming Atom-XML parser + downloads
  LibraryRepository   offline files, covers, unzipped EPUBs, JSON index
  OpdsModels          OpdsBook / OpdsFormat / DownloadedBook
ui/
  AppNavigation       bottom-nav (Browse / Offline / Settings) + reader routes
  screens/            Compose screens + LibraryViewModel
  components/         BookCover
reader/
  epub/EpubBook       unzip + OPF/spine parsing
  epub/EpubReaderScreen
  pdf/PdfReaderScreen  PdfRenderer-backed pager
```

- **UI**: Jetpack Compose + Material 3.
- **Networking**: OkHttp; covers load through the same authenticated client via
  Coil.
- **Offline metadata**: kotlinx.serialization JSON index in app-private storage;
  book files, covers, and unzipped EPUBs live under `filesDir`.

## Notes & limitations

- Downloads are stored per-app in private storage; uninstalling removes them.
- Credentials are stored in `SharedPreferences`. For a hardened build, swap
  `SettingsStore` for `EncryptedSharedPreferences`.
- The EPUB reader tracks position by chapter (spine index), not intra-chapter
  scroll offset.
- Only EPUB and PDF are opened in-app (the formats with native readers here);
  other formats are simply not offered for download.
