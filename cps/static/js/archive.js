/**
 * archive.js
 *
 * Provides base functionality for unarchiving.
 *
 * Licensed under the MIT License
 *
 * Copyright(c) 2011 Google Inc.
 */

/* global bitjs */

var bitjs = bitjs || {};
bitjs.archive = bitjs.archive || {};

(function() {

    // ===========================================================================
    // Stolen from Closure because it's the best way to do Java-like inheritance.
    bitjs.base = function(me, optMethodName, varArgs) {
        var caller = arguments.callee.caller;
        if (caller.superClass_) {
            // This is a constructor. Call the superclass constructor.
            return caller.superClass_.constructor.apply(
                me, Array.prototype.slice.call(arguments, 1));
        }

        var args = Array.prototype.slice.call(arguments, 2);
        var foundCaller = false;
        for (var ctor = me.constructor;
            ctor; ctor = ctor.superClass_ && ctor.superClass_.constructor) {
            if (ctor.prototype[optMethodName] === caller) {
                foundCaller = true;
            } else if (foundCaller) {
                return ctor.prototype[optMethodName].apply(me, args);
            }
        }

        // If we did not find the caller in the prototype chain,
        // then one of two things happened:
        // 1) The caller is an instance method.
        // 2) This method was not called by the right caller.
        if (me[optMethodName] === caller) {
            return me.constructor.prototype[optMethodName].apply(me, args);
        } else {
            throw Error(
                "goog.base called from a method of one name " +
                "to a method of a different name");
        }
    };
    bitjs.inherits = function(childCtor, parentCtor) {
        /** @constructor */
        function TempCtor() {}
        TempCtor.prototype = parentCtor.prototype;
        childCtor.superClass_ = parentCtor.prototype;
        childCtor.prototype = new TempCtor();
        childCtor.prototype.constructor = childCtor;
    };
    // ===========================================================================

    /**
     * An unarchive event.
     *
     * @param {string} type The event type.
     * @constructor
     */
    bitjs.archive.UnarchiveEvent = function(type) {
        /**
        * The event type.
        *
        * @type {string}
        */
        this.type = type;
    };

    /**
     * The UnarchiveEvent types.
     */
    bitjs.archive.UnarchiveEvent.Type = {
        START: "start",
        PROGRESS: "progress",
        EXTRACT: "extract",
        FINISH: "finish",
        INFO: "info",
        ERROR: "error"
    };

    /**
     * Useful for passing info up to the client (for debugging).
     *
     * @param {string} msg The info message.
     */
    bitjs.archive.UnarchiveInfoEvent = function(msg) {
        bitjs.base(this, bitjs.archive.UnarchiveEvent.Type.INFO);

        /**
        * The information message.
        *
        * @type {string}
        */
        this.msg = msg;
    };
    bitjs.inherits(bitjs.archive.UnarchiveInfoEvent, bitjs.archive.UnarchiveEvent);

    /**
     * An unrecoverable error has occured.
     *
     * @param {string} msg The error message.
     */
    bitjs.archive.UnarchiveErrorEvent = function(msg) {
        bitjs.base(this, bitjs.archive.UnarchiveEvent.Type.ERROR);

        /**
        * The information message.
        *
        * @type {string}
        */
        this.msg = msg;
    };
    bitjs.inherits(bitjs.archive.UnarchiveErrorEvent, bitjs.archive.UnarchiveEvent);

    /**
     * Start event.
     *
     * @param {string} msg The info message.
     */
    bitjs.archive.UnarchiveStartEvent = function() {
        bitjs.base(this, bitjs.archive.UnarchiveEvent.Type.START);
    };
    bitjs.inherits(bitjs.archive.UnarchiveStartEvent, bitjs.archive.UnarchiveEvent);

    /**
     * Finish event.
     *
     * @param {string} msg The info message.
     */
    bitjs.archive.UnarchiveFinishEvent = function() {
        bitjs.base(this, bitjs.archive.UnarchiveEvent.Type.FINISH);
    };
    bitjs.inherits(bitjs.archive.UnarchiveFinishEvent, bitjs.archive.UnarchiveEvent);

    /**
     * Progress event.
     */
    bitjs.archive.UnarchiveProgressEvent = function(
            currentFilename,
            currentFileNumber,
            currentBytesUnarchivedInFile,
            currentBytesUnarchived,
            totalUncompressedBytesInArchive,
            totalFilesInArchive)
    {
        bitjs.base(this, bitjs.archive.UnarchiveEvent.Type.PROGRESS);

        this.currentFilename = currentFilename;
        this.currentFileNumber = currentFileNumber;
        this.currentBytesUnarchivedInFile = currentBytesUnarchivedInFile;
        this.totalFilesInArchive = totalFilesInArchive;
        this.currentBytesUnarchived = currentBytesUnarchived;
        this.totalUncompressedBytesInArchive = totalUncompressedBytesInArchive;
    };
    bitjs.inherits(bitjs.archive.UnarchiveProgressEvent, bitjs.archive.UnarchiveEvent);

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
     * Extract event.
     */
    bitjs.archive.UnarchiveExtractEvent = function(unarchivedFile) {
        bitjs.base(this, bitjs.archive.UnarchiveEvent.Type.EXTRACT);

        /**
        * @type {UnarchivedFile}
        */
        this.unarchivedFile = unarchivedFile;
    };
    bitjs.inherits(bitjs.archive.UnarchiveExtractEvent, bitjs.archive.UnarchiveEvent);


    /**
     * Base class for all Unarchivers.
     *
     * @param {ArrayBuffer} arrayBuffer The Array Buffer.
     * @param {string} optPathToBitJS Optional string for where the BitJS files are located.
     * @constructor
     */
    bitjs.archive.Unarchiver = function(arrayBuffer, optPathToBitJS) {
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
        this.pathToBitJS_ = optPathToBitJS || "";

        /**
        * A map from event type to an array of listeners.
        * @type {Map.<string, Array>}
        */
        this.listeners_ = {};
        for (var type in bitjs.archive.UnarchiveEvent.Type) {
            this.listeners_[bitjs.archive.UnarchiveEvent.Type[type]] = [];
        }
    };

    /**
     * Private web worker initialized during start().
     * @type {Worker}
     * @private
     */
    bitjs.archive.Unarchiver.prototype.worker_ = null;

    /**
     * This method must be overridden by the subclass to return the script filename.
     * @return {string} The script filename.
     * @protected.
     */
    bitjs.archive.Unarchiver.prototype.getScriptFileName = function() {
        throw "Subclasses of AbstractUnarchiver must overload getScriptFileName()";
    };

    /**
     * Adds an event listener for UnarchiveEvents.
     *
     * @param {string} Event type.
     * @param {function} An event handler function.
     */
    bitjs.archive.Unarchiver.prototype.addEventListener = function(type, listener) {
        if (type in this.listeners_) {
            if (this.listeners_[type].indexOf(listener) === -1) {
                this.listeners_[type].push(listener);
            }
        }
    };

    /**
     * Removes an event listener.
     *
     * @param {string} Event type.
     * @param {EventListener|function} An event listener or handler function.
     */
    bitjs.archive.Unarchiver.prototype.removeEventListener = function(type, listener) {
        if (type in this.listeners_) {
            var index = this.listeners_[type].indexOf(listener);
            if (index !== -1) {
                this.listeners_[type].splice(index, 1);
            }
        }
    };

    /**
     * Receive an event and pass it to the listener functions.
     *
     * @param {bitjs.archive.UnarchiveEvent} e
     * @private
     */
    bitjs.archive.Unarchiver.prototype.handleWorkerEvent_ = function(e) {
        if ((e instanceof bitjs.archive.UnarchiveEvent || e.type) &&
            this.listeners_[e.type] instanceof Array) {
            this.listeners_[e.type].forEach(function (listener) {
                listener(e);
            });
            if (e.type === bitjs.archive.UnarchiveEvent.Type.FINISH) {
                this.worker_.terminate();
            }
        } else {
            console.log(e);
        }
    };

    /**
     * Starts the unarchive in a separate Web Worker thread and returns immediately.
    */
    bitjs.archive.Unarchiver.prototype.start = function() {
        var me = this;
        var scriptFileName = this.pathToBitJS_ + this.getScriptFileName();
        if (scriptFileName) {
            this.worker_ = new Worker(scriptFileName);

            this.worker_.onerror = function(e) {
                console.log("Worker error: message = " + e.message);
                throw e;
            };

            this.worker_.onmessage = function(e) {
                if (typeof e.data === "string") {
                    // Just log any strings the workers pump our way.
                    console.log(e.data);
                } else {
                    // Assume that it is an UnarchiveEvent.  Some browsers preserve the 'type'
                    // so that instanceof UnarchiveEvent returns true, but others do not.
                    me.handleWorkerEvent_(e.data);
                }
            };

            this.worker_.postMessage({file: this.ab});
        }
    };

    /**
     * Terminates the Web Worker for this Unarchiver and returns immediately.
     */
    bitjs.archive.Unarchiver.prototype.stop = function() {
        if (this.worker_) {
            this.worker_.terminate();
        }
    };


    /**
     * Unzipper
     * @extends {bitjs.archive.Unarchiver}
     * @constructor
     */
    bitjs.archive.Unzipper = function(arrayBuffer, optPathToBitJS) {
        bitjs.base(this, arrayBuffer, optPathToBitJS);
    };
    bitjs.inherits(bitjs.archive.Unzipper, bitjs.archive.Unarchiver);
    bitjs.archive.Unzipper.prototype.getScriptFileName = function() {
        return "unzip.js";
    };

    /**
     * Unrarrer
     * @extends {bitjs.archive.Unarchiver}
     * @constructor
     */
    bitjs.archive.Unrarrer = function(arrayBuffer, optPathToBitJS) {
        bitjs.base(this, arrayBuffer, optPathToBitJS);
    };
    bitjs.inherits(bitjs.archive.Unrarrer, bitjs.archive.Unarchiver);
    bitjs.archive.Unrarrer.prototype.getScriptFileName = function() {
        return "unrar.js";
    };

    /**
     * Untarrer
     * @extends {bitjs.archive.Unarchiver}
     * @constructor
     */
    bitjs.archive.Untarrer = function(arrayBuffer, optPathToBitJS) {
        bitjs.base(this, arrayBuffer, optPathToBitJS);
    };
    bitjs.inherits(bitjs.archive.Untarrer, bitjs.archive.Unarchiver);
    bitjs.archive.Untarrer.prototype.getScriptFileName = function() {
        return "untar.js";
    };

})();
