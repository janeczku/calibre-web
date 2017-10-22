/*
 * io.js
 *
 * Provides readers for bit/byte streams (reading) and a byte buffer (writing).
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

    // mask for getting the Nth bit (zero-based)
    bitjs.BIT = [	0x01, 0x02, 0x04, 0x08,
        0x10, 0x20, 0x40, 0x80,
        0x100, 0x200, 0x400, 0x800,
        0x1000, 0x2000, 0x4000, 0x8000];

    // mask for getting N number of bits (0-8)
    var BITMASK = [0, 0x01, 0x03, 0x07, 0x0F, 0x1F, 0x3F, 0x7F, 0xFF ];


    /**
     * This bit stream peeks and consumes bits out of a binary stream.
     *
     * @param {ArrayBuffer} ab An ArrayBuffer object or a Uint8Array.
     * @param {boolean} rtl Whether the stream reads bits from the byte starting
     *     from bit 7 to 0 (true) or bit 0 to 7 (false).
     * @param {Number} optOffset The offset into the ArrayBuffer
     * @param {Number} optLength The length of this BitStream
     */
    bitjs.io.BitStream = function(ab, rtl, optOffset, optLength) {
        if (!ab || !ab.toString || ab.toString() !== "[object ArrayBuffer]") {
            throw "Error! BitArray constructed with an invalid ArrayBuffer object";
        }

        var offset = optOffset || 0;
        var length = optLength || ab.byteLength;
        this.bytes = new Uint8Array(ab, offset, length);
        this.bytePtr = 0; // tracks which byte we are on
        this.bitPtr = 0; // tracks which bit we are on (can have values 0 through 7)
        this.peekBits = rtl ? this.peekBitsRtl : this.peekBitsLtr;
    };


    /**
     *   byte0      byte1      byte2      byte3
     * 7......0 | 7......0 | 7......0 | 7......0
     *
     * The bit pointer starts at bit0 of byte0 and moves left until it reaches
     * bit7 of byte0, then jumps to bit0 of byte1, etc.
     * @param {number} n The number of bits to peek.
     * @param {boolean=} movePointers Whether to move the pointer, defaults false.
     * @return {number} The peeked bits, as an unsigned number.
     */
    bitjs.io.BitStream.prototype.peekBitsLtr = function(n, movePointers) {
        if (n <= 0 || typeof n !== typeof 1) {
            return 0;
        }

        var movePointers = movePointers || false;
        var bytePtr = this.bytePtr;
        var bitPtr = this.bitPtr;
        var result = 0;
        var bitsIn = 0;
        var bytes = this.bytes;

        // keep going until we have no more bits left to peek at
        // TODO: Consider putting all bits from bytes we will need into a variable and then
        //       shifting/masking it to just extract the bits we want.
        //       This could be considerably faster when reading more than 3 or 4 bits at a time.
        while (n > 0) {
            if (bytePtr >= bytes.length) {
                throw "Error!  Overflowed the bit stream! n=" + n + ", bytePtr=" + bytePtr + ", bytes.length=" +
                    bytes.length + ", bitPtr=" + bitPtr;
            }

            var numBitsLeftInThisByte = (8 - bitPtr);
            var mask;
            if (n >= numBitsLeftInThisByte) {
                mask = (BITMASK[numBitsLeftInThisByte] << bitPtr);
                result |= (((bytes[bytePtr] & mask) >> bitPtr) << bitsIn);

                bytePtr++;
                bitPtr = 0;
                bitsIn += numBitsLeftInThisByte;
                n -= numBitsLeftInThisByte;
            } else {
                mask = (BITMASK[n] << bitPtr);
                result |= (((bytes[bytePtr] & mask) >> bitPtr) << bitsIn);

                bitPtr += n;
                bitsIn += n;
                n = 0;
            }
        }

        if (movePointers) {
            this.bitPtr = bitPtr;
            this.bytePtr = bytePtr;
        }

        return result;
    };


    /**
     *   byte0      byte1      byte2      byte3
     * 7......0 | 7......0 | 7......0 | 7......0
     *
     * The bit pointer starts at bit7 of byte0 and moves right until it reaches
     * bit0 of byte0, then goes to bit7 of byte1, etc.
     * @param {number} n The number of bits to peek.
     * @param {boolean=} movePointers Whether to move the pointer, defaults false.
     * @return {number} The peeked bits, as an unsigned number.
     */
    bitjs.io.BitStream.prototype.peekBitsRtl = function(n, movePointers) {
        if (n <= 0 || typeof n != typeof 1) {
            return 0;
        }

        var movePointers = movePointers || false;
        var bytePtr = this.bytePtr;
        var bitPtr = this.bitPtr;
        var result = 0;
        var bytes = this.bytes;

        // keep going until we have no more bits left to peek at
        // TODO: Consider putting all bits from bytes we will need into a variable and then
        //       shifting/masking it to just extract the bits we want.
        //       This could be considerably faster when reading more than 3 or 4 bits at a time.
        while (n > 0) {

            if (bytePtr >= bytes.length) {
                throw "Error!  Overflowed the bit stream! n=" + n + ", bytePtr=" + bytePtr + ", bytes.length=" +
                    bytes.length + ", bitPtr=" + bitPtr;
                // return -1;
            }

            var numBitsLeftInThisByte = (8 - bitPtr);
            if (n >= numBitsLeftInThisByte) {
                result <<= numBitsLeftInThisByte;
                result |= (BITMASK[numBitsLeftInThisByte] & bytes[bytePtr]);
                bytePtr++;
                bitPtr = 0;
                n -= numBitsLeftInThisByte;
            }
            else {
                result <<= n;
                result |= ((bytes[bytePtr] & (BITMASK[n] << (8 - n - bitPtr))) >> (8 - n - bitPtr));

                bitPtr += n;
                n = 0;
            }
        }

        if (movePointers) {
            this.bitPtr = bitPtr;
            this.bytePtr = bytePtr;
        }

        return result;
    };


    /**
     * Some voodoo magic.
     */
    bitjs.io.BitStream.prototype.getBits = function() {
        return (((((this.bytes[this.bytePtr] & 0xff) << 16) +
            ((this.bytes[this.bytePtr + 1] & 0xff) << 8) +
            ((this.bytes[this.bytePtr + 2] & 0xff))) >>> (8 - this.bitPtr)) & 0xffff);
    };


    /**
     * Reads n bits out of the stream, consuming them (moving the bit pointer).
     * @param {number} n The number of bits to read.
     * @return {number} The read bits, as an unsigned number.
     */
    bitjs.io.BitStream.prototype.readBits = function(n) {
        return this.peekBits(n, true);
    };


    /**
     * This returns n bytes as a sub-array, advancing the pointer if movePointers
     * is true.  Only use this for uncompressed blocks as this throws away remaining
     * bits in the current byte.
     * @param {number} n The number of bytes to peek.
     * @param {boolean=} movePointers Whether to move the pointer, defaults false.
     * @return {Uint8Array} The subarray.
     */
    bitjs.io.BitStream.prototype.peekBytes = function(n, movePointers) {
        if (n <= 0 || typeof n != typeof 1) {
            return 0;
        }

        // from http://tools.ietf.org/html/rfc1951#page-11
        // "Any bits of input up to the next byte boundary are ignored."
        while (this.bitPtr !== 0) {
            this.readBits(1);
        }

        movePointers = movePointers || false;
        var bytePtr = this.bytePtr;
        // var bitPtr = this.bitPtr;

        var result = this.bytes.subarray(bytePtr, bytePtr + n);

        if (movePointers) {
            this.bytePtr += n;
        }

        return result;
    };


    /**
     * @param {number} n The number of bytes to read.
     * @return {Uint8Array} The subarray.
     */
    bitjs.io.BitStream.prototype.readBytes = function(n) {
        return this.peekBytes(n, true);
    };


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
        var num = this.peekNumber( n );
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
     * This returns n bytes as a sub-array, advancing the pointer if movePointers
     * is true.
     * @param {number} n The number of bytes to read.
     * @param {boolean} movePointers Whether to move the pointers.
     * @return {Uint8Array} The subarray.
     */
    bitjs.io.ByteStream.prototype.peekBytes = function(n, movePointers) {
        if (n <= 0 || typeof n != typeof 1) {
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
        if (n <= 0 || typeof n != typeof 1) {
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
