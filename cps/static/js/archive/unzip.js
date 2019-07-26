/**
 * unzip.js
 *
 * Licensed under the MIT License
 *
 * Copyright(c) 2011 Google Inc.
 * Copyright(c) 2011 antimatter15
 *
 * Reference Documentation:
 *
 * ZIP format: http://www.pkware.com/documents/casestudies/APPNOTE.TXT
 * DEFLATE format: http://tools.ietf.org/html/rfc1951
 */
/* global bitjs, importScripts, Uint8Array*/

// This file expects to be invoked as a Worker (see onmessage below).
importScripts("../io/bitstream.js");
importScripts("../io/bytebuffer.js");
importScripts("../io/bytestream.js");
importScripts("archive.js");

// Progress variables.
var currentFilename = "";
var currentFileNumber = 0;
var currentBytesUnarchivedInFile = 0;
var currentBytesUnarchived = 0;
var totalUncompressedBytesInArchive = 0;
var totalFilesInArchive = 0;

// Helper functions.
var info = function(str) {
    postMessage(new bitjs.archive.UnarchiveInfoEvent(str));
};
var err = function(str) {
    postMessage(new bitjs.archive.UnarchiveErrorEvent(str));
};
var postProgress = function() {
    postMessage(new bitjs.archive.UnarchiveProgressEvent(
        currentFilename,
        currentFileNumber,
        currentBytesUnarchivedInFile,
        currentBytesUnarchived,
        totalUncompressedBytesInArchive,
        totalFilesInArchive));
};

var zLocalFileHeaderSignature = 0x04034b50;
var zArchiveExtraDataSignature = 0x08064b50;
var zCentralFileHeaderSignature = 0x02014b50;
var zDigitalSignatureSignature = 0x05054b50;

// takes a ByteStream and parses out the local file information
var ZipLocalFile = function(bstream) {
    if (typeof bstream !== typeof {} || !bstream.readNumber || typeof bstream.readNumber !== typeof function() {}) {
        return null;
    }

    bstream.readNumber(4); // swallow signature
    this.version = bstream.readNumber(2);
    this.generalPurpose = bstream.readNumber(2);
    this.compressionMethod = bstream.readNumber(2);
    this.lastModFileTime = bstream.readNumber(2);
    this.lastModFileDate = bstream.readNumber(2);
    this.crc32 = bstream.readNumber(4);
    this.compressedSize = bstream.readNumber(4);
    this.uncompressedSize = bstream.readNumber(4);
    this.fileNameLength = bstream.readNumber(2);
    this.extraFieldLength = bstream.readNumber(2);

    this.filename = null;
    if (this.fileNameLength > 0) {
        this.filename = bstream.readString(this.fileNameLength);
    }

    this.extraField = null;
    if (this.extraFieldLength > 0) {
        this.extraField = bstream.readString(this.extraFieldLength);
        info(" extra field=" + this.extraField);
    }

    // read in the compressed data
    this.fileData = null;
    if (this.compressedSize > 0) {
        this.fileData = new Uint8Array(bstream.bytes.buffer, bstream.ptr, this.compressedSize);
        bstream.ptr += this.compressedSize;
    }

    // TODO: deal with data descriptor if present (we currently assume no data descriptor!)
    // "This descriptor exists only if bit 3 of the general purpose bit flag is set"
    // But how do you figure out how big the file data is if you don't know the compressedSize
    // from the header?!?
    if ((this.generalPurpose & bitjs.BIT[3]) !== 0) {
        this.crc32 = bstream.readNumber(4);
        this.compressedSize = bstream.readNumber(4);
        this.uncompressedSize = bstream.readNumber(4);
    }

    // Now that we have all the bytes for this file, we can print out some information.
    info("Zip Local File Header:");
    info(" version=" + this.version);
    info(" general purpose=" + this.generalPurpose);
    info(" compression method=" + this.compressionMethod);
    info(" last mod file time=" + this.lastModFileTime);
    info(" last mod file date=" + this.lastModFileDate);
    info(" crc32=" + this.crc32);
    info(" compressed size=" + this.compressedSize);
    info(" uncompressed size=" + this.uncompressedSize);
    info(" file name length=" + this.fileNameLength);
    info(" extra field length=" + this.extraFieldLength);
    info(" filename = '" + this.filename + "'");

};

// determine what kind of compressed data we have and decompress
ZipLocalFile.prototype.unzip = function() {

    // Zip Version 1.0, no compression (store only)
    if (this.compressionMethod === 0 ) {
        info("ZIP v" + this.version + ", store only: " + this.filename + " (" + this.compressedSize + " bytes)");
        currentBytesUnarchivedInFile = this.compressedSize;
        currentBytesUnarchived += this.compressedSize;
        this.fileData = zeroCompression(this.fileData, this.uncompressedSize);
    } else if (this.compressionMethod === 8) {
        // version == 20, compression method == 8 (DEFLATE)
        info("ZIP v2.0, DEFLATE: " + this.filename + " (" + this.compressedSize + " bytes)");
        this.fileData = inflate(this.fileData, this.uncompressedSize);
    } else {
        err("UNSUPPORTED VERSION/FORMAT: ZIP v" + this.version + ", compression method=" + this.compressionMethod + ": " + this.filename + " (" + this.compressedSize + " bytes)");
        this.fileData = null;
    }
};


// Takes an ArrayBuffer of a zip file in
// returns null on error
// returns an array of DecompressedFile objects on success
// ToDo This function differs
var unzip = function(arrayBuffer) {
    postMessage(new bitjs.archive.UnarchiveStartEvent());

    currentFilename = "";
    currentFileNumber = 0;
    currentBytesUnarchivedInFile = 0;
    currentBytesUnarchived = 0;
    totalUncompressedBytesInArchive = 0;
    totalFilesInArchive = 0;
    currentBytesUnarchived = 0;

    var bstream = new bitjs.io.ByteStream(arrayBuffer);
    // detect local file header signature or return null
    if (bstream.peekNumber(4) === zLocalFileHeaderSignature) {
        var localFiles = [];
        // loop until we don't see any more local files
        while (bstream.peekNumber(4) === zLocalFileHeaderSignature) {
            var oneLocalFile = new ZipLocalFile(bstream);
            // this should strip out directories/folders
            if (oneLocalFile && oneLocalFile.uncompressedSize > 0 && oneLocalFile.fileData) {
                localFiles.push(oneLocalFile);
                totalUncompressedBytesInArchive += oneLocalFile.uncompressedSize;
            }
        }
        totalFilesInArchive = localFiles.length;

        // got all local files, now sort them
        localFiles.sort(alphanumCase);

        // archive extra data record
        if (bstream.peekNumber(4) === zArchiveExtraDataSignature) {
            info(" Found an Archive Extra Data Signature");

            // skipping this record for now
            bstream.readNumber(4);
            var archiveExtraFieldLength = bstream.readNumber(4);
            bstream.readString(archiveExtraFieldLength);
        }

        // central directory structure
        // TODO: handle the rest of the structures (Zip64 stuff)
        if (bstream.peekNumber(4) === zCentralFileHeaderSignature) {
            info(" Found a Central File Header");

            // read all file headers
            while (bstream.peekNumber(4) === zCentralFileHeaderSignature) {
                bstream.readNumber(4); // signature
                bstream.readNumber(2); // version made by
                bstream.readNumber(2); // version needed to extract
                bstream.readNumber(2); // general purpose bit flag
                bstream.readNumber(2); // compression method
                bstream.readNumber(2); // last mod file time
                bstream.readNumber(2); // last mod file date
                bstream.readNumber(4); // crc32
                bstream.readNumber(4); // compressed size
                bstream.readNumber(4); // uncompressed size
                var fileNameLength = bstream.readNumber(2); // file name length
                var extraFieldLength = bstream.readNumber(2); // extra field length
                var fileCommentLength = bstream.readNumber(2); // file comment length
                bstream.readNumber(2); // disk number start
                bstream.readNumber(2); // internal file attributes
                bstream.readNumber(4); // external file attributes
                bstream.readNumber(4); // relative offset of local header

                bstream.readString(fileNameLength); // file name
                bstream.readString(extraFieldLength); // extra field
                bstream.readString(fileCommentLength); // file comment
            }
        }

        // digital signature
        if (bstream.peekNumber(4) === zDigitalSignatureSignature) {
            info(" Found a Digital Signature");

            bstream.readNumber(4);
            var sizeOfSignature = bstream.readNumber(2);
            bstream.readString(sizeOfSignature); // digital signature data
        }

        // report # files and total length
        if (localFiles.length > 0) {
            postProgress();
        }

        // now do the unzipping of each file
        for (var i = 0; i < localFiles.length; ++i) {
            var localfile = localFiles[i];

            // update progress
            currentFilename = localfile.filename;
            currentFileNumber = i;
            currentBytesUnarchivedInFile = 0;

            // actually do the unzipping
            localfile.unzip();

            if (localfile.fileData !== null) {
                postMessage(new bitjs.archive.UnarchiveExtractEvent(localfile));
                postProgress();
            }
        }
        postProgress();
        postMessage(new bitjs.archive.UnarchiveFinishEvent());
    }
};

// returns a table of Huffman codes
// each entry's index is its code and its value is a JavaScript object
// containing {length: 6, symbol: X}
function getHuffmanCodes(bitLengths) {
    // ensure bitLengths is an array containing at least one element
    if (typeof bitLengths !== typeof [] || bitLengths.length < 1) {
        err("Error! getHuffmanCodes() called with an invalid array");
        return null;
    }

    // Reference: http://tools.ietf.org/html/rfc1951#page-8
    var numLengths = bitLengths.length;
    var blCount = [];
    var MAX_BITS = 1;

    // Step 1: count up how many codes of each length we have
    for (var i = 0; i < numLengths; ++i) {
        var length = bitLengths[i];
        // test to ensure each bit length is a positive, non-zero number
        if (typeof length !== typeof 1 || length < 0) {
            err("bitLengths contained an invalid number in getHuffmanCodes(): " + length + " of type " + (typeof length));
            return null;
        }
        // increment the appropriate bitlength count
        if (typeof blCount[length] === "undefined") blCount[length] = 0;
        // a length of zero means this symbol is not participating in the huffman coding
        if (length > 0) blCount[length]++;

        if (length > MAX_BITS) MAX_BITS = length;
    }

    // Step 2: Find the numerical value of the smallest code for each code length
    var nextCode = [];
    var code = 0;
    for (var bits = 1; bits <= MAX_BITS; ++bits) {
        var length2 = bits - 1;
        // ensure undefined lengths are zero
        if (typeof blCount[length2] === "undefined") blCount[length2] = 0;
        code = (code + blCount[bits - 1]) << 1;
        nextCode [bits] = code;
    }

    // Step 3: Assign numerical values to all codes
    var table = {};
    var tableLength = 0;
    for (var n = 0; n < numLengths; ++n) {
        var len = bitLengths[n];
        if (len !== 0) {
            table[nextCode [len]] = { length: len, symbol: n }; //, bitstring: binaryValueToString(nextCode [len],len) };
            tableLength++;
            nextCode [len]++;
        }
    }
    table.maxLength = tableLength;

    return table;
}

/*
     The Huffman codes for the two alphabets are fixed, and are not
     represented explicitly in the data.  The Huffman code lengths
     for the literal/length alphabet are:

               Lit Value    Bits        Codes
               ---------    ----        -----
                 0 - 143     8          00110000 through
                                        10111111
               144 - 255     9          110010000 through
                                        111111111
               256 - 279     7          0000000 through
                                        0010111
               280 - 287     8          11000000 through
                                        11000111
*/
// fixed Huffman codes go from 7-9 bits, so we need an array whose index can hold up to 9 bits
var fixedHCtoLiteral = null;
var fixedHCtoDistance = null;

function getFixedLiteralTable() {
    // create once
    if (!fixedHCtoLiteral) {
        var bitlengths = new Array(288);
        var i;
        for (i = 0; i <= 143; ++i) bitlengths[i] = 8;
        for (i = 144; i <= 255; ++i) bitlengths[i] = 9;
        for (i = 256; i <= 279; ++i) bitlengths[i] = 7;
        for (i = 280; i <= 287; ++i) bitlengths[i] = 8;

        // get huffman code table
        fixedHCtoLiteral = getHuffmanCodes(bitlengths);
    }
    return fixedHCtoLiteral;
}

function getFixedDistanceTable() {
    // create once
    if (!fixedHCtoDistance) {
        var bitlengths = new Array(32);
        for (var i = 0; i < 32; ++i) {
            bitlengths[i] = 5;
        }

        // get huffman code table
        fixedHCtoDistance = getHuffmanCodes(bitlengths);
    }
    return fixedHCtoDistance;
}

// extract one bit at a time until we find a matching Huffman Code
// then return that symbol
function decodeSymbol(bstream, hcTable) {
    var code = 0;
    var len = 0;

    // loop until we match
    for (;;) {
        // read in next bit
        var bit = bstream.readBits(1);
        code = (code << 1) | bit;
        ++len;

        // check against Huffman Code table and break if found
        if (hcTable.hasOwnProperty(code) && hcTable[code].length === len) {
            break;
        }
        if (len > hcTable.maxLength) {
            err("Bit stream out of sync, didn't find a Huffman Code, length was " + len +
                " and table only max code length of " + hcTable.maxLength);
            break;
        }
    }
    return hcTable[code].symbol;
}


var CodeLengthCodeOrder = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15];
/*
     Extra               Extra               Extra
Code Bits Length(s) Code Bits Lengths   Code Bits Length(s)
---- ---- ------     ---- ---- -------   ---- ---- -------
 257   0     3       267   1   15,16     277   4   67-82
 258   0     4       268   1   17,18     278   4   83-98
 259   0     5       269   2   19-22     279   4   99-114
 260   0     6       270   2   23-26     280   4  115-130
 261   0     7       271   2   27-30     281   5  131-162
 262   0     8       272   2   31-34     282   5  163-194
 263   0     9       273   3   35-42     283   5  195-226
 264   0    10       274   3   43-50     284   5  227-257
 265   1  11,12      275   3   51-58     285   0    258
 266   1  13,14      276   3   59-66
*/
var LengthLookupTable = [
    [0, 3],
    [0, 4],
    [0, 5],
    [0, 6],
    [0, 7],
    [0, 8],
    [0, 9],
    [0, 10],
    [1, 11],
    [1, 13],
    [1, 15],
    [1, 17],
    [2, 19],
    [2, 23],
    [2, 27],
    [2, 31],
    [3, 35],
    [3, 43],
    [3, 51],
    [3, 59],
    [4, 67],
    [4, 83],
    [4, 99],
    [4, 115],
    [5, 131],
    [5, 163],
    [5, 195],
    [5, 227],
    [0, 258]
];
/*
      Extra           Extra                Extra
 Code Bits Dist  Code Bits   Dist     Code Bits Distance
 ---- ---- ----  ---- ----  ------    ---- ---- --------
   0   0    1     10   4     33-48    20    9   1025-1536
   1   0    2     11   4     49-64    21    9   1537-2048
   2   0    3     12   5     65-96    22   10   2049-3072
   3   0    4     13   5     97-128   23   10   3073-4096
   4   1   5,6    14   6    129-192   24   11   4097-6144
   5   1   7,8    15   6    193-256   25   11   6145-8192
   6   2   9-12   16   7    257-384   26   12  8193-12288
   7   2  13-16   17   7    385-512   27   12 12289-16384
   8   3  17-24   18   8    513-768   28   13 16385-24576
   9   3  25-32   19   8   769-1024   29   13 24577-32768
*/
var DistLookupTable = [
    [0, 1],
    [0, 2],
    [0, 3],
    [0, 4],
    [1, 5],
    [1, 7],
    [2, 9],
    [2, 13],
    [3, 17],
    [3, 25],
    [4, 33],
    [4, 49],
    [5, 65],
    [5, 97],
    [6, 129],
    [6, 193],
    [7, 257],
    [7, 385],
    [8, 513],
    [8, 769],
    [9, 1025],
    [9, 1537],
    [10, 2049],
    [10, 3073],
    [11, 4097],
    [11, 6145],
    [12, 8193],
    [12, 12289],
    [13, 16385],
    [13, 24577]
];

function inflateBlockData(bstream, hcLiteralTable, hcDistanceTable, buffer) {
    /*
          loop (until end of block code recognized)
             decode literal/length value from input stream
             if value < 256
                copy value (literal byte) to output stream
             otherwise
                if value = end of block (256)
                   break from loop
                otherwise (value = 257..285)
                   decode distance from input stream

                   move backwards distance bytes in the output
                   stream, and copy length bytes from this
                   position to the output stream.
    */
    var blockSize = 0;
    for (;;) {
        var symbol = decodeSymbol(bstream, hcLiteralTable);
        if (symbol < 256) {
            // copy literal byte to output
            buffer.insertByte(symbol);
            blockSize++;
        } else {
            // end of block reached
            if (symbol === 256) {
                break;
            } else {
                var lengthLookup = LengthLookupTable[symbol - 257];
                var length = lengthLookup[1] + bstream.readBits(lengthLookup[0]);
                var distLookup = DistLookupTable[decodeSymbol(bstream, hcDistanceTable)];
                var distance = distLookup[1] + bstream.readBits(distLookup[0]);

                // now apply length and distance appropriately and copy to output

                // TODO: check that backward distance < data.length?

                // http://tools.ietf.org/html/rfc1951#page-11
                // "Note also that the referenced string may overlap the current
                //  position; for example, if the last 2 bytes decoded have values
                //  X and Y, a string reference with <length = 5, distance = 2>
                //  adds X,Y,X,Y,X to the output stream."
                //
                // loop for each character
                var ch = buffer.ptr - distance;
                blockSize += length;
                if (length > distance) {
                    var data = buffer.data;
                    while (length--) {
                        buffer.insertByte(data[ch++]);
                    }
                } else {
                    buffer.insertBytes(buffer.data.subarray(ch, ch + length));
                }
            } // length-distance pair
        } // length-distance pair or end-of-block
    } // loop until we reach end of block
    return blockSize;
}

function zeroCompression(compressedData, numDecompressedBytes) {
    var bstream = new bitjs.io.BitStream(compressedData.buffer,
        false /* rtl */,
        compressedData.byteOffset,
        compressedData.byteLength);
    var buffer = new bitjs.io.ByteBuffer(numDecompressedBytes);
    buffer.insertBytes(bstream.readBytes(numDecompressedBytes));
    return buffer.data;
}

// {Uint8Array} compressedData A Uint8Array of the compressed file data.
// compression method 8
// deflate: http://tools.ietf.org/html/rfc1951
function inflate(compressedData, numDecompressedBytes) {
    // Bit stream representing the compressed data.
    var bstream = new bitjs.io.BitStream(compressedData.buffer,
        false /* rtl */,
        compressedData.byteOffset,
        compressedData.byteLength);
    var buffer = new bitjs.io.ByteBuffer(numDecompressedBytes);
    var blockSize = 0;

    // block format: http://tools.ietf.org/html/rfc1951#page-9
    var bFinal = 0;
    do {
        bFinal = bstream.readBits(1);
        var bType = bstream.readBits(2);
        blockSize = 0;
        // ++numBlocks;
        // no compression
        if (bType === 0) {
            // skip remaining bits in this byte
            while (bstream.bitPtr !== 0) bstream.readBits(1);
            var len = bstream.readBits(16);
            bstream.readBits(16);
            // TODO: check if nlen is the ones-complement of len?

            if (len > 0) buffer.insertBytes(bstream.readBytes(len));
            blockSize = len;
        } else if (bType === 1) {
            // fixed Huffman codes
            blockSize = inflateBlockData(bstream, getFixedLiteralTable(), getFixedDistanceTable(), buffer);
        } else if (bType === 2) {
            // dynamic Huffman codes
            var numLiteralLengthCodes = bstream.readBits(5) + 257;
            var numDistanceCodes = bstream.readBits(5) + 1,
                numCodeLengthCodes = bstream.readBits(4) + 4;

            // populate the array of code length codes (first de-compaction)
            var codeLengthsCodeLengths = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
            for (var i = 0; i < numCodeLengthCodes; ++i) {
                codeLengthsCodeLengths[ CodeLengthCodeOrder[i] ] = bstream.readBits(3);
            }

            // get the Huffman Codes for the code lengths
            var codeLengthsCodes = getHuffmanCodes(codeLengthsCodeLengths);

            // now follow this mapping
            /*
               0 - 15: Represent code lengths of 0 - 15
                   16: Copy the previous code length 3 - 6 times.
                       The next 2 bits indicate repeat length
                             (0 = 3, ... , 3 = 6)
                          Example:  Codes 8, 16 (+2 bits 11),
                                    16 (+2 bits 10) will expand to
                                    12 code lengths of 8 (1 + 6 + 5)
                   17: Repeat a code length of 0 for 3 - 10 times.
                       (3 bits of length)
                   18: Repeat a code length of 0 for 11 - 138 times
                       (7 bits of length)
            */
            // to generate the true code lengths of the Huffman Codes for the literal
            // and distance tables together
            var literalCodeLengths = [];
            var prevCodeLength = 0;
            while (literalCodeLengths.length < numLiteralLengthCodes + numDistanceCodes) {
                var symbol = decodeSymbol(bstream, codeLengthsCodes);
                if (symbol <= 15) {
                    literalCodeLengths.push(symbol);
                    prevCodeLength = symbol;
                } else if (symbol === 16) {
                    var repeat = bstream.readBits(2) + 3;
                    while (repeat--) {
                        literalCodeLengths.push(prevCodeLength);
                    }
                } else if (symbol === 17) {
                    var repeat1 = bstream.readBits(3) + 3;
                    while (repeat1--) {
                        literalCodeLengths.push(0);
                    }
                } else if (symbol === 18) {
                    var repeat2 = bstream.readBits(7) + 11;
                    while (repeat2--) {
                        literalCodeLengths.push(0);
                    }
                }
            }

            // now split the distance code lengths out of the literal code array
            var distanceCodeLengths = literalCodeLengths.splice(numLiteralLengthCodes, numDistanceCodes);

            // now generate the true Huffman Code tables using these code lengths
            var hcLiteralTable = getHuffmanCodes(literalCodeLengths);
            var hcDistanceTable = getHuffmanCodes(distanceCodeLengths);
            blockSize = inflateBlockData(bstream, hcLiteralTable, hcDistanceTable, buffer);
        } else {
            // error
            err("Error! Encountered deflate block of type 3");
            return null;
        }

        // update progress
        currentBytesUnarchivedInFile += blockSize;
        currentBytesUnarchived += blockSize;
        postProgress();

    } while (bFinal !== 1);
    // we are done reading blocks if the bFinal bit was set for this block

    // return the buffer data bytes
    return buffer.data;
}

// event.data.file has the ArrayBuffer.
onmessage = function(event) {
    unzip(event.data.file, true);
};
