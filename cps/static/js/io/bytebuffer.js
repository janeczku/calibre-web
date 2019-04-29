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

var bitjs = bitjs || {};
bitjs.io = bitjs.io || {};


/**
 * A write-only Byte buffer which uses a Uint8 Typed Array as a backing store.
 */
bitjs.io.ByteBuffer = class {
  /**
   * @param {number} numBytes The number of bytes to allocate.
   */
  constructor(numBytes) {
    if (typeof numBytes != typeof 1 || numBytes <= 0) {
      throw "Error! ByteBuffer initialized with '" + numBytes + "'";
    }
    this.data = new Uint8Array(numBytes);
    this.ptr = 0;
  }


  /**
   * @param {number} b The byte to insert.
   */
  insertByte(b) {
    // TODO: throw if byte is invalid?
    this.data[this.ptr++] = b;
  }

  /**
   * @param {Array.<number>|Uint8Array|Int8Array} bytes The bytes to insert.
   */
  insertBytes(bytes) {
    // TODO: throw if bytes is invalid?
    this.data.set(bytes, this.ptr);
    this.ptr += bytes.length;
  }

  /**
   * Writes an unsigned number into the next n bytes.  If the number is too large
   * to fit into n bytes or is negative, an error is thrown.
   * @param {number} num The unsigned number to write.
   * @param {number} numBytes The number of bytes to write the number into.
   */
  writeNumber(num, numBytes) {
    if (numBytes < 1 || !numBytes) {
      throw 'Trying to write into too few bytes: ' + numBytes;
    }
    if (num < 0) {
      throw 'Trying to write a negative number (' + num +
          ') as an unsigned number to an ArrayBuffer';
    }
    if (num > (Math.pow(2, numBytes * 8) - 1)) {
      throw 'Trying to write ' + num + ' into only ' + numBytes + ' bytes';
    }

    // Roll 8-bits at a time into an array of bytes.
    const bytes = [];
    while (numBytes-- > 0) {
      const eightBits = num & 255;
      bytes.push(eightBits);
      num >>= 8;
    }

    this.insertBytes(bytes);
  }

  /**
   * Writes a signed number into the next n bytes.  If the number is too large
   * to fit into n bytes, an error is thrown.
   * @param {number} num The signed number to write.
   * @param {number} numBytes The number of bytes to write the number into.
   */
  writeSignedNumber(num, numBytes) {
    if (numBytes < 1) {
      throw 'Trying to write into too few bytes: ' + numBytes;
    }

    const HALF = Math.pow(2, (numBytes * 8) - 1);
    if (num >= HALF || num < -HALF) {
      throw 'Trying to write ' + num + ' into only ' + numBytes + ' bytes';
    }

    // Roll 8-bits at a time into an array of bytes.
    const bytes = [];
    while (numBytes-- > 0) {
      const eightBits = num & 255;
      bytes.push(eightBits);
      num >>= 8;
    }

    this.insertBytes(bytes);
  }

  /**
   * @param {string} str The ASCII string to write.
   */
  writeASCIIString(str) {
    for (let i = 0; i < str.length; ++i) {
      const curByte = str.charCodeAt(i);
      if (curByte < 0 || curByte > 255) {
        throw 'Trying to write a non-ASCII string!';
      }
      this.insertByte(curByte);
    }
  };
}
