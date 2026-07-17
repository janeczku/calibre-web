/* Calibre-Web service worker: makes the app installable and serves
 * downloaded books, the reader and its assets while offline. */

var SHELL_CACHE = "calibre-web-shell-{{ version }}";
var BOOKS_CACHE = "calibre-web-books-v1";
var BASE_PATH = "{{ url_for('web.index') }}";
var STATIC_PATH = "{{ url_for('static', filename='') }}";
var OFFLINE_URL = "{{ url_for('pwa.offline_library') }}";

var SHELL_ASSETS = [
    // Offline library page and its assets
    OFFLINE_URL,
    "{{ url_for('static', filename='css/libs/bootstrap.min.css') }}",
    "{{ url_for('static', filename='css/style.css') }}",
    "{{ url_for('static', filename='css/fonts/glyphicons-halflings-regular.woff2') }}",
    "{{ url_for('static', filename='css/fonts/glyphicons-halflings-regular.woff') }}",
    "{{ url_for('static', filename='js/offline.js') }}",
    "{{ url_for('static', filename='icon.png') }}",
    "{{ url_for('static', filename='icon.svg') }}",
    "{{ url_for('static', filename='generic_cover.jpg') }}",
    // epub reader (read.html) assets
    "{{ url_for('static', filename='css/libs/normalize.css') }}",
    "{{ url_for('static', filename='css/main.css') }}",
    "{{ url_for('static', filename='css/popup.css') }}",
    "{{ url_for('static', filename='css/reader.css') }}",
    "{{ url_for('static', filename='css/epub_themes.css') }}",
    "{{ url_for('static', filename='css/fonts/fontello.woff') }}",
    "{{ url_for('static', filename='css/fonts/fontello.ttf') }}",
    "{{ url_for('static', filename='js/libs/jquery.min.js') }}",
    "{{ url_for('static', filename='js/compress/jszip_epub.min.js') }}",
    "{{ url_for('static', filename='js/libs/epub.min.js') }}",
    "{{ url_for('static', filename='js/libs/screenfull.min.js') }}",
    "{{ url_for('static', filename='js/libs/reader.min.js') }}",
    "{{ url_for('static', filename='js/reading/epub.js') }}",
    "{{ url_for('static', filename='img/loader.gif') }}",
    "{{ url_for('static', filename='favicon.ico') }}"
];

self.addEventListener("install", function (event) {
    event.waitUntil(
        caches.open(SHELL_CACHE).then(function (cache) {
            return cache.addAll(SHELL_ASSETS);
        }).then(function () {
            return self.skipWaiting();
        })
    );
});

self.addEventListener("activate", function (event) {
    event.waitUntil(
        caches.keys().then(function (keys) {
            return Promise.all(keys.filter(function (key) {
                return key.indexOf("calibre-web-shell-") === 0 && key !== SHELL_CACHE;
            }).map(function (key) {
                return caches.delete(key);
            }));
        }).then(function () {
            return self.clients.claim();
        })
    );
});

function isStaticAsset(url) {
    return url.pathname.indexOf(STATIC_PATH) === 0;
}

function isBookFile(url) {
    return url.pathname.indexOf(BASE_PATH + "show/") === 0;
}

// Page navigations: network first, so content stays fresh and sessions work
// as usual. When the network is unreachable, fall back to the cached copy of
// the page (e.g. a downloaded /read/ page) and finally to the offline library.
async function handleNavigation(request) {
    try {
        return await fetch(request);
    } catch (networkError) {
        var cached = await caches.match(request, { ignoreSearch: true });
        if (cached) {
            return cached;
        }
        var offline = await caches.match(OFFLINE_URL);
        if (offline) {
            return offline;
        }
        throw networkError;
    }
}

// Static files: cache first (their URLs are cache-busted with a content hash,
// so a hit is always current). Anything fetched from the network is added to
// the shell cache so the reader keeps working offline after upgrades.
async function handleStatic(request) {
    var cached = await caches.match(request);
    if (cached) {
        return cached;
    }
    try {
        var response = await fetch(request);
        if (response.ok) {
            var cache = await caches.open(SHELL_CACHE);
            cache.put(request, response.clone());
        }
        return response;
    } catch (networkError) {
        // Offline with a different cache-busting query (e.g. fonts referenced
        // from CSS): any cached version is better than nothing.
        var fallback = await caches.match(request, { ignoreSearch: true });
        if (fallback) {
            return fallback;
        }
        throw networkError;
    }
}

// Book downloads (/show/...) are large and immutable: serve straight from the
// cache when downloaded. Everything else (covers, API calls) goes to the
// network first and only falls back to a cached copy when offline.
async function handleDefault(request, bookFile) {
    var cached = await caches.match(request);
    if (cached && bookFile) {
        return cached;
    }
    try {
        return await fetch(request);
    } catch (networkError) {
        if (cached) {
            return cached;
        }
        throw networkError;
    }
}

self.addEventListener("fetch", function (event) {
    var request = event.request;
    if (request.method !== "GET") {
        return;
    }
    var url = new URL(request.url);
    if (url.origin !== self.location.origin) {
        return;
    }
    if (request.mode === "navigate") {
        event.respondWith(handleNavigation(request));
    } else if (isStaticAsset(url)) {
        event.respondWith(handleStatic(request));
    } else {
        event.respondWith(handleDefault(request, isBookFile(url)));
    }
});
