/**
 * unrar.js
 *
 * Licensed under the MIT License
 *
 * Copyright(c) 2011 Google Inc.
 * Copyright(c) 2011 antimatter15
 */

// TODO: Rewrite the RarLocalHeader parsing to use a ByteStream instead
// of a BitStream so that it throws properly when not enough bytes are
// present.

// This file expects to be invoked as a Worker (see onmessage below).
importScripts('../io/bitstream.js');
importScripts('../io/bytestream.js');
importScripts('../io/bytebuffer.js');
importScripts('archive.js');
importScripts('rarvm.js');

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
let currentFilename = '';
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
      parseInt(bytestream.getNumBytesRead(), 10),
  ));
};

// shows a byte value as its hex representation
const nibble = '0123456789ABCDEF';
const byteValueToHexString = function(num) {
  return nibble[num>>4] + nibble[num&0xF];
};
const twoByteValueToHexString = function(num) {
  return nibble[(num>>12)&0xF] + nibble[(num>>8)&0xF] + nibble[(num>>4)&0xF] + nibble[num&0xF];
};


// Volume Types
const MARK_HEAD      = 0x72;
const MAIN_HEAD      = 0x73;
const FILE_HEAD      = 0x74;
const COMM_HEAD      = 0x75;
const AV_HEAD        = 0x76;
const SUB_HEAD       = 0x77;
const PROTECT_HEAD   = 0x78;
const SIGN_HEAD      = 0x79;
const NEWSUB_HEAD    = 0x7a;
const ENDARC_HEAD    = 0x7b;

// ============================================================================================== //

/**
 */
class RarVolumeHeader {
  /**
   * @param {bitjs.io.ByteStream} bstream
   */
  constructor(bstream) {
    let headBytesRead = 0;

    // byte 1,2
    this.crc = bstream.readNumber(2);

    // byte 3
    this.headType = bstream.readNumber(1);

    // Get flags
    // bytes 4,5
    this.flags = {};
    this.flags.value = bstream.readNumber(2);
    const flagsValue = this.flags.value;
    
    switch (this.headType) {
      case MAIN_HEAD:
        this.flags.MHD_VOLUME = !!(flagsValue & 0x01);
        this.flags.MHD_COMMENT = !!(flagsValue & 0x02);
        this.flags.MHD_LOCK = !!(flagsValue & 0x04);
        this.flags.MHD_SOLID = !!(flagsValue & 0x08);
        this.flags.MHD_PACK_COMMENT = !!(flagsValue & 0x10);
        this.flags.MHD_NEWNUMBERING = this.flags.MHD_PACK_COMMENT;
        this.flags.MHD_AV = !!(flagsValue & 0x20);
        this.flags.MHD_PROTECT = !!(flagsValue & 0x40);
        this.flags.MHD_PASSWORD = !!(flagsValue & 0x80);
        this.flags.MHD_FIRSTVOLUME = !!(flagsValue & 0x100);
        this.flags.MHD_ENCRYPTVER = !!(flagsValue & 0x200);
        //bstream.readBits(6); // unused
        break;
      case FILE_HEAD:
        this.flags.LHD_SPLIT_BEFORE = !!(flagsValue & 0x01);
        this.flags.LHD_SPLIT_AFTER = !!(flagsValue & 0x02);
        this.flags.LHD_PASSWORD = !!(flagsValue & 0x04);
        this.flags.LHD_COMMENT = !!(flagsValue & 0x08);
        this.flags.LHD_SOLID = !!(flagsValue & 0x10);
        // 3 bits unused
        this.flags.LHD_LARGE = !!(flagsValue & 0x100);
        this.flags.LHD_UNICODE = !!(flagsValue & 0x200);
        this.flags.LHD_SALT = !!(flagsValue & 0x400);
        this.flags.LHD_VERSION = !!(flagsValue & 0x800);
        this.flags.LHD_EXTTIME = !!(flagsValue & 0x1000);
        this.flags.LHD_EXTFLAGS = !!(flagsValue & 0x2000);
        // 2 bits unused
        //info('  LHD_SPLIT_BEFORE = ' + this.flags.LHD_SPLIT_BEFORE);
        break;
      default:
        break;
    }

    // byte 6,7
    this.headSize = bstream.readNumber(2);
    headBytesRead += 7;

    switch (this.headType) {
      case MAIN_HEAD:
        this.highPosAv = bstream.readNumber(2);
        this.posAv = bstream.readNumber(4);
        headBytesRead += 6;
        if (this.flags.MHD_ENCRYPTVER) {
          this.encryptVer = bstream.readNumber(1);
          headBytesRead += 1;
        }
        //info('Found MAIN_HEAD with highPosAv=' + this.highPosAv + ', posAv=' + this.posAv);
        break;
      case FILE_HEAD:
        this.packSize = bstream.readNumber(4);
        this.unpackedSize = bstream.readNumber(4);
        this.hostOS = bstream.readNumber(1);
        this.fileCRC = bstream.readNumber(4);
        this.fileTime = bstream.readNumber(4);
        this.unpVer = bstream.readNumber(1);
        this.method = bstream.readNumber(1);
        this.nameSize = bstream.readNumber(2);
        this.fileAttr = bstream.readNumber(4);
        headBytesRead += 25;
        
        if (this.flags.LHD_LARGE) {
          //info('Warning: Reading in LHD_LARGE 64-bit size values');
          this.HighPackSize = bstream.readNumber(4);
          this.HighUnpSize = bstream.readNumber(4);
          headBytesRead += 8;
        } else {
          this.HighPackSize = 0;
          this.HighUnpSize = 0;
          if (this.unpackedSize == 0xffffffff) {
            this.HighUnpSize = 0x7fffffff
            this.unpackedSize = 0xffffffff;
          }
        }
        this.fullPackSize = 0;
        this.fullUnpackSize = 0;
        this.fullPackSize |= this.HighPackSize;
        this.fullPackSize <<= 32;
        this.fullPackSize |= this.packSize;

        // read in filename

        // TODO: Use readString?
        this.filename = bstream.readBytes(this.nameSize);
        headBytesRead += this.nameSize;
        let _s = '';
        for (let _i = 0; _i < this.filename.length; _i++) {
          _s += String.fromCharCode(this.filename[_i]);
        }

        this.filename = _s;

        if (this.flags.LHD_SALT) {
          //info('Warning: Reading in 64-bit salt value');
          this.salt = bstream.readBytes(8); // 8 bytes
          headBytesRead += 8;
        }

        if (this.flags.LHD_EXTTIME) {
          // 16-bit flags
          const extTimeFlags = bstream.readNumber(2);
          headBytesRead += 2;

          // this is adapted straight out of arcread.cpp, Archive::ReadHeader()
          for (let I = 0; I < 4; ++I) {
            const rmode = extTimeFlags >> ((3 - I) * 4);
            if ((rmode & 8) == 0) {
              continue;
            }
            if (I != 0) {
              bstream.readBytes(2);
              headBytesRead += 2;
            }
            const count = (rmode & 3);
            for (let J = 0; J < count; ++J) {
              bstream.readNumber(1);
              headBytesRead += 1;
            }
          }
        }

        if (this.flags.LHD_COMMENT) {
          //info('Found a LHD_COMMENT');
        }

        if (headBytesRead < this.headSize) {
          bstream.readBytes(this.headSize - headBytesRead);
        }

        break;
      case ENDARC_HEAD:
        break;
      default:
        if (logToConsole) {
          info('Found a header of type 0x' + byteValueToHexString(this.headType));
        }
        // skip the rest of the header bytes (for now)
        bstream.readBytes(this.headSize - 7);
        break;
    }
  }

  dump() {
    info('  crc=' + this.crc);
    info('  headType=' + this.headType);
    info('  flags=' + twoByteValueToHexString(this.flags.value));
    info('  headSize=' + this.headSize);
    if (this.headType == FILE_HEAD) {
      info('Found FILE_HEAD with packSize=' + this.packSize + ', unpackedSize= ' +
          this.unpackedSize + ', hostOS=' + this.hostOS + ', unpVer=' + this.unpVer + ', method=' +
          this.method + ', filename=' + this.filename);
    }
  }
}

const BLOCK_LZ = 0;
const BLOCK_PPM = 1;

const rLDecode = [0,1,2,3,4,5,6,7,8,10,12,14,16,20,24,28,32,40,48,56,64,80,96,112,128,160,192,224];
const rLBits = [0,0,0,0,0,0,0,0,1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4,  4,  5,  5,  5,  5];
const rDBitLengthCounts = [4,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,14,0,12];
const rSDDecode = [0,4,8,16,32,64,128,192];
const rSDBits = [2,2,3, 4, 5, 6,  6,  6];
  
const rDDecode = [0, 1, 2, 3, 4, 6, 8, 12, 16, 24, 32,
			48, 64, 96, 128, 192, 256, 384, 512, 768, 1024, 1536, 2048, 3072,
			4096, 6144, 8192, 12288, 16384, 24576, 32768, 49152, 65536, 98304,
			131072, 196608, 262144, 327680, 393216, 458752, 524288, 589824,
			655360, 720896, 786432, 851968, 917504, 983040];

const rDBits = [0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5,
			5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14,
			15, 15, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16];

const rLOW_DIST_REP_COUNT = 16;

const rNC = 299;
const rDC = 60;
const rLDC = 17;
const rRC = 28;
const rBC = 20;
const rHUFF_TABLE_SIZE = (rNC+rDC+rRC+rLDC);

const UnpOldTable = new Array(rHUFF_TABLE_SIZE);

const BD = { //bitdecode
  DecodeLen: new Array(16),
  DecodePos: new Array(16),
  DecodeNum: new Array(rBC)
};
const LD = { //litdecode
  DecodeLen: new Array(16),
  DecodePos: new Array(16),
  DecodeNum: new Array(rNC)
};
const DD = { //distdecode
  DecodeLen: new Array(16),
  DecodePos: new Array(16),
  DecodeNum: new Array(rDC)
};
const LDD = { //low dist decode
  DecodeLen: new Array(16),
  DecodePos: new Array(16),
  DecodeNum: new Array(rLDC)
};
const RD = { //rep decode
  DecodeLen: new Array(16),
  DecodePos: new Array(16),
  DecodeNum: new Array(rRC)
};

/**
 * @type {Array<bitjs.io.ByteBuffer>}
 */
const rOldBuffers = [];

/**
 * The current buffer we are unpacking to.
 * @type {bitjs.io.ByteBuffer}
 */
let rBuffer;

/**
 * The buffer of the final bytes after filtering (only used in Unpack29).
 * @type {bitjs.io.ByteBuffer}
 */
let wBuffer;


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
function RarReadTables(bstream) {
  const BitLength = new Array(rBC);
  const Table = new Array(rHUFF_TABLE_SIZE);

  // before we start anything we need to get byte-aligned
  bstream.readBits( (8 - bstream.bitPtr) & 0x7 );
  
  if (bstream.readBits(1)) {
    info('Error!  PPM not implemented yet');
    return;
  }
  
  if (!bstream.readBits(1)) { //discard old table
    for (let i = UnpOldTable.length; i--;) {
      UnpOldTable[i] = 0;
    }
  }

  // read in bit lengths
  for (let I = 0; I < rBC; ++I) {
    const Length = bstream.readBits(4);
    if (Length == 15) {
      let ZeroCount = bstream.readBits(4);
      if (ZeroCount == 0) {
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

  RarMakeDecodeTables(BitLength, 0, BD, rBC);
  
  const TableSize = rHUFF_TABLE_SIZE;
  for (let i = 0; i < TableSize;) {
    const num = RarDecodeNumber(bstream, BD);
    if (num < 16) {
      Table[i] = (num + UnpOldTable[i]) & 0xf;
      i++;
    } else if (num < 18) {
      let N = (num == 16) ? (bstream.readBits(3) + 3) : (bstream.readBits(7) + 11);

      while (N-- > 0 && i < TableSize) {
        Table[i] = Table[i - 1];
        i++;
      }
    } else {
      let N = (num == 18) ? (bstream.readBits(3) + 3) : (bstream.readBits(7) + 11);

      while (N-- > 0 && i < TableSize) {
        Table[i++] = 0;
      }
    }
  }
  
  RarMakeDecodeTables(Table, 0, LD, rNC);
  RarMakeDecodeTables(Table, rNC, DD, rDC);
  RarMakeDecodeTables(Table, rNC + rDC, LDD, rLDC);
  RarMakeDecodeTables(Table, rNC + rDC + rLDC, RD, rRC);  
  
  for (let i = UnpOldTable.length; i--;) {
    UnpOldTable[i] = Table[i];
  }
  return true;
}


function RarDecodeNumber(bstream, dec) {
  const DecodeLen = dec.DecodeLen;
  const DecodePos = dec.DecodePos;
  const DecodeNum = dec.DecodeNum;
  const bitField = bstream.getBits() & 0xfffe;
  //some sort of rolled out binary search
  const bits = ((bitField < DecodeLen[8])?
    ((bitField < DecodeLen[4])?
      ((bitField < DecodeLen[2])?
        ((bitField < DecodeLen[1])?1:2)
       :((bitField < DecodeLen[3])?3:4))
     :(bitField < DecodeLen[6])?
        ((bitField < DecodeLen[5])?5:6)
        :((bitField < DecodeLen[7])?7:8))
    :((bitField < DecodeLen[12])?
      ((bitField < DecodeLen[10])?
        ((bitField < DecodeLen[9])?9:10)
       :((bitField < DecodeLen[11])?11:12))
     :(bitField < DecodeLen[14])?
        ((bitField < DecodeLen[13])?13:14)
        :15));
  bstream.readBits(bits);
  const N = DecodePos[bits] + ((bitField - DecodeLen[bits -1]) >>> (16 - bits));
  
  return DecodeNum[N];
}


function RarMakeDecodeTables(BitLength, offset, dec, size) {
  const DecodeLen = dec.DecodeLen;
  const DecodePos = dec.DecodePos;
  const DecodeNum = dec.DecodeNum;
  const LenCount = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0];
  const TmpPos = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0];
  let N = 0;
  let M = 0;

  for (let i = DecodeNum.length; i--;) {
    DecodeNum[i] = 0;
  }
  for (let i = 0; i < size; i++) {
    LenCount[BitLength[i + offset] & 0xF]++;
  }
  LenCount[0] = 0;
  TmpPos[0] = 0;
  DecodePos[0] = 0;
  DecodeLen[0] = 0;
  
  for (let I = 1; I < 16; ++I) {
    N = 2 * (N+LenCount[I]);
    M = (N << (15-I));
    if (M > 0xFFFF) {
      M = 0xFFFF;
    }
    DecodeLen[I] = M;
    DecodePos[I] = DecodePos[I-1] + LenCount[I-1];
    TmpPos[I] = DecodePos[I];
  }
  for (let I = 0; I < size; ++I) {
    if (BitLength[I + offset] != 0) {
      DecodeNum[ TmpPos[ BitLength[offset + I] & 0xF ]++] = I;
    }
  }

}

// TODO: implement
/**
 * @param {bitjs.io.BitStream} bstream
 * @param {boolean} Solid
 */
function Unpack15(bstream, Solid) {
  info('ERROR!  RAR 1.5 compression not supported');
}

/**
 * Unpacks the bit stream into rBuffer using the Unpack20 algorithm.
 * @param {bitjs.io.BitStream} bstream
 * @param {boolean} Solid
 */
function Unpack20(bstream, Solid) {
  const destUnpSize = rBuffer.data.length;
  let oldDistPtr = 0;

  if (!Solid) {
    RarReadTables20(bstream);
  }
  while (destUnpSize > rBuffer.ptr) {
    let num = RarDecodeNumber(bstream, LD);
    if (num < 256) {
      rBuffer.insertByte(num);
      continue;
    }
    if (num > 269) {
      let Length = rLDecode[num -= 270] + 3;
      if ((Bits = rLBits[num]) > 0) {
        Length += bstream.readBits(Bits);
      }
      let DistNumber = RarDecodeNumber(bstream, DD);
      let Distance = rDDecode[DistNumber] + 1;
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
      RarCopyString(Length, Distance);
      continue;
    }
    if (num == 269) {
      RarReadTables20(bstream);
      RarUpdateProgress();
      continue;
    }
    if (num == 256) {
      lastDist = rOldDist[oldDistPtr++ & 3] = lastDist;
      RarCopyString(lastLength, lastDist);
      continue;
    }
    if (num < 261) {
      const Distance = rOldDist[(oldDistPtr - (num - 256)) & 3];
      const LengthNumber = RarDecodeNumber(bstream, RD);
      let Length = rLDecode[LengthNumber] +2;
      if ((Bits = rLBits[LengthNumber]) > 0) {
        Length += bstream.readBits(Bits);
      }
      if (Distance >= 0x101) {
        Length++;
        if (Distance >= 0x2000) {
          Length++
          if (Distance >= 0x40000) {
            Length++;
          }
        }
      }
      lastLength = Length;
      lastDist = rOldDist[oldDistPtr++ & 3] = Distance;
      RarCopyString(Length, Distance);
      continue;
    }
    if (num < 270) {
      let Distance = rSDDecode[num -= 261] + 1;
      if ((Bits = rSDBits[num]) > 0) {
        Distance += bstream.readBits(Bits);
      }
      lastLength = 2;
      lastDist = rOldDist[oldDistPtr++ & 3] = Distance;
      RarCopyString(2, Distance);
      continue;
    }
    
  }
  RarUpdateProgress();
}

function RarUpdateProgress() {
  const change = rBuffer.ptr - currentBytesUnarchivedInFile;
  currentBytesUnarchivedInFile = rBuffer.ptr;
  currentBytesUnarchived += change;
  postProgress();
}

const rNC20 = 298;
const rDC20 = 48;
const rRC20 = 28;
const rBC20 = 19;
const rMC20 = 257;

const UnpOldTable20 = new Array(rMC20 * 4);

// TODO: This function should return a boolean value, see unpack20.cpp.
function RarReadTables20(bstream) {
  const BitLength = new Array(rBC20);
  const Table = new Array(rMC20 * 4);
  let TableSize;
  let N;
  let I;
  const AudioBlock = bstream.readBits(1);
  if (!bstream.readBits(1)) {
    for (let i = UnpOldTable20.length; i--;) {
      UnpOldTable20[i] = 0;
    }
  }
  TableSize = rNC20 + rDC20 + rRC20;
  for (I = 0; I < rBC20; I++) {
    BitLength[I] = bstream.readBits(4);
  }
  RarMakeDecodeTables(BitLength, 0, BD, rBC20);
  I = 0;
  while (I < TableSize) {
    const num = RarDecodeNumber(bstream, BD);
    if (num < 16) {
      Table[I] = num + UnpOldTable20[I] & 0xf;
      I++;
    } else if (num == 16) {
      N = bstream.readBits(2) + 3;
      while (N-- > 0 && I < TableSize) {
        Table[I] = Table[I - 1];
        I++;
      }
    } else {
      if (num == 17) {
        N = bstream.readBits(3) + 3;
      } else {
        N = bstream.readBits(7) + 11;
      }
      while (N-- > 0 && I < TableSize) {
        Table[I++] = 0;
      }
    }
  }
  RarMakeDecodeTables(Table, 0, LD, rNC20);
  RarMakeDecodeTables(Table, rNC20, DD, rDC20);
  RarMakeDecodeTables(Table, rNC20 + rDC20, RD, rRC20);
  for (let i = UnpOldTable20.length; i--;) {
    UnpOldTable20[i] = Table[i];
  }
}

let lowDistRepCount = 0;
let prevLowDist = 0;

let rOldDist = [0,0,0,0];
let lastDist;
let lastLength;

// ============================================================================================== //

// Unpack code specific to RarVM
const VM = new RarVM();

/**
 * Filters code, one entry per filter.
 * @type {Array<UnpackFilter>}
 */
let Filters = [];

/**
 * Filters stack, several entrances of same filter are possible.
 * @type {Array<UnpackFilter>}
 */
let PrgStack = [];

/**
 * Lengths of preceding blocks, one length per filter. Used to reduce
 * size required to write block length if lengths are repeating.
 * @type {Array<number>}
 */
let OldFilterLengths = [];

let LastFilter = 0;

function InitFilters() {
  OldFilterLengths = [];
  LastFilter = 0;
  Filters = [];
  PrgStack = [];
}


/**
 * @param {number} firstByte The first byte (flags).
 * @param {Uint8Array} vmCode An array of bytes.
 */
function RarAddVMCode(firstByte, vmCode) {
  VM.init();
  const bstream = new bitjs.io.BitStream(vmCode.buffer, true /* rtl */);

  let filtPos;
  if (firstByte & 0x80) {
    filtPos = RarVM.readData(bstream);
    if (filtPos == 0) {
      InitFilters();
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
  const newFilter = (filtPos == Filters.length);

  // new filter for PrgStack
  const stackFilter = new UnpackFilter();
  let filter = null;
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

  let emptyCount = 0;
  for (let i = 0; i < PrgStack.length; ++i) {
    PrgStack[i - emptyCount] = PrgStack[i];

    if (PrgStack[i] == null) {
      emptyCount++;
    }
    if (emptyCount > 0) {
      PrgStack[i] = null;
    }
  }

  if (emptyCount == 0) {
    PrgStack.push(null); //PrgStack.Add(1);
    emptyCount = 1;
  }

  const stackPos = PrgStack.length - emptyCount;
  PrgStack[stackPos] = stackFilter;
  stackFilter.ExecCount = filter.ExecCount;

  let blockStart = RarVM.readData(bstream);
  if (firstByte & 0x40) {
    blockStart += 258;
  }
  stackFilter.BlockStart = (blockStart + rBuffer.ptr) & MAXWINMASK;

  if (firstByte & 0x20) {
    stackFilter.BlockLength = RarVM.readData(bstream);
  } else {
    stackFilter.BlockLength = filtPos < OldFilterLengths.length
        ? OldFilterLengths[filtPos]
        : 0;
  }
  stackFilter.NextWindow = (wBuffer.ptr != rBuffer.ptr) &&
      (((wBuffer.ptr - rBuffer.ptr) & MAXWINMASK) <= blockStart);

  OldFilterLengths[filtPos] = stackFilter.BlockLength;

  for (let i = 0; i < 7; ++i) {
    stackFilter.Prg.InitR[i] = 0;
  }
  stackFilter.Prg.InitR[3] = VM_GLOBALMEMADDR;
  stackFilter.Prg.InitR[4] = stackFilter.BlockLength;
  stackFilter.Prg.InitR[5] = stackFilter.ExecCount;

  // set registers to optional parameters if any
  if (firstByte & 0x10) {
    const initMask = bstream.readBits(7);
    for (let i = 0; i < 7; ++i) {
      if (initMask & (1 << i)) {
        stackFilter.Prg.InitR[i] = RarVM.readData(bstream);
      }
    }
  }

  if (newFilter) {
    const vmCodeSize = RarVM.readData(bstream);
    if (vmCodeSize >= 0x10000 || vmCodeSize == 0) {
      return false;
    }
    const vmCode = new Uint8Array(vmCodeSize);
    for (let i = 0; i < vmCodeSize; ++i) {
      //if (Inp.Overflow(3))
      //  return(false);
      vmCode[i] = bstream.readBits(8);
    }
    VM.prepare(vmCode, filter.Prg);
  }
  stackFilter.Prg.Cmd = filter.Prg.Cmd;
  stackFilter.Prg.AltCmd = filter.Prg.Cmd;

  const staticDataSize = filter.Prg.StaticData.length;
  if (staticDataSize > 0 && staticDataSize < VM_GLOBALMEMSIZE) {
    // read statically defined data contained in DB commands
    for (let i = 0; i < staticDataSize; ++i) {
      stackFilter.Prg.StaticData[i] = filter.Prg.StaticData[i];
    }
  }

  if (stackFilter.Prg.GlobalData.length < VM_FIXEDGLOBALSIZE) {
    stackFilter.Prg.GlobalData = new Uint8Array(VM_FIXEDGLOBALSIZE);
  }

  const globalData = stackFilter.Prg.GlobalData;
  for (let i = 0; i < 7; ++i) {
    VM.setLowEndianValue(globalData, stackFilter.Prg.InitR[i], i * 4);
  }

  VM.setLowEndianValue(globalData, stackFilter.BlockLength, 0x1c);
  VM.setLowEndianValue(globalData, 0, 0x20);
  VM.setLowEndianValue(globalData, stackFilter.ExecCount, 0x2c);
  for (let i = 0; i < 16; ++i) {
    globalData[0x30 + i] = 0;
  }

  // put data block passed as parameter if any
  if (firstByte & 8) {
    //if (Inp.Overflow(3))
    //  return(false);
    const dataSize = RarVM.readData(bstream);
    if (dataSize > (VM_GLOBALMEMSIZE - VM_FIXEDGLOBALSIZE)) {
      return false;
    }

    const curSize = stackFilter.Prg.GlobalData.length;
    if (curSize < dataSize + VM_FIXEDGLOBALSIZE) {
      // Resize global data and update the stackFilter and local variable.
      const numBytesToAdd = dataSize + VM_FIXEDGLOBALSIZE - curSize;
      const newGlobalData = new Uint8Array(globalData.length + numBytesToAdd);
      newGlobalData.set(globalData);

      stackFilter.Prg.GlobalData = newGlobalData;
      globalData = newGlobalData;
    }
    //byte *GlobalData=&StackFilter->Prg.GlobalData[VM_FIXEDGLOBALSIZE];
    for (let i = 0; i < dataSize; ++i) {
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
function RarReadVMCode(bstream) {
  const firstByte = bstream.readBits(8);
  let length = (firstByte & 7) + 1;
  if (length == 7) {
    length = bstream.readBits(8) + 7;
  } else if (length == 8) {
    length = bstream.readBits(16);
  }

  // Read all bytes of VM code into an array.
  const vmCode = new Uint8Array(length);
  for (let i = 0; i < length; i++) {
    // Do something here with checking readbuf.
    vmCode[i] = bstream.readBits(8);
  }
  return RarAddVMCode(firstByte, vmCode);
}

/**
 * Unpacks the bit stream into rBuffer using the Unpack29 algorithm.
 * @param {bitjs.io.BitStream} bstream
 * @param {boolean} Solid
 */
function Unpack29(bstream, Solid) {
  // lazy initialize rDDecode and rDBits

  const DDecode = new Array(rDC);
  const DBits = new Array(rDC);
  
  let Dist = 0;
  let BitLength = 0;
  let Slot = 0;
  
  for (let I = 0; I < rDBitLengthCounts.length; I++,BitLength++) {
    for (let J = 0; J < rDBitLengthCounts[I]; J++,Slot++,Dist+=(1<<BitLength)) {
      DDecode[Slot]=Dist;
      DBits[Slot]=BitLength;
    }
  }
  
  let Bits;
  //tablesRead = false;

  rOldDist = [0,0,0,0]
  
  lastDist = 0;
  lastLength = 0;

  for (let i = UnpOldTable.length; i--;) {
    UnpOldTable[i] = 0;
  }
    
  // read in Huffman tables
  RarReadTables(bstream);
 
  while (true) {
    let num = RarDecodeNumber(bstream, LD);
    
    if (num < 256) {
      rBuffer.insertByte(num);
      continue;
    }
    if (num >= 271) {
      let Length = rLDecode[num -= 271] + 3;
      if ((Bits = rLBits[num]) > 0) {
        Length += bstream.readBits(Bits);
      }
      const DistNumber = RarDecodeNumber(bstream, DD);
      let Distance = DDecode[DistNumber] + 1;
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
            const LowDist = RarDecodeNumber(bstream, LDD);
            if (LowDist == 16) {
              lowDistRepCount = rLOW_DIST_REP_COUNT - 1;
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
      RarInsertOldDist(Distance);
      RarInsertLastMatch(Length, Distance);
      RarCopyString(Length, Distance);
      continue;
    }
    if (num == 256) {
      if (!RarReadEndOfBlock(bstream)) {
        break;
      }
      continue;
    }
    if (num == 257) {
      if (!RarReadVMCode(bstream)) {
        break;
      }
      continue;
    }
    if (num == 258) {
      if (lastLength != 0) {
        RarCopyString(lastLength, lastDist);
      }
      continue;
    }
    if (num < 263) {
      const DistNum = num - 259;
      const Distance = rOldDist[DistNum];

      for (let I = DistNum; I > 0; I--) {
        rOldDist[I] = rOldDist[I-1];
      }
      rOldDist[0] = Distance;

      const LengthNumber = RarDecodeNumber(bstream, RD);
      let Length = rLDecode[LengthNumber] + 2;
      if ((Bits = rLBits[LengthNumber]) > 0) {
        Length += bstream.readBits(Bits);
      }
      RarInsertLastMatch(Length, Distance);
      RarCopyString(Length, Distance);
      continue;
    }
    if (num < 272) {
      let Distance = rSDDecode[num -= 263] + 1;
      if ((Bits = rSDBits[num]) > 0) {
        Distance += bstream.readBits(Bits);
      }
      RarInsertOldDist(Distance);
      RarInsertLastMatch(2, Distance);
      RarCopyString(2, Distance);
      continue;
    }
  } // while (true)
  RarUpdateProgress();
  RarWriteBuf();
}

/**
 * Does stuff to the current byte buffer (rBuffer) based on
 * the filters loaded into the RarVM and writes out to wBuffer.
 */
function RarWriteBuf() {
  let writeSize = (rBuffer.ptr & MAXWINMASK);

  for (let i = 0; i < PrgStack.length; ++i) {
    const flt = PrgStack[i];
    if (flt == null) {
      continue;
    }

    if (flt.NextWindow) {
      flt.NextWindow = false;
      continue;
    }

    const blockStart = flt.BlockStart;
    const blockLength = flt.BlockLength;

    // WrittenBorder = wBuffer.ptr
    if (((blockStart - wBuffer.ptr) & MAXWINMASK) < writeSize) {
      if (wBuffer.ptr != blockStart) {
        // Copy blockStart bytes from rBuffer into wBuffer.
        RarWriteArea(wBuffer.ptr, blockStart);
        writeSize = (rBuffer.ptr - wBuffer.ptr) & MAXWINMASK;
      }
      if (blockLength <= writeSize) {
        const blockEnd = (blockStart + blockLength) & MAXWINMASK;
        if (blockStart < blockEnd || blockEnd == 0) {
          VM.setMemory(0, rBuffer.data.subarray(blockStart, blockStart + blockLength), blockLength);
        } else {
          const firstPartLength = MAXWINSIZE - blockStart;
          VM.setMemory(0, rBuffer.data.subarray(blockStart, blockStart + firstPartLength), firstPartLength);
          VM.setMemory(firstPartLength, rBuffer.data, blockEnd);
        }

        const parentPrg = Filters[flt.ParentFilter].Prg;
        const prg = flt.Prg;

        if (parentPrg.GlobalData.length > VM_FIXEDGLOBALSIZE) {
          // Copy global data from previous script execution if any.
          prg.GlobalData = new Uint8Array(parentPrg.GlobalData);
        }

        RarExecuteCode(prg);

        if (prg.GlobalData.length > VM_FIXEDGLOBALSIZE) {
          // Save global data for next script execution.
          const globalDataLen = prg.GlobalData.length;
          if (parentPrg.GlobalData.length < globalDataLen) {
            parentPrg.GlobalData = new Uint8Array(globalDataLen);
          }
          parentPrg.GlobalData.set(
              this.mem_.subarray(VM_FIXEDGLOBALSIZE, VM_FIXEDGLOBALSIZE + globalDataLen),
              VM_FIXEDGLOBALSIZE);
        } else {
          parentPrg.GlobalData = new Uint8Array(0);
        }

        let filteredData = prg.FilteredData;

        PrgStack[i] = null;
        while (i + 1 < PrgStack.length) {
          const nextFilter = PrgStack[i + 1];
          if (nextFilter == null || nextFilter.BlockStart != blockStart ||
              nextFilter.BlockLength != filteredData.length || nextFilter.NextWindow) {
            break;
          }

          // Apply several filters to same data block.

          VM.setMemory(0, filteredData, filteredData.length);

          const innerParentPrg = Filters[nextFilter.ParentFilter].Prg;
          const nextPrg = nextFilter.Prg;

          const globalDataLen = innerParentPrg.GlobalData.length;
          if (globalDataLen > VM_FIXEDGLOBALSIZE) {
            // Copy global data from previous script execution if any.
            nextPrg.GlobalData = new Uint8Array(globalDataLen);
            nextPrg.GlobalData.set(innerParentPrg.GlobalData.subarray(VM_FIXEDGLOBALSIZE, VM_FIXEDGLOBALSIZE + globalDataLen), VM_FIXEDGLOBALSIZE);
          }

          RarExecuteCode(nextPrg);

          if (nextPrg.GlobalData.length > VM_GLOBALMEMSIZE) {
            // Save global data for next script execution.
            const globalDataLen = nextPrg.GlobalData.length;
            if (innerParentPrg.GlobalData.length < globalDataLen) {
              innerParentPrg.GlobalData = new Uint8Array(globalDataLen);
            }
            innerParentPrg.GlobalData.set(
                this.mem_.subarray(VM_FIXEDGLOBALSIZE, VM_FIXEDGLOBALSIZE + globalDataLen),
                VM_FIXEDGLOBALSIZE);
          } else {
            innerParentPrg.GlobalData = new Uint8Array(0);
          }

          filteredData = nextPrg.FilteredData;
          i++;
          PrgStack[i] = null;
        } // while (i + 1 < PrgStack.length)

        for (let j = 0; j < filteredData.length; ++j) {
          wBuffer.insertByte(filteredData[j]);
        }
        writeSize = (rBuffer.ptr - wBuffer.ptr) & MAXWINMASK;
      } // if (blockLength <= writeSize)
      else {
        for (let j = i; j < PrgStack.length; ++j) {
          const theFlt = PrgStack[j];
          if (theFlt != null && theFlt.NextWindow) {
            theFlt.NextWindow = false;
          }
        }
        return;
      }
    } // if (((blockStart - wBuffer.ptr) & MAXWINMASK) < writeSize)
  } // for (let i = 0; i < PrgStack.length; ++i)

  // Write any remaining bytes from rBuffer to wBuffer;
  RarWriteArea(wBuffer.ptr, rBuffer.ptr);

  // Now that the filtered buffer has been written, swap it back to rBuffer.
  rBuffer = wBuffer;
}

/**
 * Copy bytes from rBuffer to wBuffer.
 * @param {number} startPtr The starting point to copy from rBuffer.
 * @param {number} endPtr The ending point to copy from rBuffer.
 */
function RarWriteArea(startPtr, endPtr) {
  if (endPtr < startPtr) {
    console.error('endPtr < startPtr, endPtr=' + endPtr + ', startPtr=' + startPtr);
//    RarWriteData(startPtr, -(int)StartPtr & MAXWINMASK);
//    RarWriteData(0, endPtr);
    return;
  } else if (startPtr < endPtr) {
    RarWriteData(startPtr, endPtr - startPtr);
  }
}

/**
 * Writes bytes into wBuffer from rBuffer.
 * @param {number} offset The starting point to copy bytes from rBuffer.
 * @param {number} numBytes The number of bytes to copy.
 */
function RarWriteData(offset, numBytes) {
  if (wBuffer.ptr >= rBuffer.data.length) {
    return;
  }
  const leftToWrite = rBuffer.data.length - wBuffer.ptr;
  if (numBytes > leftToWrite) {
    numBytes = leftToWrite;
  }
  for (let i = 0; i < numBytes; ++i) {
    wBuffer.insertByte(rBuffer.data[offset + i]);
  }
}

/**
 * @param {VM_PreparedProgram} prg
 */
function RarExecuteCode(prg)
{
  if (prg.GlobalData.length > 0) {
    const writtenFileSize = wBuffer.ptr;
    prg.InitR[6] = writtenFileSize;
    VM.setLowEndianValue(prg.GlobalData, writtenFileSize, 0x24);
    VM.setLowEndianValue(prg.GlobalData, (writtenFileSize >>> 32) >> 0, 0x28);
    VM.execute(prg);
  }
}

function RarReadEndOfBlock(bstream) {
  RarUpdateProgress();

  let NewTable = false;
  let NewFile = false;
  if (bstream.readBits(1)) {
    NewTable = true;
  } else {
    NewFile = true;
    NewTable = !!bstream.readBits(1);
  }
  //tablesRead = !NewTable;
  return !(NewFile || NewTable && !RarReadTables(bstream));
}

function RarInsertLastMatch(length, distance) {
  lastDist = distance;
  lastLength = length;
}

function RarInsertOldDist(distance) {
  rOldDist.splice(3,1);
  rOldDist.splice(0,0,distance);
}

/**
 * Copies len bytes from distance bytes ago in the buffer to the end of the
 * current byte buffer.
 * @param {number} length How many bytes to copy.
 * @param {number} distance How far back in the buffer from the current write
 *     pointer to start copying from.
 */
function RarCopyString(len, distance) {
  let srcPtr = rBuffer.ptr - distance;
  // If we need to go back to previous buffers, then seek back.
  if (srcPtr < 0) {
    let l = rOldBuffers.length;
    while (srcPtr < 0) {
      srcPtr = rOldBuffers[--l].data.length + srcPtr;
    }
    // TODO: lets hope that it never needs to read across buffer boundaries
    while (len--) {
      rBuffer.insertByte(rOldBuffers[l].data[srcPtr++]);
    }
  }
  if (len > distance) {
    while (len--) {
      rBuffer.insertByte(rBuffer.data[srcPtr++]);
    }
  } else {
    rBuffer.insertBytes(rBuffer.data.subarray(srcPtr, srcPtr + len));
  }
}

/**
 * @param {RarLocalFile} v
 */
function unpack(v) {
  // TODO: implement what happens when unpVer is < 15
  const Ver = v.header.unpVer <= 15 ? 15 : v.header.unpVer;
  const Solid = v.header.flags.LHD_SOLID;
  const bstream = new bitjs.io.BitStream(v.fileData.buffer, true /* rtl */, v.fileData.byteOffset, v.fileData.byteLength );

  rBuffer = new bitjs.io.ByteBuffer(v.header.unpackedSize);

  if (logToConsole) {
    info('Unpacking ' + v.filename + ' RAR v' + Ver);
  }

  switch (Ver) {
    case 15: // rar 1.5 compression
      Unpack15(bstream, Solid);
      break;
    case 20: // rar 2.x compression
    case 26: // files larger than 2GB
      Unpack20(bstream, Solid);
      break;
    case 29: // rar 3.x compression
    case 36: // alternative hash
      wBuffer = new bitjs.io.ByteBuffer(rBuffer.data.length);
      Unpack29(bstream, Solid);
      break;
  } // switch(method)

  rOldBuffers.push(rBuffer);
  // TODO: clear these old buffers when there's over 4MB of history
  return rBuffer.data;
}

/**
 */
class RarLocalFile {
  /**
   * @param {bitjs.io.ByteStream} bstream
   */
  constructor(bstream) {
    this.header = new RarVolumeHeader(bstream);
    this.filename = this.header.filename;
    
    if (this.header.headType != FILE_HEAD && this.header.headType != ENDARC_HEAD) {
      this.isValid = false;
      info('Error! RAR Volume did not include a FILE_HEAD header ');
    }
    else {
      // read in the compressed data
      this.fileData = null;
      if (this.header.packSize > 0) {
        this.fileData = bstream.readBytes(this.header.packSize);
        this.isValid = true;
      }
    }
  }

  unrar() {
    if (!this.header.flags.LHD_SPLIT_BEFORE) {
      // unstore file
      if (this.header.method == 0x30) {
        if (logToConsole) {
          info('Unstore ' + this.filename);
        }
        this.isValid = true;

        currentBytesUnarchivedInFile += this.fileData.length;
        currentBytesUnarchived += this.fileData.length;

        // Create a new buffer and copy it over.
        const len = this.header.packSize;
        const newBuffer = new bitjs.io.ByteBuffer(len);
        newBuffer.insertBytes(this.fileData);
        this.fileData = newBuffer.data;
      } else {
        this.isValid = true;
        this.fileData = unpack(this);
      }
    }
  }
}

// Reads in the volume and main header.
function unrar_start() {
  let bstream = bytestream.tee();
  const header = new RarVolumeHeader(bstream);
  if (header.crc == 0x6152 && 
      header.headType == 0x72 && 
      header.flags.value == 0x1A21 &&
      header.headSize == 7) {
    if (logToConsole) {
      info('Found RAR signature');
    }

    const mhead = new RarVolumeHeader(bstream);
    if (mhead.headType != MAIN_HEAD) {
      info('Error! RAR did not include a MAIN_HEAD header');
    } else {
      bytestream = bstream.tee();
    }
  }
}

function unrar() {
  let bstream = bytestream.tee();

  let localFile = null;
  do {
    localFile = new RarLocalFile(bstream);
    if (logToConsole) {
      info('RAR localFile isValid=' + localFile.isValid + ', volume packSize=' + localFile.header.packSize);
      localFile.header.dump();
    }

    if (localFile && localFile.isValid && localFile.header.packSize > 0) {
      bytestream = bstream.tee();
      totalUncompressedBytesInArchive += localFile.header.unpackedSize;
      allLocalFiles.push(localFile);

      currentFilename = localFile.header.filename;
      currentBytesUnarchivedInFile = 0;
      localFile.unrar();

      if (localFile.isValid) {
        postMessage(new bitjs.archive.UnarchiveExtractEvent(localFile));
        postProgress();
      }
    } else if (localFile.header.packSize == 0 && localFile.header.unpackedSize == 0) {
      // Skip this file.
      localFile.isValid = true;
    }
  } while (localFile.isValid && bstream.getNumBytesLeft() > 0);

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

    currentFilename = '';
    currentFileNumber = 0;
    currentBytesUnarchivedInFile = 0;
    currentBytesUnarchived = 0;
    totalUncompressedBytesInArchive = 0;
    totalFilesInArchive = 0;
    allLocalFiles = [];
    postMessage(new bitjs.archive.UnarchiveStartEvent());
  } else {
    bytestream.push(bytes);
  }

  if (unarchiveState === UnarchiveState.NOT_STARTED) {
    try {
      unrar_start();
      unarchiveState = UnarchiveState.UNARCHIVING;
    } catch (e) {
      if (typeof e === 'string' && e.startsWith('Error!  Overflowed')) {
        if (logToConsole) {
          console.dir(e);
        }
        // Overrun the buffer.
        unarchiveState = UnarchiveState.WAITING;
        postProgress();
      } else {
        console.error('Found an error while unrarring');
        console.dir(e);
        throw e;
      }
    }
  }

  if (unarchiveState === UnarchiveState.UNARCHIVING ||
      unarchiveState === UnarchiveState.WAITING) {
    try {
      unrar();
      unarchiveState = UnarchiveState.FINISHED;
      postMessage(new bitjs.archive.UnarchiveFinishEvent());
    } catch (e) {
      if (typeof e === 'string' && e.startsWith('Error!  Overflowed')) {
        if (logToConsole) {
          console.dir(e);
        }
        // Overrun the buffer.
        unarchiveState = UnarchiveState.WAITING;
      } else {
        console.error('Found an error while unrarring');
        console.dir(e);
        throw e;
      }
    }
  }
};
