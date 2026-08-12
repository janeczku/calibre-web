/* global $, calibre, EPUBJS, ePubReader */

var reader;

(function () {
    "use strict";

    EPUBJS.filePath = calibre.filePath;
    EPUBJS.cssPath = calibre.cssPath;

    reader = ePubReader(calibre.bookUrl, {
        restore: true,
        bookmarks: calibre.bookmark ? [calibre.bookmark] : [],
    });

    Object.keys(themes).forEach(function (theme) {
        reader.rendition.themes.register(theme, themes[theme].css_path);
    });

    if (calibre.useBookmarks) {
        reader.on("reader:bookmarked", updateBookmark.bind(reader, "add"));
        reader.on("reader:unbookmarked", updateBookmark.bind(reader, "remove"));
    } else {
        $("#bookmark, #show-Bookmarks").remove();
    }

    // Enable swipe support
    // I have no idea why swiperRight/swiperLeft from plugins is not working, events just don't get fired
    var touchStart = 0;
    var touchEnd = 0;

    reader.rendition.on('touchstart', function(event) {
        touchStart = event.changedTouches[0].screenX;
    });
    reader.rendition.on('touchend', function(event) {
      touchEnd = event.changedTouches[0].screenX;
        if (touchStart < touchEnd) {
            if(reader.book.package.metadata.direction === "rtl") {
    			reader.rendition.next();
    		} else {
    			reader.rendition.prev();
    		}
            // Swiped Right
        }
        if (touchStart > touchEnd) {
            if(reader.book.package.metadata.direction === "rtl") {
    			reader.rendition.prev();
    		} else {
                reader.rendition.next();
    		}
            // Swiped Left
        }
    });

    // Update progress percentage
    let progressDiv = document.getElementById("progress");
    // Pages counter (virtual pages via EPUB locations)
    let pagesDiv = document.getElementById("pages-count");
    // Honor saved visibility preference for pages counter
    (function () {
        try {
            var pref = localStorage.getItem("calibre.reader.showPages");
            var show = pref === null ? true : pref === "true";
            if (pagesDiv)
                pagesDiv.style.visibility = show ? "visible" : "hidden";
        } catch (e) {}
    })();

    reader.book.ready.then(() => {
        let locations_key = reader.book.key() + "-locations";
        // Key to persist last-read position for this book in localStorage
        let position_key = "calibre.reader.position." + reader.book.key();
        let stored_locations = localStorage.getItem(locations_key);
        let make_locations, save_locations;
        if (stored_locations) {
            make_locations = Promise.resolve(
                reader.book.locations.load(stored_locations)
            );
            // No-op because locations are already saved
            save_locations = () => {};
        } else {
            make_locations = reader.book.locations.generate();
            save_locations = () => {
                localStorage.setItem(
                    locations_key,
                    reader.book.locations.save()
                );
            };
        }
        make_locations
            .then(() => {
                // Try to restore last position (CFI) from localStorage if present
                try {
                    var _savedPos = localStorage.getItem(position_key);
                    if (_savedPos) {
                        try {
                            var _posObj = JSON.parse(_savedPos);
                            if (_posObj && _posObj.cfi) {
                                // Display the saved CFI location
                                try {
                                    reader.rendition.display(_posObj.cfi);
                                } catch (e) {}
                            }
                        } catch (e) {}
                    }
                } catch (e) {}

                reader.rendition.on("relocated", (location) => {
                    let percentage = Math.round(location.end.percentage * 100);
                    progressDiv.textContent = percentage + "%";

                    // Pages based on generated EPUB locations (CFI positions)
                    const cfi = location.start.cfi;
                    const current =
                        reader.book.locations.locationFromCfi(cfi) || 0; // 1-based index typically
                    const total = reader.book.locations.length() || 0;

                    if (total > 0) {
                        pagesDiv.textContent = current + "/" + total;
                        pagesDiv.style.visibility = "visible";
                    } else {
                        pagesDiv.textContent = "";
                        pagesDiv.style.visibility = "hidden";
                    }

                    // Persist last position (CFI + percentage) to localStorage so reader can restore on next open
                    try {
                        var posObj = {
                            cfi: location.start.cfi,
                            percentage: location.start.percentage,
                        };
                        localStorage.setItem(
                            position_key,
                            JSON.stringify(posObj)
                        );
                    } catch (e) {}
                });
                reader.rendition.reportLocation();
                progressDiv.style.visibility = "visible";
            })
            .then(save_locations);
    });

    // Mark unfamiliar words in the currently visible EPUB document and show their history.
    var vocabularyInFlight = false;
    var vocabularySeen = {};
    function visibleWords() {
        var words = {};
        reader.rendition.getContents().forEach(function (content) {
            var doc = content.document;
            if (!doc || !doc.body) return;
            var walker = doc.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT);
            var node;
            while ((node = walker.nextNode())) {
                var sentence = (node.parentElement && node.parentElement.textContent || node.textContent || '').trim();
                (node.textContent.match(/\b[A-Za-z][A-Za-z'’-]*\b/g) || []).forEach(function (raw) {
                    var word = raw.toLowerCase().replace(/[’']/g, "'");
                    if (word.length > 1 && !vocabularySeen[word]) words[word] = sentence.slice(0, 500);
                });
            }
        });
        return words;
    }

    function markVocabulary(words, records) {
        var byWord = {};
        (records || []).forEach(function (record) { byWord[record.word] = record; });
        reader.rendition.getContents().forEach(function (content) {
            var doc = content.document;
            if (!doc || !doc.body) return;
            var walker = doc.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT);
            var textNodes = [], node;
            while ((node = walker.nextNode())) textNodes.push(node);
            textNodes.forEach(function (textNode) {
                var fragment = doc.createDocumentFragment(), text = textNode.textContent, last = 0;
                var regex = /\b[A-Za-z][A-Za-z'’-]*\b/g, match;
                while ((match = regex.exec(text))) {
                    var word = match[0].toLowerCase().replace(/[’']/g, "'");
                    var record = byWord[word];
                    if (!record || !record.unknown) continue;
                    fragment.appendChild(doc.createTextNode(text.slice(last, match.index)));
                    var span = doc.createElement('span');
                    span.className = 'reading-vocabulary-unknown';
                    span.textContent = match[0];
                    span.title = (record.translation || '点击查看学习记录') +
                        (record.lastBookName ? '\n上次：' + record.lastBookName + ' · ' + (record.lastChapter || '') : '');
                    span.dataset.word = word;
                    span.addEventListener('click', function () {
                        alert(span.title);
                    });
                    fragment.appendChild(span); last = regex.lastIndex;
                }
                if (last > 0) {
                    fragment.appendChild(doc.createTextNode(text.slice(last)));
                    textNode.parentNode.replaceChild(fragment, textNode);
                }
            });
        });
    }

    function inspectVocabulary() {
        if (!calibre.readingVocabularyEnabled || vocabularyInFlight) return;
        var words = visibleWords(), list = Object.keys(words);
        if (!list.length) return;
        vocabularyInFlight = true;
        var location = reader.currentLocation && reader.currentLocation();
        $.ajax({
            url: calibre.readingVocabularyUrl, method: 'POST', contentType: 'application/json',
            data: JSON.stringify({bookId: calibre.bookId, bookName: calibre.bookName,
                chapter: document.getElementById('chapter-title').textContent,
                page: document.getElementById('pages-count').textContent,
                cfi: location && location.start && location.start.cfi || '',
                words: list.map(function (word) { return {word: word, sentence: words[word]}; })})
        }).done(function (response) {
            var records = response.result || response.data || [];
            list.forEach(function (word) { vocabularySeen[word] = true; });
            markVocabulary(words, records);
        }).always(function () { vocabularyInFlight = false; });
    }
    reader.rendition.on('relocated', function () { setTimeout(inspectVocabulary, 120); });

    /**
     * @param {string} action - Add or remove bookmark
     * @param {string|int} location - Location or zero
     */
    function updateBookmark(action, location) {
        // Remove other bookmarks (there can only be one)
        if (action === "add") {
            this.settings.bookmarks
                .filter(function (bookmark) {
                    return bookmark && bookmark !== location;
                })
                .map(
                    function (bookmark) {
                        this.removeBookmark(bookmark);
                    }.bind(this)
                );
        }

        var csrftoken = $("input[name='csrf_token']").val();

        // Save to database
        $.ajax(calibre.bookmarkUrl, {
            method: "post",
            data: { bookmark: location || "" },
            headers: { "X-CSRFToken": csrftoken },
        }).fail(function (xhr, status, error) {
            alert(error);
        });
    }

    // Default settings load
    const theme = localStorage.getItem("calibre.reader.theme") ?? "lightTheme";
    selectTheme(theme);

    // Restore saved font and font size after reader is ready
    reader.book.ready.then(() => {
        const savedFontSize = localStorage.getItem("calibre.reader.fontSize");
        if (savedFontSize) {
            reader.rendition.themes.fontSize(`${savedFontSize}%`);
        }

        const savedFont = localStorage.getItem("calibre.reader.font");
        if (savedFont && window.selectFont) {
            window.selectFont(savedFont);
        }
    });
})();
