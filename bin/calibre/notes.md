# `bin/` (FTS runtime bundle)

This folder contains the minimal runtime assets required to run the full‑text search (FTS) subsystem without installing the full Calibre distribution. It is intentionally small and includes only the shared libraries and extension needed by the FTS indexer and database.

## Contents

From `https://github.com/kovidgoyal/calibre/releases/download/VERSION/calibre-VERSION-x86_64.txz`:

```
bin/
└─ calibre/
   ├─ calibre-extensions/
   │  └─ sqlite_extension.so
   ├─ lib/
   │  ├─ libicudata.so.73
   │  ├─ libicui18n.so.73
   │  ├─ libicuio.so.73
   │  ├─ libicuuc.so.73
   │  └─ libstemmer.so.0
   └─ notes.md
```

## Details

- **`calibre/calibre-extensions/sqlite_extension.so`**
	- SQLite extension required by the FTS engine.
	- Loaded by the FTS process to enable advanced text search behavior.

- **`calibre/lib/`**
	- ICU libraries (`libicu*`) used for Unicode collation, normalization, and language‑aware text processing.
	- `libstemmer.so.0` provides word stemming for better search matching.

## Notes

- This directory is **not** a full Calibre install.
- Only the components strictly required for FTS are shipped here to keep deployment small and predictable.
