/*
 * bytestream.js
 *
 * Provides readers for byte streams.
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
     * This object allows you to peek and consume bytes as numbers and strings
     * out of an ArrayBuffer.  In this buffer, everything must be byte-aligned.
     *
     * @param {ArrayBuffer} ab The ArrayBuffer object.
     * @param {number=} optOffset The offset into the ArrayBuffer
     * @param {number=} optLength The length of this BitStream
     * @constructor
     */
    bitjs.io.ByteStream = function(ab, optOffset, optLength) {
        var offset = optOffset || 0;
        var length = optLength || ab.byteLength;
        this.bytes = new Uint8Array(ab, offset, length);
        this.ptr = 0;
    };


    /**
     * Peeks at the next n bytes as an unsigned number but does not advance the
     * pointer
     * TODO: This apparently cannot read more than 4 bytes as a number?
     * @param {number} n The number of bytes to peek at.
     * @return {number} The n bytes interpreted as an unsigned number.
     */
    bitjs.io.ByteStream.prototype.peekNumber = function(n) {
        // TODO: return error if n would go past the end of the stream?
        if (n <= 0 || typeof n !== typeof 1) {
            return -1;
        }

        var result = 0;
        // read from last byte to first byte and roll them in
        var curByte = this.ptr + n - 1;
        while (curByte >= this.ptr) {
            result <<= 8;
            result |= this.bytes[curByte];
            --curByte;
        }
        return result;
    };


    /**
     * Returns the next n bytes as an unsigned number (or -1 on error)
     * and advances the stream pointer n bytes.
     * @param {number} n The number of bytes to read.
     * @return {number} The n bytes interpreted as an unsigned number.
     */
    bitjs.io.ByteStream.prototype.readNumber = function(n) {
        var num = this.peekNumber(n);
        this.ptr += n;
        return num;
    };


    /**
     * Returns the next n bytes as a signed number but does not advance the
     * pointer.
     * @param {number} n The number of bytes to read.
     * @return {number} The bytes interpreted as a signed number.
     */
    bitjs.io.ByteStream.prototype.peekSignedNumber = function(n) {
        var num = this.peekNumber(n);
        var HALF = Math.pow(2, (n * 8) - 1);
        var FULL = HALF * 2;

        if (num >= HALF) num -= FULL;

        return num;
    };


    /**
     * Returns the next n bytes as a signed number and advances the stream pointer.
     * @param {number} n The number of bytes to read.
     * @return {number} The bytes interpreted as a signed number.
     */
    bitjs.io.ByteStream.prototype.readSignedNumber = function(n) {
        var num = this.peekSignedNumber(n);
        this.ptr += n;
        return num;
    };


    /**
     * ToDo: Returns the next n bytes as a signed number and advances the stream pointer.
     * @param {number} n The number of bytes to read.
     * @return {number} The bytes interpreted as a signed number.
     */
    bitjs.io.ByteStream.prototype.movePointer = function(n) {
        this.ptr += n;
        // end of buffer reached
        if ((this.bytes.byteLength - this.ptr) < 0 ) {
            this.ptr =  this.bytes.byteLength;
        }
    }

    /**
     * ToDo: Returns the next n bytes as a signed number and advances the stream pointer.
     * @param {number} n The number of bytes to read.
     * @return {number} The bytes interpreted as a signed number.
     */
    bitjs.io.ByteStream.prototype.moveTo = function(n) {
        if ( n < 0 ) {
            n = 0;
        }
        this.ptr = n;
        // end of buffer reached
        if ((this.bytes.byteLength - this.ptr) < 0 ) {
            this.ptr =  this.bytes.byteLength;
        }
    }

    /**
     * This returns n bytes as a sub-array, advancing the pointer if movePointers
     * is true.
     * @param {number} n The number of bytes to read.
     * @param {boolean} movePointers Whether to move the pointers.
     * @return {Uint8Array} The subarray.
     */
    bitjs.io.ByteStream.prototype.peekBytes = function(n, movePointers) {
        if (n <= 0 || typeof n !== typeof 1) {
            return null;
        }

        var result = this.bytes.subarray(this.ptr, this.ptr + n);

        if (movePointers) {
            this.ptr += n;
        }

        return result;
    };


    /**
     * Reads the next n bytes as a sub-array.
     * @param {number} n The number of bytes to read.
     * @return {Uint8Array} The subarray.
     */
    bitjs.io.ByteStream.prototype.readBytes = function(n) {
        return this.peekBytes(n, true);
    };


    /**
     * Peeks at the next n bytes as a string but does not advance the pointer.
     * @param {number} n The number of bytes to peek at.
     * @return {string} The next n bytes as a string.
     */
    bitjs.io.ByteStream.prototype.peekString = function(n) {
        if (n <= 0 || typeof n !== typeof 1) {
            return "";
        }

        var result = "";
        for (var p = this.ptr, end = this.ptr + n; p < end; ++p) {
            result += String.fromCharCode(this.bytes[p]);
        }
        return result;
    };


    /**
     * Returns the next n bytes as an ASCII string and advances the stream pointer
     * n bytes.
     * @param {number} n The number of bytes to read.
     * @return {string} The next n bytes as a string.
     */
    bitjs.io.ByteStream.prototype.readString = function(n) {
        var strToReturn = this.peekString(n);
        this.ptr += n;
        return strToReturn;
    };

})();
