# foliate-js (vendored subset)

This directory contains the subset of [foliate-js](https://github.com/johnfactotum/foliate-js)
needed to parse and render MOBI/KF8 (AZW/AZW3) books in the browser.

- Upstream commit: `78914aef4466eb960965702401634c2cb348e9b1`
- License: MIT, see `LICENSE`

Only the modules used by Calibre-Web's MOBI reader are included:

- `view.js`, `paginator.js`, `fixed-layout.js`, `overlayer.js`, `progress.js`,
  `epubcfi.js`, `text-walker.js`
- `mobi.js` and `vendor/fflate.js` for MOBI/KF8 parsing and decompression

The generic format detection in `view.js` is left untouched, but Calibre-Web
passes an already parsed `MOBI` book object to `foliate-view`, so the EPUB/PDF/
CBZ/FB2 loaders are not used and their modules are not vendored.

Local change: the iframe sandbox in `paginator.js` and `fixed-layout.js` was
changed from `allow-same-origin allow-scripts` to `allow-same-origin`. E-book
content is untrusted, and scripts embedded in a book must not run inside the
reader. Please keep this change when updating the vendored files.
