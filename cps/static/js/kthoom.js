/*
 * kthoom.js
 *
 * Licensed under the MIT License
 *
 * Copyright(c) 2011 Google Inc.
 * Copyright(c) 2011 antimatter15
*/

/* Reference Documentation:

  * Web Workers: http://www.whatwg.org/specs/web-workers/current-work/
  * Web Workers in Mozilla: https://developer.mozilla.org/En/Using_web_workers
  * File API (FileReader): http://www.w3.org/TR/FileAPI/
  * Typed Arrays: http://www.khronos.org/registry/typedarray/specs/latest/#6

*/
/* global screenfull, bitjs, Uint8Array, opera, loadArchiveFormats, archiveOpenFile */
/* exported init, event */


if (window.opera) {
    window.console.log = function(str) {
        opera.postError(str);
    };
}

var kthoom;

// gets the element with the given id
function getElem(id) {
    if (document.documentElement.querySelector) {
        // querySelector lookup
        return document.body.querySelector("#" + id);
    }
    // getElementById lookup
    return document.getElementById(id);
}

if (typeof window.kthoom === "undefined" ) {
    kthoom = {};
}

// key codes
kthoom.Key = {
    ESCAPE: 27,
    SPACE: 32,
    LEFT: 37,
    UP: 38,
    RIGHT: 39,
    DOWN: 40,
    A: 65, B: 66, C: 67, D: 68, E: 69, F: 70, G: 71, H: 72, I: 73, J: 74, K: 75, L: 76, M: 77,
    N: 78, O: 79, P: 80, Q: 81, R: 82, S: 83, T: 84, U: 85, V: 86, W: 87, X: 88, Y: 89, Z: 90,
    QUESTION_MARK: 191,
    LEFT_SQUARE_BRACKET: 219,
    RIGHT_SQUARE_BRACKET: 221
};

// global variables
var unarchiver = null;
var currentImage = 0;
var imageFiles = [];
var imageFilenames = [];
var totalImages = 0;
var prevScrollPosition = 0;

var settings = {
    hflip: false,
    vflip: false,
    rotateTimes: 0,
    fitMode: kthoom.Key.B,
    theme: "light",
    direction: 0, // 0 = Left to Right, 1 = Right to Left
    nextPage: 0, // 0 = Reset to Top, 1 = Remember Position
	scrollbar: 1, // 0 = Hide Scrollbar, 1 = Show Scrollbar	
    pageDisplay: 0 // 0 = Single Page, 1 = Long Strip
};

kthoom.saveSettings = function() {
    localStorage.kthoomSettings = JSON.stringify(settings);
};

kthoom.loadSettings = function() {
    try {
        if (!localStorage.kthoomSettings) {
            return;
        }

        $.extend(settings, JSON.parse(localStorage.kthoomSettings));

        kthoom.setSettings();
    } catch (err) {
        alert("Error load settings");
    }
};

kthoom.setSettings = function() {
    // Set settings control values
    $.each(settings, function(key, value) {
        if (typeof value === "boolean") {
            $("input[name=" + key + "]").prop("checked", value);
        } else {
            $("input[name=" + key + "]").val([value]);
        }
    });
};

var createURLFromArray = function(array, mimeType) {
    var offset = 0; // array.byteOffset;
    var len = array.byteLength;
    var blob;

    if (mimeType === "image/xml+svg") {
        var xmlStr = new TextDecoder("utf-8").decode(array);
        return "data:image/svg+xml;UTF-8," + encodeURIComponent(xmlStr);
    }

    // TODO: Move all this browser support testing to a common place
    //     and do it just once.

    // Blob constructor, see http://dev.w3.org/2006/webapi/FileAPI/#dfn-Blob.
    if (typeof Blob === "function") {
        blob = new Blob([array], {type: mimeType});
    } else {
        throw "Browser support for Blobs is missing.";
    }

    if (blob.slice) {
        blob = blob.slice(offset, offset + len, mimeType);
    } else {
        throw "Browser support for Blobs is missing.";
    }

    if ((typeof URL !== "function" && typeof URL !== "object") ||
        typeof URL.createObjectURL !== "function") {
            throw "Browser support for Object URLs is missing";
    }

    return URL.createObjectURL(blob);
};


// Stores an image filename and its data: URI.
kthoom.ImageFile = function(file) {
    this.filename = file.filename;
    var fileExtension = file.filename.split(".").pop().toLowerCase();
    switch (fileExtension) {
        case "jpg":
        case "jpeg":
            this.mimeType = "image/jpeg";
            break;
        case "png":
            this.mimeType = "image/png";
            break;
        case "gif":
            this.mimeType = "image/gif";
            break;
        case "svg":
            this.mimeType = "image/svg+xml";
            break;
        case "webp":
            this.mimeType = "image/webp";
            break;
        default:
            this.mimeType = undefined;
            break;
    }

    // Reset mime type for special files originating from Apple devices
    // This folder may contain files having image extensions (for example .jpg) but those files are not actual images
    // Trying to view these files cause corrupted/empty pages in the comic reader and files should be ignored
    if (this.filename.indexOf("__MACOSX") !== -1) {
        this.mimeType = undefined;
    }

    if ( this.mimeType !== undefined) {
        this.dataURI = createURLFromArray(file.fileData, this.mimeType);
    }
};

function updateDirectionButtons(){
    var left = 1;
    var right = 1;
    if (currentImage <= 0 ) {
        if (settings.direction === 0) {
            left = 0;
        } else {
            right = 0;
        }
    }
    if ((currentImage + 1) >= Math.max(totalImages, imageFiles.length)) {
        if (settings.direction === 0) {
            right = 0;
        } else {
            left = 0;
       }
    }
    left === 1 ? $("#left").show() : $("#left").hide();
    right === 1 ? $("#right").show() : $("#right").hide();
}
function initProgressClick() {
    $("#progress").click(function(e) {
        var offset = $(this).offset();
        var x = e.pageX - offset.left;
        var rate = settings.direction === 0 ? x / $(this).width() : 1 - x / $(this).width();
        currentImage = Math.max(1, Math.ceil(rate * totalImages)) - 1;
        updateDirectionButtons();
        setBookmark();
        updatePage();
    });
}

function loadFromArrayBuffer(ab) {
    const collator = new Intl.Collator('en', { numeric: true, sensitivity: 'base' });
    loadArchiveFormats(['rar', 'zip', 'tar'], function() {
        // Open the file as an archive
        archiveOpenFile(ab, function (archive) {
            if (archive) {
                totalImages = archive.entries.length
                console.info('Uncompressing ' + archive.archive_type + ' ...');
                entries = archive.entries.sort((a,b) => collator.compare(a.name, b.name));
                entries.forEach(function(e, i) {
                    updateProgress( (i + 1)/ totalImages * 100);
                    if (e.is_file) {
                        e.readData(function(d) {
                            // add any new pages based on the filename
                            if (imageFilenames.indexOf(e.name) === -1) {
                                let data = {filename: e.name, fileData: d};
                                var test = new kthoom.ImageFile(data);
                                if (test.mimeType !== undefined) {
                                    imageFilenames.push(e.name);
                                    imageFiles.push(test);
                                    // add thumbnails to the TOC list
                                    $("#thumbnails").append(
                                        "<li>" +
                                        "<a data-page='" + imageFiles.length + "'>" +
                                        "<img src='" + imageFiles[imageFiles.length - 1].dataURI + "'/>" +
                                        "<span>" + imageFiles.length + "</span>" +
                                        "</a>" +
                                        "</li>"
                                    );
                                    
                                    drawCanvas();
                                    setImage(test.dataURI, null);
                                    
                                    // display first page if we haven't yet
                                    if (imageFiles.length === currentImage + 1) {
                                        updateDirectionButtons();
                                        updatePage();
                                    }
                                } else {
                                    totalImages--;
                                }
                            }
                        });
                    }
                });
            }
        });
    });
}

function scrollTocToActive() {
    $(".page").text((currentImage + 1 ) + "/" + totalImages);

    // Mark the current page in the TOC
    $("#tocView a[data-page]")
        // Remove the currently active thumbnail
        .removeClass("active")
        // Find the new one
        .filter("[data-page=" + (currentImage + 1) + "]")
        // Set it to active
        .addClass("active");

    // Scroll to the thumbnail in the TOC on page change
    $("#tocView").stop().animate({
        scrollTop: $("#tocView a.active").position().top
    }, 200);
}

function updatePage() {
    scrollTocToActive();
    scrollCurrentImageIntoView();
    updateProgress();
    pageDisplayUpdate();
    setTheme();

    kthoom.setSettings();
    kthoom.saveSettings();
}

function setTheme() {
    $("body").toggleClass("dark-theme", settings.theme === "dark");
	$("#mainContent").toggleClass("disabled-scrollbar", settings.scrollbar === 0);
}

function pageDisplayUpdate() {
    if(settings.pageDisplay === 0) {
        $(".mainImage").addClass("hide");
        $(".mainImage").eq(currentImage).removeClass("hide");
        $("#mainContent").removeClass("long-strip");
    } else {
        $(".mainImage").removeClass("hide");
        $("#mainContent").addClass("long-strip");
        scrollCurrentImageIntoView();
    }
}

function updateProgress(loadPercentage) {
    if (settings.direction === 0) {
        $("#progress .bar-read")
            .removeClass("from-right")
            .addClass("from-left");
        $("#progress .bar-load")
            .removeClass("from-right")
            .addClass("from-left");
    } else {
        $("#progress .bar-read")
            .removeClass("from-left")
            .addClass("from-right");
        $("#progress .bar-load")
            .removeClass("from-left")
            .addClass("from-right");
    }

    // Set the load/unzip progress if it's passed in
    if (loadPercentage) {
        $("#progress .bar-load").css({ width: loadPercentage + "%" });

        if (loadPercentage === 100) {
            $("#progress")
                .removeClass("loading")
                .find(".load").text("");
        }
    }
    // Set page progress bar
    $("#progress .bar-read").css({ width: totalImages === 0 ? 0 : Math.round((currentImage + 1) / totalImages * 100) + "%"});
}

function setImage(url, _canvas) {
    var canvas = _canvas || $(".mainImage").slice(-1)[0]; // Select the last item on the array if _canvas is null
    var x = canvas.getContext("2d");

    $("#mainText").hide();
    if (url === "error") {
        x.fillStyle = "black";
        x.textAlign = "center";
        x.font = "24px sans-serif";
        x.strokeStyle = (settings.theme === "dark") ? "white" : "black";
        x.fillText("Unable to decompress image #" + (currentImage + 1), innerWidth / 2, 100);

        $(".mainImage").slice(-1).addClass("error");
    } else {
        if ($("body").css("scrollHeight") / innerHeight > 1) {
            $("body").css("overflowY", "scroll");
        }

        var img = new Image();
        img.onerror = function() {
            canvas.width = innerWidth - 100;
            canvas.height = 300;
            x.fillStyle = "black";
            x.font = "50px sans-serif";
            x.strokeStyle = "black";
            x.fillText("Page #" + (currentImage + 1) + " (" +
                imageFiles[currentImage].filename + ")", innerWidth / 2, 100);
            x.fillStyle = "black";
            x.fillText("Is corrupt or not an image", innerWidth / 2, 200);

            var xhr = new XMLHttpRequest();
            if (/(html|htm)$/.test(imageFiles[currentImage].filename)) {
                xhr.open("GET", url, true);
                xhr.onload = function() {
                    $("#mainText").css("display", "");
                    $("#mainText").innerHTML("<iframe style=\"width:100%;height:700px;border:0\" src=\"data:text/html," + escape(xhr.responseText) + "\"></iframe>");
                };
                xhr.send(null);
            } else if (!/(jpg|jpeg|png|gif|webp)$/.test(imageFiles[currentImage].filename) && imageFiles[currentImage].data.uncompressedSize < 10 * 1024) {
                xhr.open("GET", url, true);
                xhr.onload = function() {
                    $("#mainText").css("display", "");
                    $("#mainText").innerText(xhr.responseText);
                };
                xhr.send(null);
            }
        };
        img.onload = function() {
            var h = img.height,
                w = img.width,
                sw = w,
                sh = h;
            settings.rotateTimes =  (4 + settings.rotateTimes) % 4;
            x.save();
            if (settings.rotateTimes % 2 === 1) {
                sh = w;
                sw = h;
            }
            canvas.height = sh;
            canvas.width = sw;
            x.translate(sw / 2, sh / 2);
            x.rotate(Math.PI / 2 * settings.rotateTimes);
            x.translate(-w / 2, -h / 2);
            if (settings.vflip) {
                x.scale(1, -1);
                x.translate(0, -h);
            }
            if (settings.hflip) {
                x.scale(-1, 1);
                x.translate(-w, 0);
            }
            canvas.style.display = "none";
            scrollTo(0, 0);
            x.drawImage(img, 0, 0);

            canvas.style.display = "";
            $("body").css("overflowY", "");
            x.restore();
        };
        img.src = url;
    }
}

// reloadImages is a slow process when multiple images are involved. Only used when rotating/mirroring
function reloadImages() {
    for(i=0; i < imageFiles.length; i++) {
        setImage(imageFiles[i].dataURI, $(".mainImage")[i]);
    }
}

function showLeftPage() {
    if (settings.direction === 0) {
        showPrevPage();
    } else {
        showNextPage();
    }
    setBookmark();
}

function showRightPage() {
    if (settings.direction === 0) {
        showNextPage();
    } else {
        showPrevPage();
    }
    setBookmark();
}

function showPrevPage() {
    currentImage--;
    if (currentImage < 0) {
        // Freeze on the current page.
        currentImage++;
    } else {
        updatePage();
    }
    updateDirectionButtons();
}

function showNextPage() {
    currentImage++;
    if (currentImage >= Math.max(totalImages, imageFiles.length)) {
        // Freeze on the current page.
        currentImage--;
    } else {
        updatePage();
    }
    updateDirectionButtons();
}

function scrollCurrentImageIntoView() {
    if(settings.pageDisplay == 0) {
        // This will scroll all the way up when Single Page is selected
		$("#mainContent").scrollTop(0);
    } else {
        // This will scroll to the image when Long Strip is selected
        $("#mainContent").stop().animate({
            scrollTop: $(".mainImage").eq(currentImage).offset().top + $("#mainContent").scrollTop() - $("#mainContent").offset().top
        }, 200);
    }
}

function updateScale() {
    var canvasArray = $("#mainContent > canvas");
    var maxheight = innerHeight - 50;
    
    canvasArray.css("width", "");
    canvasArray.css("height", "");
    canvasArray.css("maxWidth", "");
    canvasArray.css("maxHeight", "");

    if(settings.pageDisplay === 0) {
        canvasArray.addClass("hide");
        pageDisplayUpdate();
    }

    switch (settings.fitMode) {
        case kthoom.Key.B:
            canvasArray.css("maxWidth", "100%");
            canvasArray.css("maxHeight", maxheight + "px");
            break;
        case kthoom.Key.H:
            canvasArray.css("maxHeight", maxheight + "px");
            break;
        case kthoom.Key.W:
            canvasArray.css("width", "100%");
            break;
        default:
            break;
    }

    $("#mainContent > canvas.error").css("width", innerWidth - 100);
    $("#mainContent > canvas.error").css("height", 200);

    $("#mainContent").css({maxHeight: maxheight + 5});
    kthoom.setSettings();
    kthoom.saveSettings();
}

function keyHandler(evt) {
    var hasModifier = evt.ctrlKey || evt.shiftKey || evt.metaKey;
    switch (evt.keyCode) {
        case kthoom.Key.LEFT:
            if (hasModifier) break;
            showLeftPage();
            break;
        case kthoom.Key.RIGHT:
            if (hasModifier) break;
            showRightPage();
            break;
        case kthoom.Key.S:
            if (hasModifier) break;
            settings.pageDisplay = 0;
            pageDisplayUpdate();
            kthoom.setSettings();
            kthoom.saveSettings();
            break;
        case kthoom.Key.O:
            if (hasModifier) break;
            settings.pageDisplay = 1;
            pageDisplayUpdate();
            kthoom.setSettings();
            kthoom.saveSettings();
            break;
        case kthoom.Key.L:
            if (hasModifier) break;
            settings.rotateTimes--;
            if (settings.rotateTimes < 0) {
                settings.rotateTimes = 3;
            }
            updatePage();
			reloadImages();
            break;
        case kthoom.Key.R:
            if (hasModifier) break;
            settings.rotateTimes++;
            if (settings.rotateTimes > 3) {
                settings.rotateTimes = 0;
            }
            updatePage();
			reloadImages();
            break;
        case kthoom.Key.F:
            if (hasModifier) break;
            if (!settings.hflip && !settings.vflip) {
                settings.hflip = true;
            } else if (settings.hflip === true && settings.vflip === true) {
                settings.vflip = false;
                settings.hflip = false;
            } else if (settings.hflip === true) {
                settings.vflip = true;
                settings.hflip = false;
            } else if (settings.vflip === true) {
                settings.hflip = true;
            }
            updatePage();
			reloadImages();
            break;
        case kthoom.Key.W:
            if (hasModifier) break;
            settings.fitMode = kthoom.Key.W;
            updateScale();
            break;
        case kthoom.Key.H:
            if (hasModifier) break;
            settings.fitMode = kthoom.Key.H;
            updateScale();
            break;
        case kthoom.Key.B:
            if (hasModifier) break;
            settings.fitMode = kthoom.Key.B;
            updateScale();
            break;
        case kthoom.Key.N:
            if (hasModifier) break;
            settings.fitMode = kthoom.Key.N;
            updateScale();
            break;
        case kthoom.Key.SPACE:
            if (evt.shiftKey) {
                evt.preventDefault();
                // If it's Shift + Space and the container is at the top of the page
                showPrevPage();
            } else {
                evt.preventDefault();
                // If you're at the bottom of the page and you only pressed space
                showNextPage();
            }
            break;
        default:
            //console.log('KeyCode', evt.keyCode);
            break;
    }
}

function drawCanvas() {
    var maxheight = innerHeight - 50;
    var canvasElement = $("<canvas></canvas>");
    var x = canvasElement[0].getContext("2d");
    canvasElement.addClass("mainImage");

    switch (settings.fitMode) {
        case kthoom.Key.B:
            canvasElement.css("maxWidth", "100%");
            canvasElement.css("maxHeight", maxheight + "px");
            break;
        case kthoom.Key.H:
            canvasElement.css("maxHeight", maxheight + "px");
            break;
        case kthoom.Key.W:
            canvasElement.css("width", "100%");
            break;
        default:
            break;
    }

    if(settings.pageDisplay === 0) {
        canvasElement.addClass("hide");
    }

    //Fill with Placeholder text. setImage will override this
    canvasElement.width = innerWidth - 100;
    canvasElement.height = 200;
    x.fillStyle = "black";
    x.textAlign = "center";
    x.font = "24px sans-serif";
    x.strokeStyle = (settings.theme === "dark") ? "white" : "black";
    x.fillText("Loading Page #" + (currentImage + 1), innerWidth / 2, 100);

    $("#mainContent").append(canvasElement);
}

function updateArrows() {
    if ($('input[name="direction"]:checked').val() === "0") {
        $("#prev_page_key").html("&larr;");
        $("#next_page_key").html("&rarr;");
    } else {
        $("#prev_page_key").html("&rarr;");
        $("#next_page_key").html("&larr;");
    }
};

function init(filename) {
    var request = new XMLHttpRequest();
    request.open("GET", filename);
    request.responseType = "arraybuffer";
    request.addEventListener("load", function () {
        if (request.status >= 200 && request.status < 300) {
            loadFromArrayBuffer(request.response);
        } else {
            console.warn(request.statusText, request.responseText);
        }
    });
    kthoom.loadSettings();
    setTheme();
    updateScale();
    request.send();
    initProgressClick();
    document.body.className += /AppleWebKit/.test(navigator.userAgent) ? " webkit" : "";

    $(document).keydown(keyHandler);

    $(window).resize(function () {
        updateScale();
    });

    // Open TOC menu
    $("#slider").click(function () {
        $("#sidebar").toggleClass("open");
        $("#main").toggleClass("closed");
        $(this).toggleClass("icon-menu icon-right");

        // We need this in a timeout because if we call it during the CSS transition, IE11 shakes the page ¯\_(ツ)_/¯
        setTimeout(function () {
            // Focus on the TOC or the main content area, depending on which is open
            $("#main:not(.closed) #mainContent, #sidebar.open #tocView").focus();
            scrollTocToActive();
        }, 500);
    });

    // Open Settings modal
    $("#setting").click(function () {
        $("#settings-modal").toggleClass("md-show");
    });

    // On Settings input change
    $("#settings input").on("change", function () {
        // Get either the checked boolean or the assigned value
        var value = this.type === "checkbox" ? this.checked : this.value;

        // If it's purely numeric, parse it to an integer
        value = /^\d+$/.test(value) ? parseInt(value) : value;

        settings[this.name] = value;

        if (["hflip", "vflip", "rotateTimes"].includes(this.name)) {
            reloadImages();
        } else if (this.name === "direction") {
            updateDirectionButtons();
            return updateProgress();
        }

        updatePage();
        updateScale();
    });

    // Close modal
    $(".closer, .overlay").click(function () {
        $(".md-show").removeClass("md-show");
        $("#mainContent").focus(); // focus back on the main container so you use up/down keys without having to click on it
    });

    // TOC thumbnail pagination
    $("#thumbnails").on("click", "a", function () {
        currentImage = $(this).data("page") - 1;
        updatePage();
    });

    // Fullscreen mode
    if (typeof screenfull !== "undefined") {
        $("#fullscreen").click(function () {
            screenfull.toggle($("#container")[0]);
            // Focus on main container so you can use up/down keys immediately after fullscreen
            $("#mainContent").focus();
        });

        if (screenfull.raw) {
            var $button = $("#fullscreen");
            document.addEventListener(screenfull.raw.fullscreenchange, function () {
                screenfull.isFullscreen
                    ? $button.addClass("icon-resize-small").removeClass("icon-resize-full")
                    : $button.addClass("icon-resize-full").removeClass("icon-resize-small");
            });
        }
    }

    // Focus the scrollable area so that keyboard scrolling work as expected
    $("#mainContent").focus();

    $("#mainContent").swipe({
        swipeRight: function () {
            showLeftPage();
        },
        swipeLeft: function () {
            showRightPage();
        },
    });
    $(".mainImage").click(function (evt) {
        // Firefox does not support offsetX/Y, so we have to manually calculate
        // where the user clicked in the image.
        var mainContentWidth = $("#mainContent").width();
        var mainContentHeight = $("#mainContent").height();
        var comicWidth = evt.target.clientWidth;
        var comicHeight = evt.target.clientHeight;
        var offsetX = (mainContentWidth - comicWidth) / 2;
        var offsetY = (mainContentHeight - comicHeight) / 2;
        var clickX = evt.offsetX ? evt.offsetX : (evt.clientX - offsetX);
        var clickY = evt.offsetY ? evt.offsetY : (evt.clientY - offsetY);

        // Determine if the user clicked/tapped the left side or the
        // right side of the page.
        var clickedLeft = false;
        switch (settings.rotateTimes) {
            case 0:
                clickedLeft = clickX < (comicWidth / 2);
                break;
            case 1:
                clickedLeft = clickY < (comicHeight / 2);
                break;
            case 2:
                clickedLeft = clickX > (comicWidth / 2);
                break;
            case 3:
                clickedLeft = clickY > (comicHeight / 2);
                break;
        }
        if (clickedLeft) {
            showLeftPage();
        } else {
            showRightPage();
        }
    });

    // Scrolling up/down will update current image if a new image is into view (for Long Strip Display)
    $("#mainContent").scroll(function (){
        var scroll = $("#mainContent").scrollTop();
        var viewLength = 0;
        $(".mainImage").each(function(){
            viewLength += $(this).height();
        });
        if (settings.pageDisplay === 0) {
            // Don't trigger the scroll for Single Page
        } else if (scroll > prevScrollPosition) {
            //Scroll Down
            if (currentImage + 1 < imageFiles.length) {
                if (currentImageOffset(currentImage + 1) <= 1) {
                    currentImage = Math.floor((imageFiles.length) / (viewLength-viewLength/(imageFiles.length)) * scroll, 0);
                    if ( currentImage >= imageFiles.length) {
                        currentImage = imageFiles.length - 1;
                    }
                    console.log(currentImage);
                    scrollTocToActive();
                    updateProgress();
                }
            }
        } else {
            //Scroll Up
            if (currentImage - 1 > -1) {
                if (currentImageOffset(currentImage - 1) >= 0) {
                    currentImage = Math.floor((imageFiles.length) / (viewLength-viewLength/(imageFiles.length)) * scroll, 0);
                    console.log(currentImage);
                    scrollTocToActive();
                    updateProgress();
                }
            }
        }
        // Update scroll position
        prevScrollPosition = scroll;
    });
}

function currentImageOffset(imageIndex) {
    return $(".mainImage").eq(imageIndex).offset().top - $("#mainContent").position().top
}

function setBookmark() {
  // get csrf_token
    let csrf_token = $("input[name='csrf_token']").val();
    //This sends a bookmark update to calibreweb.
    $.ajax(calibre.bookmarkUrl, {
        method: "post",
        data: {
            csrf_token: csrf_token,
            bookmark: currentImage
        }
    }).fail(function (xhr, status, error) {
        console.error(error);
    });
}

$(function() {
    $('input[name="direction"]').change(function () {
        updateArrows();
    });

    $('#left').click(function () {
        showLeftPage();
    });
    $('#right').click(function () {
        showRightPage();
    });
});
