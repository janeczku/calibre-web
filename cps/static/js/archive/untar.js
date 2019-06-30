/**
 * untar.js
 *
 * Licensed under the MIT License
 *
 * Copyright(c) 2011 Google Inc.
 *
 * Reference Documentation:
 *
 * TAR format: http://www.gnu.org/software/automake/manual/tar/Standard.html
 */

/* global bitjs, importScripts, Uint8Array */

// This file expects to be invoked as a Worker (see onmessage below).
importScripts("../io/bytestream.js");
importScripts("archive.js");

// Progress variables.
var currentFilename = "";
var currentFileNumber = 0;
var currentBytesUnarchivedInFile = 0;
var currentBytesUnarchived = 0;
var totalUncompressedBytesInArchive = 0;
var totalFilesInArchive = 0;
var allLocalFiles = [];

// Helper functions.
var info = function(str) {
    postMessage(new bitjs.archive.UnarchiveInfoEvent(str));
};
var err = function(str) {
    postMessage(new bitjs.archive.UnarchiveErrorEvent(str));
};

// Removes all characters from the first zero-byte in the string onwards.
var readCleanString = function(bstr, numBytes) {
    var str = bstr.readString(numBytes);
    var zIndex = str.indexOf(String.fromCharCode(0));
    return zIndex != -1 ? str.substr(0, zIndex) : str;
};

var postProgress = function() {
    postMessage(new bitjs.archive.UnarchiveProgressEvent(
        currentFilename,
        currentFileNumber,
        currentBytesUnarchivedInFile,
        currentBytesUnarchived,
        totalUncompressedBytesInArchive,
        totalFilesInArchive
    ));
};

// takes a ByteStream and parses out the local file information
var TarLocalFile = function(bstream) {
    this.isValid = false;

    var bytesRead = 0;

    // Read in the header block
    this.name = readCleanString(bstream, 100);
    this.mode = readCleanString(bstream, 8);
    this.uid = readCleanString(bstream, 8);
    this.gid = readCleanString(bstream, 8);
    this.size = parseInt(readCleanString(bstream, 12), 8);
    this.mtime = readCleanString(bstream, 12);
    this.chksum = readCleanString(bstream, 8);
    this.typeflag = readCleanString(bstream, 1);
    this.linkname = readCleanString(bstream, 100);
    this.maybeMagic = readCleanString(bstream, 6);

    if (this.maybeMagic === "ustar") {
        this.version = readCleanString(bstream, 2);
        this.uname = readCleanString(bstream, 32);
        this.gname = readCleanString(bstream, 32);
        this.devmajor = readCleanString(bstream, 8);
        this.devminor = readCleanString(bstream, 8);
        this.prefix = readCleanString(bstream, 155);

        if (this.prefix.length) {
            this.name = this.prefix + this.name;
        }
        bstream.readBytes(12); // 512 - 500
    } else {
        bstream.readBytes(255); // 512 - 257
    }

    bytesRead += 512;

    // Done header, now rest of blocks are the file contents.
    this.filename = this.name;
    this.fileData = null;

    info("Untarring file '" + this.filename + "'");
    info("  size = " + this.size);
    info("  typeflag = " + this.typeflag);

    // A regular file.
    if (this.typeflag == 0) {
        info("  This is a regular file.");
        var sizeInBytes = parseInt(this.size);
        this.fileData = new Uint8Array(bstream.readBytes(sizeInBytes));
        bytesRead += sizeInBytes;
        if (this.name.length > 0 && this.size > 0 && this.fileData && this.fileData.buffer) {
            this.isValid = true;
        }

        // Round up to 512-byte blocks.
        var remaining = 512 - (bytesRead % 512);
        if (remaining > 0 && remaining < 512) {
            bstream.readBytes(remaining);
        }
    } else if (this.typeflag == 5) {
        info("  This is a directory.");
    }
};


var untar = function(arrayBuffer) {
    postMessage(new bitjs.archive.UnarchiveStartEvent());
    currentFilename = "";
    currentFileNumber = 0;
    currentBytesUnarchivedInFile = 0;
    currentBytesUnarchived = 0;
    totalUncompressedBytesInArchive = 0;
    totalFilesInArchive = 0;
    allLocalFiles = [];

    var bstream = new bitjs.io.ByteStream(arrayBuffer);
    postProgress();
    /*
    // go through whole file, read header of each block and memorize, filepointer
    */
    while (bstream.peekNumber(4) !== 0) {
        var localFile = new TarLocalFile(bstream);
        allLocalFiles.push(localFile);
        postProgress();
    }
    // got all local files, now sort them
    allLocalFiles.sort(alphanumCase);

    allLocalFiles.forEach(function(oneLocalFile) {
        // While we don't encounter an empty block, keep making TarLocalFiles.
        if (oneLocalFile && oneLocalFile.isValid) {
            // If we make it to this point and haven't thrown an error, we have successfully
            // read in the data for a local file, so we can update the actual bytestream.
            totalUncompressedBytesInArchive += oneLocalFile.size;

            // update progress
            currentFilename = oneLocalFile.filename;
            currentFileNumber = totalFilesInArchive++;
            currentBytesUnarchivedInFile = oneLocalFile.size;
            currentBytesUnarchived += oneLocalFile.size;
            postMessage(new bitjs.archive.UnarchiveExtractEvent(oneLocalFile));
            postProgress();
        }
    });
    totalFilesInArchive = allLocalFiles.length;

    postProgress();
    postMessage(new bitjs.archive.UnarchiveFinishEvent());
};

// event.data.file has the first ArrayBuffer.
// event.data.bytes has all subsequent ArrayBuffers.
onmessage = function(event) {
    try {
        untar(event.data.file, true);
    } catch (e) {
        if (typeof e === "string" && e.startsWith("Error!  Overflowed")) {
            // Overrun the buffer.
            // unarchiveState = UnarchiveState.WAITING;
        } else {
            err("Found an error while untarring");
            err(e);
            throw e;
        }
    }
};
