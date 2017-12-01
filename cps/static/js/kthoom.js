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
/* global screenfull */

// var start = 0;

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
var currentImage = 0;
var imageFiles = [];
var imageFilenames = [];
var totalImages = 0;

var settings = {
    hflip: false, 
    vflip: false, 
    rotateTimes: 0,
    fitMode: kthoom.Key.B,
    theme: "light"
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


// Stores an image filename and its data: URI.
kthoom.ImageFile = function(file) {
    this.filename = file.filename;
    this.dataURI = file.fileData;
    this.data = file;
};


kthoom.initProgressMeter = function() {
    $("#Progress").removeClass("hide");
    $("#Progress").click(function(e) {
        var page = Math.max(1, Math.ceil((e.offsetX / $(this).width()) * totalImages)) - 1;
        currentImage = page;
        updatePage();
    });
};

kthoom.setProgressMeter = function(optLabel) {
    var pct = imageFiles.length / totalImages * 100;
    if (pct === 100) {
        //smartpct = 100;
        getElem("progress_title").innerHTML = "Complete";
    } else {
        var labelText = pct.toFixed(2) + "% " + imageFiles.length + "/" + totalImages + "";
        if (optLabel) {
            labelText = optLabel + " " + labelText;
        }
        getElem("progress_title").innerHTML=labelText;
    }
    if (!isNaN(pct)) {
        getElem("meter").style.width = pct + "%";
    }

    getElem("meter2").style.width= 100 * (totalImages === 0 ? 0 : ((currentImage + 1) / totalImages)) + "%";
    getElem("page").innerHTML=(currentImage + 1) + "/" + totalImages ;
};

function loadFromArrayBuffer(ab) {
    var f = [];
    if (typeof ab !== "object") {
        ab = JSON.parse(ab);
    }
    f.fileData = ab.content;
    f.filename = ab.name;
    // add any new pages based on the filename
    if (imageFilenames.indexOf(f.filename) === -1) {
        imageFilenames.push(f.filename);
        imageFiles.push(new kthoom.ImageFile(f));
                        
        // add thumbnails to the TOC list
        $("#thumbnails").append(
            "<li>" +
                "<a data-page='" + imageFiles.length + "'>" +
                    "<img src='" + imageFiles[imageFiles.length - 1].dataURI + "'/>" +
                    "<span>" + imageFiles.length + "</span>" +
                "</a>" +
            "</li>"
        );
    }
    // var percentage = (ab.page + 1) / (ab.last + 1);
    totalImages = ab.last + 1;
    kthoom.setProgressMeter("Unzipping");
    // lastCompletion = percentage * 100;

    // display first page if we haven't yet
    if (imageFiles.length === currentImage + 1) {
        updatePage();
    }
}


function updatePage() {
    getElem("page").innerHTML=(currentImage + 1) + "/" + totalImages ;
    getElem("meter2").style.width= 100 * (totalImages === 0 ? 0 : ((currentImage + 1) / totalImages)) + "%";
    if (imageFiles[currentImage]) {
        setImage(imageFiles[currentImage].dataURI);
    } else {
        setImage("loading");
    }

    $("body").toggleClass("dark-theme", settings.theme === "dark");

    kthoom.setSettings();
    kthoom.saveSettings();
}

function setImage(url) {
    var canvas = $("#mainImage")[0];
    var x = $("#mainImage")[0].getContext("2d");
    $("#mainText").hide();
    if (url === "loading") {
        updateScale(true);
        canvas.width = innerWidth - 100;
        canvas.height = 200;
        x.fillStyle = "black";
        x.textAlign = "center";
        x.font = "24px sans-serif";
        x.strokeStyle = "black";
        x.fillText("Loading Page #" + (currentImage + 1), innerWidth / 2, 100);
    } else {
        if (url === "error") {
            updateScale(true);
            canvas.width = innerWidth - 100;
            canvas.height = 200;
            x.fillStyle = "black";
            x.textAlign = "center";
            x.font = "24px sans-serif";
            x.strokeStyle = "black";
            x.fillText("Unable to decompress image #" + (currentImage + 1), innerWidth / 2, 100);
        } else {
            if ($("body").css("scrollHeight") / innerHeight > 1) {
                $("body").css("overflowY", "scroll");
            }

            var img = new Image();
            img.onerror = function() {
                canvas.width = innerWidth - 100;
                canvas.height = 300;
                updateScale(true);
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
                    }
                    xhr.send(null);
                } else if (!/(jpg|jpeg|png|gif)$/.test(imageFiles[currentImage].filename) && imageFiles[currentImage].data.uncompressedSize < 10 * 1024) {
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

                updateScale(false);

                canvas.style.display = "";
                $("body").css("overflowY", "");
                x.restore();
            };
            img.src = url;
        }
    }
}

function showPrevPage() {
    currentImage--;
    if (currentImage < 0) {
        // Freeze on the current page.
        currentImage++;
    } else {
        updatePage();
    }
}

function showNextPage() {
    currentImage++;
    if (currentImage >= Math.max(totalImages, imageFiles.length)) {
        // Freeze on the current page.
        currentImage--;
    } else {
        updatePage();
    }
}

function updateScale(clear) {
    var mainImageStyle = getElem("mainImage").style;
    mainImageStyle.width = "";
    mainImageStyle.height = "";
    mainImageStyle.maxWidth = "";
    mainImageStyle.maxHeight = "";
    var maxheight = innerHeight - 50;

    if (!clear) {
        switch (settings.fitMode) {
            case kthoom.Key.B:
                mainImageStyle.maxWidth = "100%";
                mainImageStyle.maxHeight = maxheight + "px";
                break;
            case kthoom.Key.H:
                mainImageStyle.height = maxheight + "px";
                break;
            case kthoom.Key.W:
                mainImageStyle.width = "100%";
                break;
            default:
                break;
        }
    }
    $("#mainContent").css({maxHeight: maxheight + 5});
    kthoom.setSettings();
    kthoom.saveSettings();
}

function keyHandler(evt) {
    var code = evt.keyCode;

    if ($("#progress").css("display") === "none") {
        return;
    }
    // canKeyNext = (($("body").css("offsetWidth") + $("body").css("scrollLeft")) / $("body").css("scrollWidth")) >= 1;
    // canKeyPrev = (scrollX <= 0);

    if (evt.ctrlKey || evt.shiftKey || evt.metaKey) return;
    switch (code) {
        case kthoom.Key.LEFT:
            showPrevPage();
            break;
        case kthoom.Key.RIGHT:
            showNextPage();
            break;
        case kthoom.Key.L:
            settings.rotateTimes--;
            if (settings.rotateTimes < 0) {
                settings.rotateTimes = 3;
            }
            updatePage();
            break;
        case kthoom.Key.R:
            settings.rotateTimes++;
            if (settings.rotateTimes > 3) {
                settings.rotateTimes = 0;
            }
            updatePage();
            break;
        case kthoom.Key.F:
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
            break;
        case kthoom.Key.W:
            settings.fitMode = kthoom.Key.W;
            updateScale(false);
            break;
        case kthoom.Key.H:
            settings.fitMode = kthoom.Key.H;
            updateScale(false);
            break;
        case kthoom.Key.B:
            settings.fitMode = kthoom.Key.B;
            updateScale(false);
            break;
        case kthoom.Key.N:
            settings.fitMode = kthoom.Key.N;
            updateScale(false);
            break;
        default:
            //console.log('KeyCode = ' + code);
            break;
    }
}

function ImageLoadCallback() {
    var jso = this.response;
    // Unable to decompress file, or no response from server
    if (jso === null) {
        setImage("error");
    } else {
        if (jso.page !== jso.last) {
            this.open("GET", this.fileid + "/" + (jso.page + 1));
            this.addEventListener("load", ImageLoadCallback);
            this.send();
        }
        /*else
        {
            var diff = ((new Date).getTime() - start) / 1000;
            console.log("Transfer done in " + diff + "s");
        }*/
        loadFromArrayBuffer(jso);
    }
}
function init(fileid) {
    // start = (new Date).getTime();
    var request = new XMLHttpRequest();
    request.open("GET", fileid);
    request.responseType = "json";
    request.fileid = fileid.substring(0, fileid.length - 2);
    request.addEventListener("load", ImageLoadCallback);
    request.send();
    kthoom.initProgressMeter();
    document.body.className += /AppleWebKit/.test(navigator.userAgent) ? " webkit" : "";
    kthoom.loadSettings();
    updateScale(true);
    $(document).keydown(keyHandler);

    $(window).resize(function() {
        updateScale(false);
    });

    // Open TOC menu
    $("#slider").click(function() {
        $("#sidebar").toggleClass("open");
        $("#main").toggleClass("closed");
        $(this).toggleClass("icon-menu icon-right");
    });

    // Open Settings modal
    $("#setting").click(function() {
        $("#settings-modal").toggleClass("md-show");
    });

    // On Settings input change
    $("#settings input").on("change", function() {
        // Get either the checked boolean or the assigned value
        var value = this.type === "checkbox" ? this.checked : this.value;

        // If it's purely numeric, parse it to an integer
        value = /^\d+$/.test(value) ? parseInt(value) : value;

        settings[this.name] = value;
        updatePage();
        updateScale(false);
    });

    // Close modal
    $(".closer, .overlay").click(function() {
        $(".md-show").removeClass("md-show");
    });

    // TOC thumbnail pagination
    $("#thumbnails").on("click", "a", function() {
        currentImage = $(this).data("page") - 1;
        updatePage();
    });

    // Fullscreen mode
    if (typeof screenfull !== "undefined") {
        $("#fullscreen").click(function() {
            screenfull.toggle($("#container")[0]);
        });

        if (screenfull.raw) {
            var $button = $("#fullscreen");
            document.addEventListener(screenfull.raw.fullscreenchange, function() {
                screenfull.isFullscreen
                    ? $button.addClass("icon-resize-small").removeClass("icon-resize-full")
                    : $button.addClass("icon-resize-full").removeClass("icon-resize-small");
            });
        }
    }

    $("#mainImage").click(function(evt) {
        // Firefox does not support offsetX/Y so we have to manually calculate
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
        var clickedPrev = false;
        switch (settings.rotateTimes) {
            case 0:
                clickedPrev = clickX < (comicWidth / 2);
                break;
            case 1:
                clickedPrev = clickY < (comicHeight / 2);
                break;
            case 2:
                clickedPrev = clickX > (comicWidth / 2);
                break;
            case 3:
                clickedPrev = clickY > (comicHeight / 2);
                break;
        }
        if (clickedPrev) {
            showPrevPage();
        } else {
            showNextPage();
        }
    });
}
