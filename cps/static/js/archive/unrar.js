/**
 * unrar.js
 *
 * Licensed under the MIT License
 *
 * Copyright(c) 2011 Google Inc.
 * Copyright(c) 2011 antimatter15
 *
 * Reference Documentation:
 *
 * http://kthoom.googlecode.com/hg/docs/unrar.html
 */
/* global bitjs, importScripts, RarVM, Uint8Array, UnpackFilter */
/* global VM_FIXEDGLOBALSIZE, VM_GLOBALMEMSIZE, MAXWINMASK, VM_GLOBALMEMADDR, MAXWINSIZE */

// This file expects to be invoked as a Worker (see onmessage below).
importScripts("../io/bitstream.js");
importScripts("../io/bytebuffer.js");
importScripts("archive.js");
importScripts("rarvm.js");

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

// shows a byte value as its hex representation
var nibble = "0123456789ABCDEF";
var byteValueToHexString = function(num) {
    return nibble[num >> 4] + nibble[num & 0xF];
};
var twoByteValueToHexString = function(num) {
    return nibble[(num >> 12) & 0xF] + nibble[(num >> 8) & 0xF] + nibble[(num >> 4) & 0xF] + nibble[num & 0xF];
};


// Volume Types
// MARK_HEAD      = 0x72;
var MAIN_HEAD      = 0x73,
    FILE_HEAD      = 0x74,
    // COMM_HEAD      = 0x75,
    // AV_HEAD        = 0x76,
    // SUB_HEAD       = 0x77,
    // PROTECT_HEAD   = 0x78,
    // SIGN_HEAD      = 0x79,
    // NEWSUB_HEAD    = 0x7a,
    ENDARC_HEAD = 0x7b;

// ============================================================================================== //

/**
 * @param {bitjs.io.BitStream} bstream
 * @constructor
 */
var RarVolumeHeader = function(bstream) {
    var headPos = bstream.bytePtr;
    // byte 1,2
    info("Rar Volume Header @" + bstream.bytePtr);

    this.crc = bstream.readBits(16);
    info("  crc=" + this.crc);

    // byte 3
    this.headType = bstream.readBits(8);
    info("  headType=" + this.headType);

    // Get flags
    // bytes 4,5
    this.flags = {};
    this.flags.value = bstream.peekBits(16);

    info("  flags=" + twoByteValueToHexString(this.flags.value));
    switch (this.headType) {
        case MAIN_HEAD:
            this.flags.MHD_VOLUME = !!bstream.readBits(1);
            this.flags.MHD_COMMENT = !!bstream.readBits(1);
            this.flags.MHD_LOCK = !!bstream.readBits(1);
            this.flags.MHD_SOLID = !!bstream.readBits(1);
            this.flags.MHD_PACK_COMMENT = !!bstream.readBits(1);
            this.flags.MHD_NEWNUMBERING = this.flags.MHD_PACK_COMMENT;
            this.flags.MHD_AV = !!bstream.readBits(1);
            this.flags.MHD_PROTECT = !!bstream.readBits(1);
            this.flags.MHD_PASSWORD = !!bstream.readBits(1);
            this.flags.MHD_FIRSTVOLUME = !!bstream.readBits(1);
            this.flags.MHD_ENCRYPTVER = !!bstream.readBits(1);
            bstream.readBits(6); // unused
            break;
        case FILE_HEAD:
            this.flags.LHD_SPLIT_BEFORE = !!bstream.readBits(1); // 0x0001
            this.flags.LHD_SPLIT_AFTER = !!bstream.readBits(1); // 0x0002
            this.flags.LHD_PASSWORD = !!bstream.readBits(1); // 0x0004
            this.flags.LHD_COMMENT = !!bstream.readBits(1); // 0x0008
            this.flags.LHD_SOLID = !!bstream.readBits(1); // 0x0010
            bstream.readBits(3); // unused
            this.flags.LHD_LARGE = !!bstream.readBits(1); // 0x0100
            this.flags.LHD_UNICODE = !!bstream.readBits(1); // 0x0200
            this.flags.LHD_SALT = !!bstream.readBits(1); // 0x0400
            this.flags.LHD_VERSION = !!bstream.readBits(1); // 0x0800
            this.flags.LHD_EXTTIME = !!bstream.readBits(1); // 0x1000
            this.flags.LHD_EXTFLAGS = !!bstream.readBits(1); // 0x2000
            bstream.readBits(2); // unused
            info("  LHD_SPLIT_BEFORE = " + this.flags.LHD_SPLIT_BEFORE);
            break;
        default:
            bstream.readBits(16);
    }

    // byte 6,7
    this.headSize = bstream.readBits(16);
    info("  headSize=" + this.headSize);
    switch (this.headType) {
        case MAIN_HEAD:
            this.highPosAv = bstream.readBits(16);
            this.posAv = bstream.readBits(32);
            if (this.flags.MHD_ENCRYPTVER) {
                this.encryptVer = bstream.readBits(8);
            }
            info("Found MAIN_HEAD with highPosAv=" + this.highPosAv + ", posAv=" + this.posAv);
            break;
        case FILE_HEAD:
            this.packSize = bstream.readBits(32);
            this.unpackedSize = bstream.readBits(32);
            this.hostOS = bstream.readBits(8);
            this.fileCRC = bstream.readBits(32);
            this.fileTime = bstream.readBits(32);
            this.unpVer = bstream.readBits(8);
            this.method = bstream.readBits(8);
            this.nameSize = bstream.readBits(16);
            this.fileAttr = bstream.readBits(32);

            if (this.flags.LHD_LARGE) {
                info("Warning: Reading in LHD_LARGE 64-bit size values");
                this.HighPackSize = bstream.readBits(32);
                this.HighUnpSize = bstream.readBits(32);
            } else {
                this.HighPackSize = 0;
                this.HighUnpSize = 0;
                if (this.unpackedSize === 0xffffffff) {
                    this.HighUnpSize = 0x7fffffff;
                    this.unpackedSize = 0xffffffff;
                }
            }
            this.fullPackSize = 0;
            this.fullUnpackSize = 0;
            this.fullPackSize |= this.HighPackSize;
            this.fullPackSize <<= 32;
            this.fullPackSize |= this.packSize;

            // read in filename

            this.filename = bstream.readBytes(this.nameSize);
            var _s = "";
            for (var _i = 0; _i < this.filename.length ; _i++) {
                _s += String.fromCharCode(this.filename[_i]);
            }

            this.filename = _s;

            if (this.flags.LHD_SALT) {
                info("Warning: Reading in 64-bit salt value");
                this.salt = bstream.readBits(64); // 8 bytes
            }

            if (this.flags.LHD_EXTTIME) {
                // 16-bit flags
                var extTimeFlags = bstream.readBits(16);

                // this is adapted straight out of arcread.cpp, Archive::ReadHeader()
                for (var I = 0; I < 4; ++I) {
                    var rmode = extTimeFlags >> ((3 - I) * 4);
                    if ((rmode & 8) === 0) {
                        continue;
                    }
                    if (I !== 0) {
                        bstream.readBits(16);
                    }
                    var count = (rmode & 3);
                    for (var J = 0; J < count; ++J) {
                        bstream.readBits(8);
                    }
                }
            }

            if (this.flags.LHD_COMMENT) {
                info("Found a LHD_COMMENT");
            }


            while (headPos + this.headSize > bstream.bytePtr) {
                bstream.readBits(1);
            }

            // If Info line is commented in firefox fails if server on same computer than browser with error "expected expression, got default"
            //info("Found FILE_HEAD with packSize=" + this.packSize + ", unpackedSize= " + this.unpackedSize + ", hostOS=" + this.hostOS + ", unpVer=" + this.unpVer + ", method=" + this.method + ", filename=" + this.filename);

            break;
        default:
            info("Found a header of type 0x" + byteValueToHexString(this.headType));
            // skip the rest of the header bytes (for now)
            bstream.readBytes(this.headSize - 7);
            break;
    }
};

//var BLOCK_LZ  = 0;

var rLDecode = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14, 16, 20, 24, 28, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224],
    rLBits = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5],
    rDBitLengthCounts = [4, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 14, 0, 12],
    rSDDecode = [0, 4, 8, 16, 32, 64, 128, 192],
    rSDBits = [2, 2, 3, 4, 5, 6, 6, 6];

var rDDecode = [0, 1, 2, 3, 4, 6, 8, 12, 16, 24, 32,
    48, 64, 96, 128, 192, 256, 384, 512, 768, 1024, 1536, 2048, 3072,
    4096, 6144, 8192, 12288, 16384, 24576, 32768, 49152, 65536, 98304,
    131072, 196608, 262144, 327680, 393216, 458752, 524288, 589824,
    655360, 720896, 786432, 851968, 917504, 983040
];

var rDBits = [0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5,
    5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14,
    15, 15, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16
];

var rLowDistRepCount = 16;

var rNC = 299,
    rDC = 60,
    rLDC = 17,
    rRC = 28,
    rBC = 20,
    rHuffTableSize = (rNC + rDC + rRC + rLDC);

//var UnpBlockType = BLOCK_LZ;
var UnpOldTable = new Array(rHuffTableSize);

var BD = { //bitdecode
    DecodeLen: new Array(16),
    DecodePos: new Array(16),
    DecodeNum: new Array(rBC)
};
var LD = { //litdecode
    DecodeLen: new Array(16),
    DecodePos: new Array(16),
    DecodeNum: new Array(rNC)
};
var DD = { //distdecode
    DecodeLen: new Array(16),
    DecodePos: new Array(16),
    DecodeNum: new Array(rDC)
};
var LDD = { //low dist decode
    DecodeLen: new Array(16),
    DecodePos: new Array(16),
    DecodeNum: new Array(rLDC)
};
var RD = { //rep decode
    DecodeLen: new Array(16),
    DecodePos: new Array(16),
    DecodeNum: new Array(rRC)
};

/**
 * @type {Array<bitjs.io.ByteBuffer>}
 */
var rOldBuffers = [];

/**
 * The current buffer we are unpacking to.
 * @type {bitjs.io.ByteBuffer}
 */
var rBuffer;

/**
 * The buffer of the final bytes after filtering (only used in Unpack29).
 * @type {bitjs.io.ByteBuffer}
 */
var wBuffer;

var lowDistRepCount = 0;
var prevLowDist = 0;

var rOldDist = [0, 0, 0, 0];
var lastDist;
var lastLength;

/**
 * In unpack.cpp, UnpPtr keeps track of what bytes have been unpacked
 * into the Window buffer and WrPtr keeps track of what bytes have been
 * actually written to disk after the unpacking and optional filtering
 * has been done.
 *
 * In our case, rBuffer is the buffer for the unpacked bytes and wBuffer is
 * the final output bytes.
 */


/**
 * Read in Huffman tables for RAR
 * @param {bitjs.io.BitStream} bstream
 */
function rarReadTables(bstream) {
    var BitLength = new Array(rBC);
    var Table = new Array(rHuffTableSize);
    var i;
    // before we start anything we need to get byte-aligned
    bstream.readBits((8 - bstream.bitPtr) & 0x7);

    if (bstream.readBits(1)) {
        info("Error!  PPM not implemented yet");
        return;
    }

    if (!bstream.readBits(1)) { //discard old table
        for (i = UnpOldTable.length; i--;) {
            UnpOldTable[i] = 0;
        }
    }

    // read in bit lengths
    for (var I = 0; I < rBC; ++I) {
        var Length = bstream.readBits(4);
        if (Length === 15) {
            var ZeroCount = bstream.readBits(4);
            if (ZeroCount === 0) {
                BitLength[I] = 15;
            } else {
                ZeroCount += 2;
                while (ZeroCount-- > 0 && I < rBC) {
                    BitLength[I++] = 0;
                }
                --I;
            }
        } else {
            BitLength[I] = Length;
        }
    }

    // now all 20 bit lengths are obtained, we construct the Huffman Table:

    rarMakeDecodeTables(BitLength, 0, BD, rBC);

    var TableSize = rHuffTableSize;
    //console.log(DecodeLen, DecodePos, DecodeNum);
    for (i = 0; i < TableSize;) {
        var N;
        var num = rarDecodeNumber(bstream, BD);
        if (num < 16) {
            Table[i] = (num + UnpOldTable[i]) & 0xf;
            i++;
        } else if (num < 18) {
            N = (num === 16) ? (bstream.readBits(3) + 3) : (bstream.readBits(7) + 11);

            while (N-- > 0 && i < TableSize) {
                Table[i] = Table[i - 1];
                i++;
            }
        } else {
            N = (num === 18) ? (bstream.readBits(3) + 3) : (bstream.readBits(7) + 11);

            while (N-- > 0 && i < TableSize) {
                Table[i++] = 0;
            }
        }
    }

    rarMakeDecodeTables(Table, 0, LD, rNC);
    rarMakeDecodeTables(Table, rNC, DD, rDC);
    rarMakeDecodeTables(Table, rNC + rDC, LDD, rLDC);
    rarMakeDecodeTables(Table, rNC + rDC + rLDC, RD, rRC);

    for (i = UnpOldTable.length; i--;) {
        UnpOldTable[i] = Table[i];
    }
    return true;
}


function rarDecodeNumber(bstream, dec) {
    var DecodeLen = dec.DecodeLen,
        DecodePos = dec.DecodePos,
        DecodeNum = dec.DecodeNum;
    var bitField = bstream.getBits() & 0xfffe;
    //some sort of rolled out binary search
    var bits = ((bitField < DecodeLen[8]) ?
        ((bitField < DecodeLen[4]) ?
            ((bitField < DecodeLen[2]) ?
                ((bitField < DecodeLen[1]) ? 1 : 2) :
                ((bitField < DecodeLen[3]) ? 3 : 4)) :
            (bitField < DecodeLen[6]) ?
                ((bitField < DecodeLen[5]) ? 5 : 6) :
                ((bitField < DecodeLen[7]) ? 7 : 8)) :
        ((bitField < DecodeLen[12]) ?
            ((bitField < DecodeLen[10]) ?
                ((bitField < DecodeLen[9]) ? 9 : 10) :
                ((bitField < DecodeLen[11]) ? 11 : 12)) :
            (bitField < DecodeLen[14]) ?
                ((bitField < DecodeLen[13]) ? 13 : 14) :
                15));
    bstream.readBits(bits);
    var N = DecodePos[bits] + ((bitField - DecodeLen[bits - 1]) >>> (16 - bits));

    return DecodeNum[N];
}


function rarMakeDecodeTables(BitLength, offset, dec, size) {
    var DecodeLen = dec.DecodeLen;
    var DecodePos = dec.DecodePos;
    var DecodeNum = dec.DecodeNum;
    var LenCount = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
    var TmpPos = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
    var N = 0;
    var M = 0;
    var i;
    for (i = DecodeNum.length; i--;) {
        DecodeNum[i] = 0;
    }
    for (i = 0; i < size; i++) {
        LenCount[BitLength[i + offset] & 0xF]++;
    }
    LenCount[0] = 0;
    TmpPos[0] = 0;
    DecodePos[0] = 0;
    DecodeLen[0] = 0;

    var I;
    for (I = 1; I < 16; ++I) {
        N = 2 * (N + LenCount[I]);
        M = (N << (15 - I));
        if (M > 0xFFFF) {
            M = 0xFFFF;
        }
        DecodeLen[I] = M;
        DecodePos[I] = DecodePos[I - 1] + LenCount[I - 1];
        TmpPos[I] = DecodePos[I];
    }
    for (I = 0; I < size; ++I) {
        if (BitLength[I + offset] !== 0) {
            DecodeNum[TmpPos[BitLength[offset + I] & 0xF]++] = I;
        }
    }

}

// TODO: implement
/**
 * @param {bitjs.io.BitStream} bstream
 * @param {boolean} Solid
 */
function unpack15() { //bstream, Solid) {
    info("ERROR!  RAR 1.5 compression not supported");
}

/**
 * Unpacks the bit stream into rBuffer using the Unpack20 algorithm.
 * @param {bitjs.io.BitStream} bstream
 * @param {boolean} Solid
 */
function unpack20(bstream) { //, Solid) {
    var destUnpSize = rBuffer.data.length;
    var oldDistPtr = 0;
    var Length;
    var Distance;
    rarReadTables20(bstream);
    while (destUnpSize > rBuffer.ptr) {
        var num = rarDecodeNumber(bstream, LD);
        var Bits;
        if (num < 256) {
            rBuffer.insertByte(num);
            continue;
        }
        if (num > 269) {
            Length = rLDecode[num -= 270] + 3;
            if ((Bits = rLBits[num]) > 0) {
                Length += bstream.readBits(Bits);
            }
            var DistNumber = rarDecodeNumber(bstream, DD);
            Distance = rDDecode[DistNumber] + 1;
            if ((Bits = rDBits[DistNumber]) > 0) {
                Distance += bstream.readBits(Bits);
            }
            if (Distance >= 0x2000) {
                Length++;
                if (Distance >= 0x40000) {
                    Length++;
                }
            }
            lastLength = Length;
            lastDist = rOldDist[oldDistPtr++ & 3] = Distance;
            rarCopyString(Length, Distance);
            continue;
        }
        if (num === 269) {
            rarReadTables20(bstream);
            rarUpdateProgress();
            continue;
        }
        if (num === 256) {
            lastDist = rOldDist[oldDistPtr++ & 3] = lastDist;
            rarCopyString(lastLength, lastDist);
            continue;
        }
        if (num < 261) {
            Distance = rOldDist[(oldDistPtr - (num - 256)) & 3];
            var LengthNumber = rarDecodeNumber(bstream, RD);
            Length = rLDecode[LengthNumber] + 2;
            if ((Bits = rLBits[LengthNumber]) > 0) {
                Length += bstream.readBits(Bits);
            }
            if (Distance >= 0x101) {
                Length++;
                if (Distance >= 0x2000) {
                    Length++;
                    if (Distance >= 0x40000) {
                        Length++;
                    }
                }
            }
            lastLength = Length;
            lastDist = rOldDist[oldDistPtr++ & 3] = Distance;
            rarCopyString(Length, Distance);
            continue;
        }
        if (num < 270) {
            Distance = rSDDecode[num -= 261] + 1;
            if ((Bits = rSDBits[num]) > 0) {
                Distance += bstream.readBits(Bits);
            }
            lastLength = 2;
            lastDist = rOldDist[oldDistPtr++ & 3] = Distance;
            rarCopyString(2, Distance);
            continue;
        }
    }
    rarUpdateProgress();
}

function rarUpdateProgress() {
    var change = rBuffer.ptr - currentBytesUnarchivedInFile;
    currentBytesUnarchivedInFile = rBuffer.ptr;
    currentBytesUnarchived += change;
    postProgress();
}

var rNC20 = 298,
    rDC20 = 48,
    rRC20 = 28,
    rBC20 = 19,
    rMC20 = 257;

var UnpOldTable20 = new Array(rMC20 * 4);

function rarReadTables20(bstream) {
    var BitLength = new Array(rBC20);
    var Table = new Array(rMC20 * 4);
    var TableSize, N, I;
    var i;
    bstream.readBits(1);
    if (!bstream.readBits(1)) {
        for (i = UnpOldTable20.length; i--;) {
            UnpOldTable20[i] = 0;
        }
    }
    TableSize = rNC20 + rDC20 + rRC20;
    for (I = 0; I < rBC20; I++) {
        BitLength[I] = bstream.readBits(4);
    }
    rarMakeDecodeTables(BitLength, 0, BD, rBC20);
    I = 0;
    while (I < TableSize) {
        var num = rarDecodeNumber(bstream, BD);
        if (num < 16) {
            Table[I] = num + UnpOldTable20[I] & 0xf;
            I++;
        } else if (num === 16) {
            N = bstream.readBits(2) + 3;
            while (N-- > 0 && I < TableSize) {
                Table[I] = Table[I - 1];
                I++;
            }
        } else {
            if (num === 17) {
                N = bstream.readBits(3) + 3;
            } else {
                N = bstream.readBits(7) + 11;
            }
            while (N-- > 0 && I < TableSize) {
                Table[I++] = 0;
            }
        }
    }
    rarMakeDecodeTables(Table, 0, LD, rNC20);
    rarMakeDecodeTables(Table, rNC20, DD, rDC20);
    rarMakeDecodeTables(Table, rNC20 + rDC20, RD, rRC20);
    for (i = UnpOldTable20.length; i--;) {
        UnpOldTable20[i] = Table[i];
    }
}

// ============================================================================================== //

// Unpack code specific to RarVM
var VM = new RarVM();

/**
 * Filters code, one entry per filter.
 * @type {Array<UnpackFilter>}
 */
var Filters = [];

/**
 * Filters stack, several entrances of same filter are possible.
 * @type {Array<UnpackFilter>}
 */
var PrgStack = [];

/**
 * Lengths of preceding blocks, one length per filter. Used to reduce
 * size required to write block length if lengths are repeating.
 * @type {Array<number>}
 */
var OldFilterLengths = [];

var LastFilter = 0;

function initFilters() {
    OldFilterLengths = [];
    LastFilter = 0;
    Filters = [];
    PrgStack = [];
}


/**
 * @param {number} firstByte The first byte (flags).
 * @param {Uint8Array} vmCode An array of bytes.
 */
function rarAddVMCode(firstByte, vmCode) {
    VM.init();
    var i;
    var bstream = new bitjs.io.BitStream(vmCode.buffer, true /* rtl */ );

    var filtPos;
    if (firstByte & 0x80) {
        filtPos = RarVM.readData(bstream);
        if (filtPos === 0) {
            initFilters();
        } else {
            filtPos--;
        }
    } else {
        filtPos = LastFilter;
    }

    if (filtPos > Filters.length || filtPos > OldFilterLengths.length) {
        return false;
    }

    LastFilter = filtPos;
    var newFilter = (filtPos === Filters.length);

    // new filter for PrgStack
    var stackFilter = new UnpackFilter();
    var filter = null;
    // new filter code, never used before since VM reset
    if (newFilter) {
        // too many different filters, corrupt archive
        if (filtPos > 1024) {
            return false;
        }

        filter = new UnpackFilter();
        Filters.push(filter);
        stackFilter.ParentFilter = (Filters.length - 1);
        OldFilterLengths.push(0); // OldFilterLengths.Add(1)
        filter.ExecCount = 0;
    } else { // filter was used in the past
        filter = Filters[filtPos];
        stackFilter.ParentFilter = filtPos;
        filter.ExecCount++;
    }

    var emptyCount = 0;
    for (i = 0; i < PrgStack.length; ++i) {
        PrgStack[i - emptyCount] = PrgStack[i];

        if (PrgStack[i] === null) {
            emptyCount++;
        }
        if (emptyCount > 0) {
            PrgStack[i] = null;
        }
    }

    if (emptyCount === 0) {
        PrgStack.push(null); //PrgStack.Add(1);
        emptyCount = 1;
    }

    var stackPos = PrgStack.length - emptyCount;
    PrgStack[stackPos] = stackFilter;
    stackFilter.ExecCount = filter.ExecCount;

    var blockStart = RarVM.readData(bstream);
    if (firstByte & 0x40) {
        blockStart += 258;
    }
    stackFilter.BlockStart = (blockStart + rBuffer.ptr) & MAXWINMASK;

    if (firstByte & 0x20) {
        stackFilter.BlockLength = RarVM.readData(bstream);
    } else {
        stackFilter.BlockLength = filtPos < OldFilterLengths.length ?
            OldFilterLengths[filtPos] :
            0;
    }
    stackFilter.NextWindow = (wBuffer.ptr !== rBuffer.ptr) &&
        (((wBuffer.ptr - rBuffer.ptr) & MAXWINMASK) <= blockStart);

    OldFilterLengths[filtPos] = stackFilter.BlockLength;

    for (i = 0; i < 7; ++i) {
        stackFilter.Prg.InitR[i] = 0;
    }
    stackFilter.Prg.InitR[3] = VM_GLOBALMEMADDR;
    stackFilter.Prg.InitR[4] = stackFilter.BlockLength;
    stackFilter.Prg.InitR[5] = stackFilter.ExecCount;

    // set registers to optional parameters if any
    if (firstByte & 0x10) {
        var initMask = bstream.readBits(7);
        for (i = 0; i < 7; ++i) {
            if (initMask & (1 << i)) {
                stackFilter.Prg.InitR[i] = RarVM.readData(bstream);
            }
        }
    }

    if (newFilter) {
        var vmCodeSize = RarVM.readData(bstream);
        if (vmCodeSize >= 0x10000 || vmCodeSize === 0) {
            return false;
        }
        vmCode = new Uint8Array(vmCodeSize);
        for (i = 0; i < vmCodeSize; ++i) {
            //if (Inp.Overflow(3))
            //  return(false);
            vmCode[i] = bstream.readBits(8);
        }
        VM.prepare(vmCode, filter.Prg);
    }
    stackFilter.Prg.Cmd = filter.Prg.Cmd;
    stackFilter.Prg.AltCmd = filter.Prg.Cmd;

    var staticDataSize = filter.Prg.StaticData.length;
    if (staticDataSize > 0 && staticDataSize < VM_GLOBALMEMSIZE) {
        // read statically defined data contained in DB commands
        for (i = 0; i < staticDataSize; ++i) {
            stackFilter.Prg.StaticData[i] = filter.Prg.StaticData[i];
        }
    }

    if (stackFilter.Prg.GlobalData.length < VM_FIXEDGLOBALSIZE) {
        stackFilter.Prg.GlobalData = new Uint8Array(VM_FIXEDGLOBALSIZE);
    }

    var globalData = stackFilter.Prg.GlobalData;
    for (i = 0; i < 7; ++i) {
        VM.setLowEndianValue(globalData, stackFilter.Prg.InitR[i], i * 4);
    }

    VM.setLowEndianValue(globalData, stackFilter.BlockLength, 0x1c);
    VM.setLowEndianValue(globalData, 0, 0x20);
    VM.setLowEndianValue(globalData, stackFilter.ExecCount, 0x2c);
    for (i = 0; i < 16; ++i) {
        globalData[0x30 + i] = 0;
    }

    // put data block passed as parameter if any
    if (firstByte & 8) {
        //if (Inp.Overflow(3))
        //  return(false);
        var dataSize = RarVM.readData(bstream);
        if (dataSize > (VM_GLOBALMEMSIZE - VM_FIXEDGLOBALSIZE)) {
            return (false);
        }

        var curSize = stackFilter.Prg.GlobalData.length;
        if (curSize < dataSize + VM_FIXEDGLOBALSIZE) {
            // Resize global data and update the stackFilter and local variable.
            var numBytesToAdd = dataSize + VM_FIXEDGLOBALSIZE - curSize;
            var newGlobalData = new Uint8Array(globalData.length + numBytesToAdd);
            newGlobalData.set(globalData);

            stackFilter.Prg.GlobalData = newGlobalData;
            globalData = newGlobalData;
        }
        //byte *GlobalData=&StackFilter->Prg.GlobalData[VM_FIXEDGLOBALSIZE];
        for (i = 0; i < dataSize; ++i) {
            //if (Inp.Overflow(3))
            //  return(false);
            globalData[VM_FIXEDGLOBALSIZE + i] = bstream.readBits(8);
        }
    }

    return true;
}


/**
 * @param {!bitjs.io.BitStream} bstream
 */
function rarReadVMCode(bstream) {
    var firstByte = bstream.readBits(8);
    var length = (firstByte & 7) + 1;
    if (length === 7) {
        length = bstream.readBits(8) + 7;
    } else if (length === 8) {
        length = bstream.readBits(16);
    }

    // Read all bytes of VM code into an array.
    var vmCode = new Uint8Array(length);
    for (var i = 0; i < length; i++) {
        // Do something here with checking readbuf.
        vmCode[i] = bstream.readBits(8);
    }
    return rarAddVMCode(firstByte, vmCode);
}

/**
 * Unpacks the bit stream into rBuffer using the Unpack29 algorithm.
 * @param {bitjs.io.BitStream} bstream
 * @param {boolean} Solid
 */
function unpack29(bstream) {
    // lazy initialize rDDecode and rDBits

    var DDecode = new Array(rDC);
    var DBits = new Array(rDC);
    var Distance = 0;
    var Length = 0;
    var Dist = 0, BitLength = 0, Slot = 0;
    var I;
    for (I = 0; I < rDBitLengthCounts.length; I++, BitLength++) {
        for (var J = 0; J < rDBitLengthCounts[I]; J++, Slot++, Dist += (1 << BitLength)) {
            DDecode[Slot] = Dist;
            DBits[Slot] = BitLength;
        }
    }

    var Bits;
    //tablesRead = false;

    rOldDist = [0, 0, 0, 0];

    lastDist = 0;
    lastLength = 0;
    var i;
    for (i = UnpOldTable.length; i--;) {
        UnpOldTable[i] = 0;
    }

    // read in Huffman tables
    rarReadTables(bstream);

    while (true) {
        var num = rarDecodeNumber(bstream, LD);

        if (num < 256) {
            rBuffer.insertByte(num);
            continue;
        }
        if (num >= 271) {
            Length = rLDecode[num -= 271] + 3;
            if ((Bits = rLBits[num]) > 0) {
                Length += bstream.readBits(Bits);
            }
            var DistNumber = rarDecodeNumber(bstream, DD);
            Distance = DDecode[DistNumber] + 1;
            if ((Bits = DBits[DistNumber]) > 0) {
                if (DistNumber > 9) {
                    if (Bits > 4) {
                        Distance += ((bstream.getBits() >>> (20 - Bits)) << 4);
                        bstream.readBits(Bits - 4);
                        //todo: check this
                    }
                    if (lowDistRepCount > 0) {
                        lowDistRepCount--;
                        Distance += prevLowDist;
                    } else {
                        var LowDist = rarDecodeNumber(bstream, LDD);
                        if (LowDist === 16) {
                            lowDistRepCount = rLowDistRepCount - 1;
                            Distance += prevLowDist;
                        } else {
                            Distance += LowDist;
                            prevLowDist = LowDist;
                        }
                    }
                } else {
                    Distance += bstream.readBits(Bits);
                }
            }
            if (Distance >= 0x2000) {
                Length++;
                if (Distance >= 0x40000) {
                    Length++;
                }
            }
            rarInsertOldDist(Distance);
            rarInsertLastMatch(Length, Distance);
            rarCopyString(Length, Distance);
            continue;
        }
        if (num === 256) {
            if (!rarReadEndOfBlock(bstream)) {
                break;
            }
            continue;
        }
        if (num === 257) {
            if (!rarReadVMCode(bstream)) {
                break;
            }
            continue;
        }
        if (num === 258) {
            if (lastLength !== 0) {
                rarCopyString(lastLength, lastDist);
            }
            continue;
        }
        if (num < 263) {
            var DistNum = num - 259;
            Distance = rOldDist[DistNum];

            for (var I2 = DistNum; I2 > 0; I2--) {
                rOldDist[I2] = rOldDist[I2 - 1];
            }
            rOldDist[0] = Distance;

            var LengthNumber = rarDecodeNumber(bstream, RD);
            Length = rLDecode[LengthNumber] + 2;
            if ((Bits = rLBits[LengthNumber]) > 0) {
                Length += bstream.readBits(Bits);
            }
            rarInsertLastMatch(Length, Distance);
            rarCopyString(Length, Distance);
            continue;
        }
        if (num < 272) {
            Distance = rSDDecode[num -= 263] + 1;
            if ((Bits = rSDBits[num]) > 0) {
                Distance += bstream.readBits(Bits);
            }
            rarInsertOldDist(Distance);
            rarInsertLastMatch(2, Distance);
            rarCopyString(2, Distance);
            continue;
        }
    } // while (true)
    rarUpdateProgress();
    rarWriteBuf();
}

/**
 * Does stuff to the current byte buffer (rBuffer) based on
 * the filters loaded into the RarVM and writes out to wBuffer.
 */
function rarWriteBuf() {
    var writeSize = (rBuffer.ptr & MAXWINMASK);
    var j;
    var flt;
    for (var i = 0; i < PrgStack.length; ++i) {
        flt = PrgStack[i];
        if (flt === null) {
            continue;
        }

        if (flt.NextWindow) {
            flt.NextWindow = false;
            continue;
        }

        var blockStart = flt.BlockStart;
        var blockLength = flt.BlockLength;
        var parentPrg;

        // WrittenBorder = wBuffer.ptr
        if (((blockStart - wBuffer.ptr) & MAXWINMASK) < writeSize) {
            if (wBuffer.ptr !== blockStart) {
                // Copy blockStart bytes from rBuffer into wBuffer.
                rarWriteArea(wBuffer.ptr, blockStart);
                writeSize = (rBuffer.ptr - wBuffer.ptr) & MAXWINMASK;
            }
            if (blockLength <= writeSize) {
                var blockEnd = (blockStart + blockLength) & MAXWINMASK;
                if (blockStart < blockEnd || blockEnd === 0) {
                    VM.setMemory(0, rBuffer.data.subarray(blockStart, blockStart + blockLength), blockLength);
                } else {
                    var firstPartLength = MAXWINSIZE - blockStart;
                    VM.setMemory(0, rBuffer.data.subarray(blockStart, blockStart + firstPartLength), firstPartLength);
                    VM.setMemory(firstPartLength, rBuffer.data, blockEnd);
                }

                parentPrg = Filters[flt.ParentFilter].Prg;
                var prg = flt.Prg;

                if (parentPrg.GlobalData.length > VM_FIXEDGLOBALSIZE) {
                    // Copy global data from previous script execution if any.
                    prg.GlobalData = new Uint8Array(parentPrg.GlobalData);
                }

                rarExecuteCode(prg);
                var globalDataLen;

                if (prg.GlobalData.length > VM_FIXEDGLOBALSIZE) {
                    // Save global data for next script execution.
                    globalDataLen = prg.GlobalData.length;
                    if (parentPrg.GlobalData.length < globalDataLen) {
                        parentPrg.GlobalData = new Uint8Array(globalDataLen);
                    }
                    parentPrg.GlobalData.set(
                        this.mem_.subarray(VM_FIXEDGLOBALSIZE, VM_FIXEDGLOBALSIZE + globalDataLen),
                        VM_FIXEDGLOBALSIZE);
                } else {
                    parentPrg.GlobalData = new Uint8Array(0);
                }

                var filteredData = prg.FilteredData;

                PrgStack[i] = null;
                while (i + 1 < PrgStack.length) {
                    var nextFilter = PrgStack[i + 1];
                    if (nextFilter === null || nextFilter.BlockStart !== blockStart ||
                        nextFilter.BlockLength !== filteredData.length || nextFilter.NextWindow) {
                        break;
                    }

                    // Apply several filters to same data block.

                    VM.setMemory(0, filteredData, filteredData.length);

                    parentPrg = Filters[nextFilter.ParentFilter].Prg;
                    var nextPrg = nextFilter.Prg;

                    globalDataLen = parentPrg.GlobalData.length;
                    if (globalDataLen > VM_FIXEDGLOBALSIZE) {
                        // Copy global data from previous script execution if any.
                        nextPrg.GlobalData = new Uint8Array(globalDataLen);
                        nextPrg.GlobalData.set(parentPrg.GlobalData.subarray(VM_FIXEDGLOBALSIZE, VM_FIXEDGLOBALSIZE + globalDataLen), VM_FIXEDGLOBALSIZE);
                    }

                    rarExecuteCode(nextPrg);

                    if (nextPrg.GlobalData.length > VM_GLOBALMEMSIZE) {
                        // Save global data for next script execution.
                        globalDataLen = nextPrg.GlobalData.length;
                        if (parentPrg.GlobalData.length < globalDataLen) {
                            parentPrg.GlobalData = new Uint8Array(globalDataLen);
                        }
                        parentPrg.GlobalData.set(
                            this.mem_.subarray(VM_FIXEDGLOBALSIZE, VM_FIXEDGLOBALSIZE + globalDataLen),
                            VM_FIXEDGLOBALSIZE);
                    } else {
                        parentPrg.GlobalData = new Uint8Array(0);
                    }

                    filteredData = nextPrg.FilteredData;
                    i++;
                    PrgStack[i] = null;
                } // while (i + 1 < PrgStack.length)

                for (j = 0; j < filteredData.length; ++j) {
                    wBuffer.insertByte(filteredData[j]);
                }
                writeSize = (rBuffer.ptr - wBuffer.ptr) & MAXWINMASK;
            } else { // if (blockLength <= writeSize)
                for (j = i; j < PrgStack.length; ++j) {
                    flt = PrgStack[j];
                    if (flt !== null && flt.NextWindow) {
                        flt.NextWindow = false;
                    }
                }
                //WrPtr=WrittenBorder;
                return;
            }
        } // if (((blockStart - wBuffer.ptr) & MAXWINMASK) < writeSize)
    } // for (var i = 0; i < PrgStack.length; ++i)

    // Write any remaining bytes from rBuffer to wBuffer;
    rarWriteArea(wBuffer.ptr, rBuffer.ptr);

    // Now that the filtered buffer has been written, swap it back to rBuffer.
    rBuffer = wBuffer;
}

/**
 * Copy bytes from rBuffer to wBuffer.
 * @param {number} startPtr The starting point to copy from rBuffer.
 * @param {number} endPtr The ending point to copy from rBuffer.
 */
function rarWriteArea(startPtr, endPtr) {
    if (endPtr < startPtr) {
        console.error("endPtr < startPtr, endPtr=" + endPtr + ", startPtr=" + startPtr);
        //    rarWriteData(startPtr, -(int)StartPtr & MAXWINMASK);
        //    RarWriteData(0, endPtr);
        return;
    } else if (startPtr < endPtr) {
        rarWriteData(startPtr, endPtr - startPtr);
    }
}

/**
 * Writes bytes into wBuffer from rBuffer.
 * @param {number} offset The starting point to copy bytes from rBuffer.
 * @param {number} numBytes The number of bytes to copy.
 */
function rarWriteData(offset, numBytes) {
    if (wBuffer.ptr >= rBuffer.data.length) {
        return;
    }
    var leftToWrite = rBuffer.data.length - wBuffer.ptr;
    if (numBytes > leftToWrite) {
        numBytes = leftToWrite;
    }
    for (var i = 0; i < numBytes; ++i) {
        wBuffer.insertByte(rBuffer.data[offset + i]);
    }
}

/**
 * @param {VM_PreparedProgram} prg
 */
function rarExecuteCode(prg) {
    if (prg.GlobalData.length > 0) {
        var writtenFileSize = wBuffer.ptr;
        prg.InitR[6] = writtenFileSize;
        VM.setLowEndianValue(prg.GlobalData, writtenFileSize, 0x24);
        VM.setLowEndianValue(prg.GlobalData, (writtenFileSize >>> 32) >> 0, 0x28);
        VM.execute(prg);
    }
}

function rarReadEndOfBlock(bstream) {
    rarUpdateProgress();

    var NewTable = false,
        NewFile = false;
    if (bstream.readBits(1)) {
        NewTable = true;
    } else {
        NewFile = true;
        NewTable = !!bstream.readBits(1);
    }
    //tablesRead = !NewTable;
    return !(NewFile || (NewTable && !rarReadTables(bstream)));
}

function rarInsertLastMatch(length, distance) {
    lastDist = distance;
    lastLength = length;
}

function rarInsertOldDist(distance) {
    rOldDist.splice(3, 1);
    rOldDist.splice(0, 0, distance);
}

/**
 * Copies len bytes from distance bytes ago in the buffer to the end of the
 * current byte buffer.
 * @param {number} length How many bytes to copy.
 * @param {number} distance How far back in the buffer from the current write
 *     pointer to start copying from.
 */
function rarCopyString(length, distance) {
    var srcPtr = rBuffer.ptr - distance;
    if (srcPtr < 0) {
        var l = rOldBuffers.length;
        while (srcPtr < 0) {
            srcPtr = rOldBuffers[--l].data.length + srcPtr;
        }
        // TODO: lets hope that it never needs to read beyond file boundaries
        while (length--) {
            rBuffer.insertByte(rOldBuffers[l].data[srcPtr++]);
        }
    }
    if (length > distance) {
        while (length--) {
            rBuffer.insertByte(rBuffer.data[srcPtr++]);
        }
    } else {
        rBuffer.insertBytes(rBuffer.data.subarray(srcPtr, srcPtr + length));
    }
}

/**
 * @param {RarLocalFile} v
 */
function unpack(v) {
    // TODO: implement what happens when unpVer is < 15
    var Ver = v.header.unpVer <= 15 ? 15 : v.header.unpVer;
    // var Solid = v.header.LHD_SOLID;
    var bstream = new bitjs.io.BitStream(v.fileData.buffer, true /* rtl */, v.fileData.byteOffset, v.fileData.byteLength);

    rBuffer = new bitjs.io.ByteBuffer(v.header.unpackedSize);

    info("Unpacking " + v.filename + " RAR v" + Ver);

    switch (Ver) {
        case 15: // rar 1.5 compression
            unpack15(); //(bstream, Solid);
            break;
        case 20: // rar 2.x compression
        case 26: // files larger than 2GB
            unpack20(bstream); //, Solid);
            break;
        case 29: // rar 3.x compression
        case 36: // alternative hash
            wBuffer = new bitjs.io.ByteBuffer(rBuffer.data.length);
            unpack29(bstream);
            break;
    } // switch(method)

    rOldBuffers.push(rBuffer);
    // TODO: clear these old buffers when there's over 4MB of history
    return rBuffer.data;
}

// bstream is a bit stream
var RarLocalFile = function(bstream) {
    this.header = new RarVolumeHeader(bstream);
    this.filename = this.header.filename;

    if (this.header.headType !== FILE_HEAD && this.header.headType !== ENDARC_HEAD) {
        this.isValid = false;
        info("Error! RAR Volume did not include a FILE_HEAD header ");
    } else {
        // read in the compressed data
        this.fileData = null;
        if (this.header.packSize > 0) {
            this.fileData = bstream.readBytes(this.header.packSize);
            this.isValid = true;
        }
    }
};

RarLocalFile.prototype.unrar = function() {
    if (!this.header.flags.LHD_SPLIT_BEFORE) {
        // unstore file
        if (this.header.method === 0x30) {
            info("Unstore " + this.filename);
            this.isValid = true;

            currentBytesUnarchivedInFile += this.fileData.length;
            currentBytesUnarchived += this.fileData.length;

            // Create a new buffer and copy it over.
            var len = this.header.packSize;
            var newBuffer = new bitjs.io.ByteBuffer(len);
            newBuffer.insertBytes(this.fileData);
            this.fileData = newBuffer.data;
        } else {
            this.isValid = true;
            this.fileData = unpack(this);
        }
    }
};

var unrar = function(arrayBuffer) {
    currentFilename = "";
    currentFileNumber = 0;
    currentBytesUnarchivedInFile = 0;
    currentBytesUnarchived = 0;
    totalUncompressedBytesInArchive = 0;
    totalFilesInArchive = 0;

    postMessage(new bitjs.archive.UnarchiveStartEvent());
    var bstream = new bitjs.io.BitStream(arrayBuffer, false /* rtl */);

    var header = new RarVolumeHeader(bstream);
    if (header.crc === 0x6152 &&
        header.headType === 0x72 &&
        header.flags.value === 0x1A21 &&
        header.headSize === 7) {
        info("Found RAR signature");

        var mhead = new RarVolumeHeader(bstream);
        if (mhead.headType !== MAIN_HEAD) {
            info("Error! RAR did not include a MAIN_HEAD header");
        } else {
            var localFiles = [];
            var localFile = null;
            do {
                try {
                    localFile = new RarLocalFile(bstream);
                    info("RAR localFile isValid=" + localFile.isValid + ", volume packSize=" + localFile.header.packSize);
                    if (localFile && localFile.isValid && localFile.header.packSize > 0) {
                        totalUncompressedBytesInArchive += localFile.header.unpackedSize;
                        localFiles.push(localFile);
                    } else if (localFile.header.packSize === 0 && localFile.header.unpackedSize === 0) {
                        localFile.isValid = true;
                    }
                } catch (err) {
                    break;
                }
                //info("bstream" + bstream.bytePtr+"/"+bstream.bytes.length);
            } while (localFile.isValid);
            totalFilesInArchive = localFiles.length;

            // now we have all information but things are unpacked
            localFiles.sort(alphanumCase);

            info(localFiles.map(function(a) {
                return a.filename;
            }).join(", "));
            for (var i = 0; i < localFiles.length; ++i) {
                var localfile = localFiles[i];

                // update progress
                currentFilename = localfile.header.filename;
                currentBytesUnarchivedInFile = 0;

                // actually do the unzipping
                localfile.unrar();

                if (localfile.isValid) {
                    postMessage(new bitjs.archive.UnarchiveExtractEvent(localfile));
                    postProgress();
                }
            }

            postProgress();
        }
    } else {
        err("Invalid RAR file");
    }
    postMessage(new bitjs.archive.UnarchiveFinishEvent());
};

// event.data.file has the ArrayBuffer.
onmessage = function(event) {
    var ab = event.data.file;
    unrar(ab, true);
};
