/*
 * bytestream.js
 *
 * Provides a writer for bytes.
 *
 * Licensed under the MIT License
 *
 * Copyright(c) 2011 Google Inc.
 * Copyright(c) 2011 antimatter15
 */

/* global bitjs, Uint8Array */

var bitjs = bitjs || {};
bitjs.io = bitjs.io || {};

(function() {


    /**
     * A write-only Byte buffer which uses a Uint8 Typed Array as a backing store.
     * @param {number} numBytes The number of bytes to allocate.
     * @constructor
     */
    bitjs.io.ByteBuffer = function(numBytes) {
        if (typeof numBytes !== typeof 1 || numBytes <= 0) {
            throw "Error! ByteBuffer initialized with '" + numBytes + "'";
        }
        this.data = new Uint8Array(numBytes);
        this.ptr = 0;
    };


    /**
     * @param {number} b The byte to insert.
     */
    bitjs.io.ByteBuffer.prototype.insertByte = function(b) {
        // TODO: throw if byte is invalid?
        this.data[this.ptr++] = b;
    };


    /**
     * @param {Array.<number>|Uint8Array|Int8Array} bytes The bytes to insert.
     */
    bitjs.io.ByteBuffer.prototype.insertBytes = function(bytes) {
        // TODO: throw if bytes is invalid?
        this.data.set(bytes, this.ptr);
        this.ptr += bytes.length;
    };


    /**
     * Writes an unsigned number into the next n bytes.  If the number is too large
     * to fit into n bytes or is negative, an error is thrown.
     * @param {number} num The unsigned number to write.
     * @param {number} numBytes The number of bytes to write the number into.
     */
    bitjs.io.ByteBuffer.prototype.writeNumber = function(num, numBytes) {
        if (numBytes < 1) {
            throw "Trying to write into too few bytes: " + numBytes;
        }
        if (num < 0) {
            throw "Trying to write a negative number (" + num +
                ") as an unsigned number to an ArrayBuffer";
        }
        if (num > (Math.pow(2, numBytes * 8) - 1)) {
            throw "Trying to write " + num + " into only " + numBytes + " bytes";
        }

        // Roll 8-bits at a time into an array of bytes.
        var bytes = [];
        while (numBytes-- > 0) {
            var eightBits = num & 255;
            bytes.push(eightBits);
            num >>= 8;
        }

        this.insertBytes(bytes);
    };


    /**
     * Writes a signed number into the next n bytes.  If the number is too large
     * to fit into n bytes, an error is thrown.
     * @param {number} num The signed number to write.
     * @param {number} numBytes The number of bytes to write the number into.
     */
    bitjs.io.ByteBuffer.prototype.writeSignedNumber = function(num, numBytes) {
        if (numBytes < 1) {
            throw "Trying to write into too few bytes: " + numBytes;
        }

        var HALF = Math.pow(2, (numBytes * 8) - 1);
        if (num >= HALF || num < -HALF) {
            throw "Trying to write " + num + " into only " + numBytes + " bytes";
        }

        // Roll 8-bits at a time into an array of bytes.
        var bytes = [];
        while (numBytes-- > 0) {
            var eightBits = num & 255;
            bytes.push(eightBits);
            num >>= 8;
        }

        this.insertBytes(bytes);
    };


    /**
     * @param {string} str The ASCII string to write.
     */
    bitjs.io.ByteBuffer.prototype.writeASCIIString = function(str) {
        for (var i = 0; i < str.length; ++i) {
            var curByte = str.charCodeAt(i);
            if (curByte < 0 || curByte > 255) {
                throw "Trying to write a non-ASCII string!";
            }
            this.insertByte(curByte);
        }
    };

})();
