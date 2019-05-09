/**
 * archive.js
 *
 * Provides base functionality for unarchiving.
 *
 * Licensed under the MIT License
 *
 * Copyright(c) 2011 Google Inc.
 */

var bitjs = bitjs || {};
bitjs.archive = bitjs.archive || {};

/**
 * An unarchive event.
 */
bitjs.archive.UnarchiveEvent = class {
  /**
   * @param {string} type The event type.
   */
  constructor(type) {
    /**
     * The event type.
     * @type {string}
     */
    this.type = type;
  }
}

/**
 * The UnarchiveEvent types.
 */
bitjs.archive.UnarchiveEvent.Type = {
  START: 'start',
  PROGRESS: 'progress',
  EXTRACT: 'extract',
  FINISH: 'finish',
  INFO: 'info',
  ERROR: 'error'
};

/**
 * Useful for passing info up to the client (for debugging).
 */
bitjs.archive.UnarchiveInfoEvent = class extends bitjs.archive.UnarchiveEvent {
  /**
   * @param {string} msg The info message.
   */
  constructor(msg) {
    super(bitjs.archive.UnarchiveEvent.Type.INFO);

    /**
     * The information message.
     * @type {string}
     */
    this.msg = msg;
  }
}

/**
 * An unrecoverable error has occured.
 */
bitjs.archive.UnarchiveErrorEvent = class extends bitjs.archive.UnarchiveEvent {
  /**
   * @param {string} msg The error message.
   */
  constructor(msg) {
    super(bitjs.archive.UnarchiveEvent.Type.ERROR);

    /**
     * The information message.
     * @type {string}
     */
    this.msg = msg;
  }
}

/**
 * Start event.
 */
bitjs.archive.UnarchiveStartEvent = class extends bitjs.archive.UnarchiveEvent {
  constructor() {
    super(bitjs.archive.UnarchiveEvent.Type.START);
  }
}

/**
 * Finish event.
 */
bitjs.archive.UnarchiveFinishEvent = class extends bitjs.archive.UnarchiveEvent {
  constructor() {
    super(bitjs.archive.UnarchiveEvent.Type.FINISH);
  }
}

/**
 * Progress event.
 */
bitjs.archive.UnarchiveProgressEvent = class extends bitjs.archive.UnarchiveEvent {
  /**
   * @param {string} currentFilename
   * @param {number} currentFileNumber
   * @param {number} currentBytesUnarchivedInFile
   * @param {number} currentBytesUnarchived
   * @param {number} totalUncompressedBytesInArchive
   * @param {number} totalFilesInArchive
   * @param {number} totalCompressedBytesRead
   */
  constructor(currentFilename, currentFileNumber, currentBytesUnarchivedInFile,
      currentBytesUnarchived, totalUncompressedBytesInArchive, totalFilesInArchive,
      totalCompressedBytesRead) {
    super(bitjs.archive.UnarchiveEvent.Type.PROGRESS);

    this.currentFilename = currentFilename;
    this.currentFileNumber = currentFileNumber;
    this.currentBytesUnarchivedInFile = currentBytesUnarchivedInFile;
    this.totalFilesInArchive = totalFilesInArchive;
    this.currentBytesUnarchived = currentBytesUnarchived;
    this.totalUncompressedBytesInArchive = totalUncompressedBytesInArchive;
    this.totalCompressedBytesRead = totalCompressedBytesRead;
  }
}

/**
 * Extract event.
 */
bitjs.archive.UnarchiveExtractEvent = class extends bitjs.archive.UnarchiveEvent {
  /**
   * @param {UnarchivedFile} unarchivedFile
   */
  constructor(unarchivedFile) {
    super(bitjs.archive.UnarchiveEvent.Type.EXTRACT);

    /**
     * @type {UnarchivedFile}
     */
    this.unarchivedFile = unarchivedFile;
  }
}

/**
 * All extracted files returned by an Unarchiver will implement
 * the following interface:
 *
 * interface UnarchivedFile {
 *   string filename
 *   TypedArray fileData  
 * }
 *
 */

/**
 * Base class for all Unarchivers.
 */
bitjs.archive.Unarchiver = class {
  /**
   * @param {ArrayBuffer} arrayBuffer The Array Buffer.
   * @param {string} opt_pathToBitJS Optional string for where the BitJS files are located.
   */
  constructor(arrayBuffer, opt_pathToBitJS) {
    /**
     * The ArrayBuffer object.
     * @type {ArrayBuffer}
     * @protected
     */
    this.ab = arrayBuffer;

    /**
     * The path to the BitJS files.
     * @type {string}
     * @private
     */
    this.pathToBitJS_ = opt_pathToBitJS || '/';

    /**
     * A map from event type to an array of listeners.
     * @type {Map.<string, Array>}
     */
    this.listeners_ = {};
    for (let type in bitjs.archive.UnarchiveEvent.Type) {
      this.listeners_[bitjs.archive.UnarchiveEvent.Type[type]] = [];
    }

    /**
     * Private web worker initialized during start().
     * @type {Worker}
     * @private
     */
    this.worker_ = null;
  }

  /**
   * This method must be overridden by the subclass to return the script filename.
   * @return {string} The script filename.
   * @protected.
   */
  getScriptFileName() {
    throw 'Subclasses of AbstractUnarchiver must overload getScriptFileName()';
  }

  /**
   * Adds an event listener for UnarchiveEvents.
   *
   * @param {string} Event type.
   * @param {function} An event handler function.
   */
  addEventListener(type, listener) {
    if (type in this.listeners_) {
      if (this.listeners_[type].indexOf(listener) == -1) {
        this.listeners_[type].push(listener);
      }
    }
  }

  /**
   * Removes an event listener.
   *
   * @param {string} Event type.
   * @param {EventListener|function} An event listener or handler function.
   */
  removeEventListener(type, listener) {
    if (type in this.listeners_) {
      const index = this.listeners_[type].indexOf(listener);
      if (index != -1) {
        this.listeners_[type].splice(index, 1);
      }
    }
  }

  /**
   * Receive an event and pass it to the listener functions.
   *
   * @param {bitjs.archive.UnarchiveEvent} e
   * @private
   */
  handleWorkerEvent_(e) {
    if ((e instanceof bitjs.archive.UnarchiveEvent || e.type) &&
        this.listeners_[e.type] instanceof Array) {
      this.listeners_[e.type].forEach(function (listener) { listener(e) });
      if (e.type == bitjs.archive.UnarchiveEvent.Type.FINISH) {
          this.worker_.terminate();
      }
    } else {
      console.log(e);
    }
  }

  /**
   * Starts the unarchive in a separate Web Worker thread and returns immediately.
   */
  start() {
    const me = this;
    const scriptFileName = this.pathToBitJS_ + this.getScriptFileName();
    if (scriptFileName) {
      this.worker_ = new Worker(scriptFileName);

      this.worker_.onerror = function(e) {
        console.log('Worker error: message = ' + e.message);
        throw e;
      };

      this.worker_.onmessage = function(e) {
        if (typeof e.data == 'string') {
          // Just log any strings the workers pump our way.
          console.log(e.data);
        } else {
          // Assume that it is an UnarchiveEvent.  Some browsers preserve the 'type'
          // so that instanceof UnarchiveEvent returns true, but others do not.
          me.handleWorkerEvent_(e.data);
        }
      };

      const ab = this.ab;
      this.worker_.postMessage({
        file: ab,
        logToConsole: false,
      });
      this.ab = null;
    }
  }

  /**
   * Adds more bytes to the unarchiver's Worker thread.
   */
  update(ab) {
    if (this.worker_) {
      this.worker_.postMessage({bytes: ab});
    }
  }

  /**
   * Terminates the Web Worker for this Unarchiver and returns immediately.
   */
  stop() {
    if (this.worker_) {
      this.worker_.terminate();
    }
  }
}


/**
 * Unzipper
 */
bitjs.archive.Unzipper = class extends bitjs.archive.Unarchiver {
  constructor(arrayBuffer, opt_pathToBitJS) {
    super(arrayBuffer, opt_pathToBitJS);
  }

  getScriptFileName() { return 'archive/unzip.js'; }
}


/**
 * Unrarrer
 */
bitjs.archive.Unrarrer = class extends bitjs.archive.Unarchiver {
  constructor(arrayBuffer, opt_pathToBitJS) {
    super(arrayBuffer, opt_pathToBitJS);
  }

  getScriptFileName() { return 'archive/unrar.js'; }
}

/**
 * Untarrer
 * @extends {bitjs.archive.Unarchiver}
 * @constructor
 */
bitjs.archive.Untarrer = class extends bitjs.archive.Unarchiver {
  constructor(arrayBuffer, opt_pathToBitJS) {
    super(arrayBuffer, opt_pathToBitJS);
  }

  getScriptFileName() { return 'archive/untar.js'; };
}

/**
 * Factory method that creates an unarchiver based on the byte signature found
 * in the arrayBuffer.
 * @param {ArrayBuffer} ab
 * @param {string=} opt_pathToBitJS Path to the unarchiver script files.
 * @return {bitjs.archive.Unarchiver}
 */
bitjs.archive.GetUnarchiver = function(ab, opt_pathToBitJS) {
  if (ab.byteLength < 10) {
    return null;
  }

  let unarchiver = null;
  const pathToBitJS = opt_pathToBitJS || '';
  const h = new Uint8Array(ab, 0, 10);

  if (h[0] == 0x52 && h[1] == 0x61 && h[2] == 0x72 && h[3] == 0x21) { // Rar!
    unarchiver = new bitjs.archive.Unrarrer(ab, pathToBitJS);
  } else if (h[0] == 0x50 && h[1] == 0x4B) { // PK (Zip)
    unarchiver = new bitjs.archive.Unzipper(ab, pathToBitJS);
  } else { // Try with tar
    unarchiver = new bitjs.archive.Untarrer(ab, pathToBitJS);
  }
  return unarchiver;
};
