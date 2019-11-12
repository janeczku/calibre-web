/*
 * bitstream.js
 *
 * Provides readers for bitstreams.
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
    bitjs.BIT = [0x01, 0x02, 0x04, 0x08,
        0x10, 0x20, 0x40, 0x80,
        0x100, 0x200, 0x400, 0x800,
        0x1000, 0x2000, 0x4000, 0x8000
    ];

    // mask for getting N number of bits (0-8)
    var BITMASK = [0, 0x01, 0x03, 0x07, 0x0F, 0x1F, 0x3F, 0x7F, 0xFF];


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

        var movePointers = movePointers || false,
            bytePtr = this.bytePtr,
            bitPtr = this.bitPtr,
            result = 0,
            bitsIn = 0,
            bytes = this.bytes;

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
        if (n <= 0 || typeof n !== typeof 1) {
            return 0;
        }

        var movePointers = movePointers || false,
            bytePtr = this.bytePtr,
            bitPtr = this.bitPtr,
            result = 0,
            bytes = this.bytes;

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
            } else {
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
     * Peek at 16 bits from current position in the buffer.
     * Bit at (bytePtr,bitPtr) has the highest position in returning data.
     * Taken from getbits.hpp in unrar.
     * TODO: Move this out of BitStream and into unrar.
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
        if (n <= 0 || typeof n !== typeof 1) {
            return 0;
        }

        // from http://tools.ietf.org/html/rfc1951#page-11
        // "Any bits of input up to the next byte boundary are ignored."
        while (this.bitPtr !== 0) {
            this.readBits(1);
        }

        var movePointers = movePointers || false;
        var bytePtr = this.bytePtr;
        // bitPtr = this.bitPtr;

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

})();
