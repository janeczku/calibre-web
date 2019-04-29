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

// This file expects to be invoked as a Worker (see onmessage below).
importScripts('../io/bytestream.js');
importScripts('archive.js');

const UnarchiveState = {
  NOT_STARTED: 0,
  UNARCHIVING: 1,
  WAITING: 2,
  FINISHED: 3,
};

// State - consider putting these into a class.
let unarchiveState = UnarchiveState.NOT_STARTED;
let bytestream = null;
let allLocalFiles = null;
let logToConsole = false;

// Progress variables.
let currentFilename = "";
let currentFileNumber = 0;
let currentBytesUnarchivedInFile = 0;
let currentBytesUnarchived = 0;
let totalUncompressedBytesInArchive = 0;
let totalFilesInArchive = 0;

// Helper functions.
const info = function(str) {
  postMessage(new bitjs.archive.UnarchiveInfoEvent(str));
};
const err = function(str) {
  postMessage(new bitjs.archive.UnarchiveErrorEvent(str));
};
const postProgress = function() {
  postMessage(new bitjs.archive.UnarchiveProgressEvent(
      currentFilename,
      currentFileNumber,
      currentBytesUnarchivedInFile,
      currentBytesUnarchived,
      totalUncompressedBytesInArchive,
      totalFilesInArchive,
      bytestream.getNumBytesRead(),
  ));
};

// Removes all characters from the first zero-byte in the string onwards.
const readCleanString = function(bstr, numBytes) {
  const str = bstr.readString(numBytes);
  const zIndex = str.indexOf(String.fromCharCode(0));
  return zIndex != -1 ? str.substr(0, zIndex) : str;
};

class TarLocalFile {
  // takes a ByteStream and parses out the local file information
  constructor(bstream) {
    this.isValid = false;

    let bytesRead = 0;

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

    if (this.maybeMagic == "ustar") {
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
      const sizeInBytes = parseInt(this.size);
      this.fileData = new Uint8Array(bstream.readBytes(sizeInBytes));
      bytesRead += sizeInBytes;
      if (this.name.length > 0 && this.size > 0 && this.fileData && this.fileData.buffer) {
        this.isValid = true;
      }

      // Round up to 512-byte blocks.
      const remaining = 512 - bytesRead % 512;
      if (remaining > 0 && remaining < 512) {
        bstream.readBytes(remaining);
      }
    } else if (this.typeflag == 5) {
       info("  This is a directory.")
    }
  }
}

const untar = function() {
  let bstream = bytestream.tee();

  // While we don't encounter an empty block, keep making TarLocalFiles.
  while (bstream.peekNumber(4) != 0) {
    const oneLocalFile = new TarLocalFile(bstream);
    if (oneLocalFile && oneLocalFile.isValid) {
      // If we make it to this point and haven't thrown an error, we have successfully
      // read in the data for a local file, so we can update the actual bytestream.
      bytestream = bstream.tee();

      allLocalFiles.push(oneLocalFile);
      totalUncompressedBytesInArchive += oneLocalFile.size;

      // update progress
      currentFilename = oneLocalFile.filename;
      currentFileNumber = totalFilesInArchive++;
      currentBytesUnarchivedInFile = oneLocalFile.size;
      currentBytesUnarchived += oneLocalFile.size;
      postMessage(new bitjs.archive.UnarchiveExtractEvent(oneLocalFile));
      postProgress();
    }
  }
  totalFilesInArchive = allLocalFiles.length;

  postProgress();

  bytestream = bstream.tee();
};

// event.data.file has the first ArrayBuffer.
// event.data.bytes has all subsequent ArrayBuffers.
onmessage = function(event) {
  const bytes = event.data.file || event.data.bytes;
  logToConsole = !!event.data.logToConsole;

  // This is the very first time we have been called. Initialize the bytestream.
  if (!bytestream) {
    bytestream = new bitjs.io.ByteStream(bytes);
  } else {
    bytestream.push(bytes);
  }

  if (unarchiveState === UnarchiveState.NOT_STARTED) {
    currentFilename = "";
    currentFileNumber = 0;
    currentBytesUnarchivedInFile = 0;
    currentBytesUnarchived = 0;
    totalUncompressedBytesInArchive = 0;
    totalFilesInArchive = 0;
    allLocalFiles = [];
  
    postMessage(new bitjs.archive.UnarchiveStartEvent());

    unarchiveState = UnarchiveState.UNARCHIVING;

    postProgress();
  }

  if (unarchiveState === UnarchiveState.UNARCHIVING ||
    unarchiveState === UnarchiveState.WAITING) {
    try {
      untar();
      unarchiveState = UnarchiveState.FINISHED;
      postMessage(new bitjs.archive.UnarchiveFinishEvent());
    } catch (e) {
      if (typeof e === 'string' && e.startsWith('Error!  Overflowed')) {
        // Overrun the buffer.
        unarchiveState = UnarchiveState.WAITING;
      } else {
        console.error('Found an error while untarring');
        console.dir(e);
        throw e;
      }
    }
  }
};
