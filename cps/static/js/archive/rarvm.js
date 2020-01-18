/**
 * rarvm.js
 *
 * Licensed under the MIT License
 *
 * Copyright(c) 2017 Google Inc.
 */

/**
 * CRC Implementation.
 */
/* global Uint8Array, Uint32Array, bitjs, DataView, mem */
/* exported MAXWINMASK, UnpackFilter */

function emptyArr(n, v) {
    var arr = [];
    for (var i = 0; i < n; i += 1) {
        arr[i] = v;
    }
    return arr;
}

var CRCTab = emptyArr(256, 0);

function initCRC() {
    for (var i = 0; i < 256; ++i) {
        var c = i;
        for (var j = 0; j < 8; ++j) {
            // Read http://stackoverflow.com/questions/6798111/bitwise-operations-on-32-bit-unsigned-ints
            // for the bitwise operator issue (JS interprets operands as 32-bit signed
            // integers and we need to deal with unsigned ones here).
            c = ((c & 1) ? ((c >>> 1) ^ 0xEDB88320) : (c >>> 1)) >>> 0;
        }
        CRCTab[i] = c;
    }
}

/**
 * @param {number} startCRC
 * @param {Uint8Array} arr
 * @return {number}
 */
function CRC(startCRC, arr) {
    if (CRCTab[1] === 0) {
        initCRC();
    }

    /*
    #if defined(LITTLE_ENDIAN) && defined(PRESENT_INT32) && defined(ALLOW_NOT_ALIGNED_INT)
      while (Size>0 && ((long)Data & 7))
      {
        StartCRC=CRCTab[(byte)(StartCRC^Data[0])]^(StartCRC>>8);
        Size--;
        Data++;
      }
      while (Size>=8)
      {
        StartCRC^=*(uint32 *)Data;
        StartCRC=CRCTab[(byte)StartCRC]^(StartCRC>>8);
        StartCRC=CRCTab[(byte)StartCRC]^(StartCRC>>8);
        StartCRC=CRCTab[(byte)StartCRC]^(StartCRC>>8);
        StartCRC=CRCTab[(byte)StartCRC]^(StartCRC>>8);
        StartCRC^=*(uint32 *)(Data+4);
        StartCRC=CRCTab[(byte)StartCRC]^(StartCRC>>8);
        StartCRC=CRCTab[(byte)StartCRC]^(StartCRC>>8);
        StartCRC=CRCTab[(byte)StartCRC]^(StartCRC>>8);
        StartCRC=CRCTab[(byte)StartCRC]^(StartCRC>>8);
        Data+=8;
        Size-=8;
      }
    #endif
    */

    for (var i = 0; i < arr.length; ++i) {
        var byte = ((startCRC ^ arr[i]) >>> 0) & 0xff;
        startCRC = (CRCTab[byte] ^ (startCRC >>> 8)) >>> 0;
    }

    return startCRC;
}

// ============================================================================================== //


/**
 * RarVM Implementation.
 */
var VM_MEMSIZE = 0x40000;
var VM_MEMMASK = (VM_MEMSIZE - 1);
var VM_GLOBALMEMADDR = 0x3C000;
var VM_GLOBALMEMSIZE = 0x2000;
var VM_FIXEDGLOBALSIZE = 64;
var MAXWINSIZE = 0x400000;
var MAXWINMASK = (MAXWINSIZE - 1);

/**
 */
var VmCommands = {
    VM_MOV: 0,
    VM_CMP: 1,
    VM_ADD: 2,
    VM_SUB: 3,
    VM_JZ: 4,
    VM_JNZ: 5,
    VM_INC: 6,
    VM_DEC: 7,
    VM_JMP: 8,
    VM_XOR: 9,
    VM_AND: 10,
    VM_OR: 11,
    VM_TEST: 12,
    VM_JS: 13,
    VM_JNS: 14,
    VM_JB: 15,
    VM_JBE: 16,
    VM_JA: 17,
    VM_JAE: 18,
    VM_PUSH: 19,
    VM_POP: 20,
    VM_CALL: 21,
    VM_RET: 22,
    VM_NOT: 23,
    VM_SHL: 24,
    VM_SHR: 25,
    VM_SAR: 26,
    VM_NEG: 27,
    VM_PUSHA: 28,
    VM_POPA: 29,
    VM_PUSHF: 30,
    VM_POPF: 31,
    VM_MOVZX: 32,
    VM_MOVSX: 33,
    VM_XCHG: 34,
    VM_MUL: 35,
    VM_DIV: 36,
    VM_ADC: 37,
    VM_SBB: 38,
    VM_PRINT: 39,

    /*
    #ifdef VM_OPTIMIZE
      VM_MOVB, VM_MOVD, VM_CMPB, VM_CMPD,

      VM_ADDB, VM_ADDD, VM_SUBB, VM_SUBD, VM_INCB, VM_INCD, VM_DECB, VM_DECD,
      VM_NEGB, VM_NEGD,
    #endif
    */

    // TODO: This enum value would be much larger if VM_OPTIMIZE.
    VM_STANDARD: 40,
};

/**
 */
var VmStandardFilters = {
    VMSF_NONE: 0,
    VMSF_E8: 1,
    VMSF_E8E9: 2,
    VMSF_ITANIUM: 3,
    VMSF_RGB: 4,
    VMSF_AUDIO: 5,
    VMSF_DELTA: 6,
    VMSF_UPCASE: 7,
};

/**
 */
var VmFlags = {
    VM_FC: 1,
    VM_FZ: 2,
    VM_FS: 0x80000000,
};

/**
 */
var VmOpType = {
    VM_OPREG: 0,
    VM_OPINT: 1,
    VM_OPREGMEM: 2,
    VM_OPNONE: 3,
};

/**
 * Finds the key that maps to a given value in an object.  This function is useful in debugging
 * variables that use the above enums.
 * @param {Object} obj
 * @param {number} val
 * @return {string} The key/enum value as a string.
 */
function findKeyForValue(obj, val) {
    for (var key in obj) {
        if (obj[key] === val) {
            return key;
        }
    }
    return null;
}

function getDebugString(obj, val) {
    var s = "Unknown.";
    if (obj === VmCommands) {
        s = "VmCommands.";
    } else if (obj === VmStandardFilters) {
        s = "VmStandardFilters.";
    } else if (obj === VmFlags) {
        s = "VmOpType.";
    } else if (obj === VmOpType) {
        s = "VmOpType.";
    }

    return s + findKeyForValue(obj, val);
}

/**
 * @struct
 * @constructor
 */
var VmPreparedOperand = function() {
    /** @type {VmOpType} */
    this.Type;

    /** @type {number} */
    this.Data = 0;

    /** @type {number} */
    this.Base = 0;

    // TODO: In C++ this is a uint*
    /** @type {Array<number>} */
    this.Addr = null;
};

/** @return {string} */
VmPreparedOperand.prototype.toString = function() {
    if (this.Type === null) {
        return "Error: Type was null in VmPreparedOperand";
    }
    return "{ " +
        "Type: " + getDebugString(VmOpType, this.Type) +
        ", Data: " + this.Data +
        ", Base: " + this.Base +
        " }";
};

/**
 * @struct
 * @constructor
 */
var VmPreparedCommand = function() {
    /** @type {VmCommands} */
    this.OpCode;

    /** @type {boolean} */
    this.ByteMode = false;

    /** @type {VmPreparedOperand} */
    this.Op1 = new VmPreparedOperand();

    /** @type {VmPreparedOperand} */
    this.Op2 = new VmPreparedOperand();
};

/** @return {string} */
VmPreparedCommand.prototype.toString = function(indent) {
    if (this.OpCode === null) {
        return "Error: OpCode was null in VmPreparedCommand";
    }
    indent = indent || "";
    return indent + "{\n" +
        indent + "  OpCode: " + getDebugString(VmCommands, this.OpCode) + ",\n" +
        indent + "  ByteMode: " + this.ByteMode + ",\n" +
        indent + "  Op1: " + this.Op1.toString() + ",\n" +
        indent + "  Op2: " + this.Op2.toString() + ",\n" +
        indent + "}";
};

/**
 * @struct
 * @constructor
 */
var VmPreparedProgram = function() {
    /** @type {Array<VmPreparedCommand>} */
    this.Cmd = [];

    /** @type {Array<VmPreparedCommand>} */
    this.AltCmd = null;

    /** @type {Uint8Array} */
    this.GlobalData = new Uint8Array();

    /** @type {Uint8Array} */
    this.StaticData = new Uint8Array(); // static data contained in DB operators

    /** @type {Uint32Array} */
    this.InitR = new Uint32Array(7);

    /**
     * A pointer to bytes that have been filtered by a program.
     * @type {Uint8Array}
     */
    this.FilteredData = null;
};

/** @return {string} */
VmPreparedProgram.prototype.toString = function() {
    var s = "{\n  Cmd: [\n";
    for (var i = 0; i < this.Cmd.length; ++i) {
        s += this.Cmd[i].toString("  ") + ",\n";
    }
    s += "],\n";
    // TODO: Dump GlobalData, StaticData, InitR?
    s += " }\n";
    return s;
};

/**
 * @struct
 * @constructor
 */
var UnpackFilter = function() {
    /** @type {number} */
    this.BlockStart = 0;

    /** @type {number} */
    this.BlockLength = 0;

    /** @type {number} */
    this.ExecCount = 0;

    /** @type {boolean} */
    this.NextWindow = false;

    // position of parent filter in Filters array used as prototype for filter
    // in PrgStack array. Not defined for filters in Filters array.
    /** @type {number} */
    this.ParentFilter = null;

    /** @type {VmPreparedProgram} */
    this.Prg = new VmPreparedProgram();
};

var VMCF_OP0 = 0;
var VMCF_OP1 = 1;
var VMCF_OP2 = 2;
var VMCF_OPMASK = 3;
var VMCF_BYTEMODE = 4;
var VMCF_JUMP = 8;
var VMCF_PROC = 16;
var VMCF_USEFLAGS = 32;
var VMCF_CHFLAGS = 64;

var VmCmdFlags = [
    /* VM_MOV   */
    VMCF_OP2 | VMCF_BYTEMODE,
    /* VM_CMP   */
    VMCF_OP2 | VMCF_BYTEMODE | VMCF_CHFLAGS,
    /* VM_ADD   */
    VMCF_OP2 | VMCF_BYTEMODE | VMCF_CHFLAGS,
    /* VM_SUB   */
    VMCF_OP2 | VMCF_BYTEMODE | VMCF_CHFLAGS,
    /* VM_JZ    */
    VMCF_OP1 | VMCF_JUMP | VMCF_USEFLAGS,
    /* VM_JNZ   */
    VMCF_OP1 | VMCF_JUMP | VMCF_USEFLAGS,
    /* VM_INC   */
    VMCF_OP1 | VMCF_BYTEMODE | VMCF_CHFLAGS,
    /* VM_DEC   */
    VMCF_OP1 | VMCF_BYTEMODE | VMCF_CHFLAGS,
    /* VM_JMP   */
    VMCF_OP1 | VMCF_JUMP,
    /* VM_XOR   */
    VMCF_OP2 | VMCF_BYTEMODE | VMCF_CHFLAGS,
    /* VM_AND   */
    VMCF_OP2 | VMCF_BYTEMODE | VMCF_CHFLAGS,
    /* VM_OR    */
    VMCF_OP2 | VMCF_BYTEMODE | VMCF_CHFLAGS,
    /* VM_TEST  */
    VMCF_OP2 | VMCF_BYTEMODE | VMCF_CHFLAGS,
    /* VM_JS    */
    VMCF_OP1 | VMCF_JUMP | VMCF_USEFLAGS,
    /* VM_JNS   */
    VMCF_OP1 | VMCF_JUMP | VMCF_USEFLAGS,
    /* VM_JB    */
    VMCF_OP1 | VMCF_JUMP | VMCF_USEFLAGS,
    /* VM_JBE   */
    VMCF_OP1 | VMCF_JUMP | VMCF_USEFLAGS,
    /* VM_JA    */
    VMCF_OP1 | VMCF_JUMP | VMCF_USEFLAGS,
    /* VM_JAE   */
    VMCF_OP1 | VMCF_JUMP | VMCF_USEFLAGS,
    /* VM_PUSH  */
    VMCF_OP1,
    /* VM_POP   */
    VMCF_OP1,
    /* VM_CALL  */
    VMCF_OP1 | VMCF_PROC,
    /* VM_RET   */
    VMCF_OP0 | VMCF_PROC,
    /* VM_NOT   */
    VMCF_OP1 | VMCF_BYTEMODE,
    /* VM_SHL   */
    VMCF_OP2 | VMCF_BYTEMODE | VMCF_CHFLAGS,
    /* VM_SHR   */
    VMCF_OP2 | VMCF_BYTEMODE | VMCF_CHFLAGS,
    /* VM_SAR   */
    VMCF_OP2 | VMCF_BYTEMODE | VMCF_CHFLAGS,
    /* VM_NEG   */
    VMCF_OP1 | VMCF_BYTEMODE | VMCF_CHFLAGS,
    /* VM_PUSHA */
    VMCF_OP0,
    /* VM_POPA  */
    VMCF_OP0,
    /* VM_PUSHF */
    VMCF_OP0 | VMCF_USEFLAGS,
    /* VM_POPF  */
    VMCF_OP0 | VMCF_CHFLAGS,
    /* VM_MOVZX */
    VMCF_OP2,
    /* VM_MOVSX */
    VMCF_OP2,
    /* VM_XCHG  */
    VMCF_OP2 | VMCF_BYTEMODE,
    /* VM_MUL   */
    VMCF_OP2 | VMCF_BYTEMODE,
    /* VM_DIV   */
    VMCF_OP2 | VMCF_BYTEMODE,
    /* VM_ADC   */
    VMCF_OP2 | VMCF_BYTEMODE | VMCF_USEFLAGS | VMCF_CHFLAGS,
    /* VM_SBB   */
    VMCF_OP2 | VMCF_BYTEMODE | VMCF_USEFLAGS | VMCF_CHFLAGS,
    /* VM_PRINT */
    VMCF_OP0,
];


/**
 * @param {number} length
 * @param {number} crc
 * @param {VmStandardFilters} type
 * @struct
 * @constructor
 */
var StandardFilterSignature = function(length, crc, type) {
    /** @type {number} */
    this.Length = length;

    /** @type {number} */
    this.CRC = crc;

    /** @type {VmStandardFilters} */
    this.Type = type;
};

/**
 * @type {Array<StandardFilterSignature>}
 */
var StdList = [
    new StandardFilterSignature(53, 0xad576887, VmStandardFilters.VMSF_E8),
    new StandardFilterSignature(57, 0x3cd7e57e, VmStandardFilters.VMSF_E8E9),
    new StandardFilterSignature(120, 0x3769893f, VmStandardFilters.VMSF_ITANIUM),
    new StandardFilterSignature(29, 0x0e06077d, VmStandardFilters.VMSF_DELTA),
    new StandardFilterSignature(149, 0x1c2c5dc8, VmStandardFilters.VMSF_RGB),
    new StandardFilterSignature(216, 0xbc85e701, VmStandardFilters.VMSF_AUDIO),
    new StandardFilterSignature(40, 0x46b9c560, VmStandardFilters.VMSF_UPCASE),
];

/**
 * @constructor
 */
var RarVM = function() {
    /** @private {Uint8Array} */
    this.mem_ = null;

    /** @private {Uint32Array<number>} */
    this.R_ = new Uint32Array(8);

    /** @private {number} */
    this.flags_ = 0;
};

/**
 * Initializes the memory of the VM.
 */
RarVM.prototype.init = function() {
    if (!this.mem_) {
        this.mem_ = new Uint8Array(VM_MEMSIZE);
    }
};

/**
 * @param {Uint8Array} code
 * @return {VmStandardFilters}
 */
RarVM.prototype.isStandardFilter = function(code) {
    var codeCRC = (CRC(0xffffffff, code, code.length) ^ 0xffffffff) >>> 0;
    for (var i = 0; i < StdList.length; ++i) {
        if (StdList[i].CRC === codeCRC && StdList[i].Length === code.length) {
            return StdList[i].Type;
        }
    }

    return VmStandardFilters.VMSF_NONE;
};

/**
 * @param {VmPreparedOperand} op
 * @param {boolean} byteMode
 * @param {bitjs.io.BitStream} bstream A rtl bit stream.
 */
RarVM.prototype.decodeArg = function(op, byteMode, bstream) {
    var data = bstream.peekBits(16);
    if (data & 0x8000) {
        op.Type = VmOpType.VM_OPREG; // Operand is register (R[0]..R[7])
        bstream.readBits(1); // 1 flag bit and...
        op.Data = bstream.readBits(3); // ... 3 register number bits
        op.Addr = [this.R_[op.Data]]; // TODO &R[Op.Data] // Register address
    } else {
        if ((data & 0xc000) === 0) {
            op.Type = VmOpType.VM_OPINT; // Operand is integer
            bstream.readBits(2); // 2 flag bits
            if (byteMode) {
                op.Data = bstream.readBits(8); // Byte integer.
            } else {
                op.Data = RarVM.readData(bstream); // 32 bit integer.
            }
        } else {
            // Operand is data addressed by register data, base address or both.
            op.Type = VmOpType.VM_OPREGMEM;
            if ((data & 0x2000) === 0) {
                bstream.readBits(3); // 3 flag bits
                // Base address is zero, just use the address from register.
                op.Data = bstream.readBits(3); // (Data>>10)&7
                op.Addr = [this.R_[op.Data]]; // TODO &R[op.Data]
                op.Base = 0;
            } else {
                bstream.readBits(4); // 4 flag bits
                if ((data & 0x1000) === 0) {
                    // Use both register and base address.
                    op.Data = bstream.readBits(3);
                    op.Addr = [this.R_[op.Data]]; // TODO &R[op.Data]
                } else {
                    // Use base address only. Access memory by fixed address.
                    op.Data = 0;
                }
                op.Base = RarVM.readData(bstream); // Read base address.
            }
        }
    }
};

/**
 * @param {VmPreparedProgram} prg
 */
RarVM.prototype.execute = function(prg) {
    this.R_.set(prg.InitR);

    var globalSize = Math.min(prg.GlobalData.length, VM_GLOBALMEMSIZE);
    if (globalSize) {
        this.mem_.set(prg.GlobalData.subarray(0, globalSize), VM_GLOBALMEMADDR);
    }

    var staticSize = Math.min(prg.StaticData.length, VM_GLOBALMEMSIZE - globalSize);
    if (staticSize) {
        this.mem_.set(prg.StaticData.subarray(0, staticSize), VM_GLOBALMEMADDR + globalSize);
    }

    this.R_[7] = VM_MEMSIZE;
    this.flags_ = 0;

    var preparedCodes = prg.AltCmd ? prg.AltCmd : prg.Cmd;
    if (prg.Cmd.length > 0 && !this.executeCode(preparedCodes)) {
        // Invalid VM program. Let's replace it with 'return' command.
        preparedCodes.OpCode = VmCommands.VM_RET;
    }

    var dataView = new DataView(this.mem_.buffer, VM_GLOBALMEMADDR);
    var newBlockPos = dataView.getUint32(0x20, true /* little endian */ ) & VM_MEMMASK;
    var newBlockSize = dataView.getUint32(0x1c, true /* little endian */ ) & VM_MEMMASK;
    if (newBlockPos + newBlockSize >= VM_MEMSIZE) {
        newBlockPos = newBlockSize = 0;
    }
    prg.FilteredData = this.mem_.subarray(newBlockPos, newBlockPos + newBlockSize);

    prg.GlobalData = new Uint8Array(0);

    var dataSize = Math.min(dataView.getUint32(0x30),
        (VM_GLOBALMEMSIZE - VM_FIXEDGLOBALSIZE));
    if (dataSize !== 0) {
        var len = dataSize + VM_FIXEDGLOBALSIZE;
        prg.GlobalData = new Uint8Array(len);
        prg.GlobalData.set(mem.subarray(VM_GLOBALMEMADDR, VM_GLOBALMEMADDR + len));
    }
};

/**
 * @param {Array<VmPreparedCommand>} preparedCodes
 * @return {boolean}
 */
RarVM.prototype.executeCode = function(preparedCodes) {
    var codeIndex = 0;
    var cmd = preparedCodes[codeIndex];
    // TODO: Why is this an infinite loop instead of just returning
    // when a VM_RET is hit?
    while (1) {
        switch (cmd.OpCode) {
            case VmCommands.VM_RET:
                if (this.R_[7] >= VM_MEMSIZE) {
                    return true;
                }
                //SET_IP(GET_VALUE(false,(uint *)&Mem[R[7] & VM_MEMMASK]));
                this.R_[7] += 4;
                continue;

            case VmCommands.VM_STANDARD:
                this.executeStandardFilter(cmd.Op1.Data);
                break;

            default:
                console.error("RarVM OpCode not supported: " + getDebugString(VmCommands, cmd.OpCode));
                break;
        } // switch (cmd.OpCode)
        codeIndex++;
        cmd = preparedCodes[codeIndex];
    }
};

/**
 * @param {number} filterType
 */
RarVM.prototype.executeStandardFilter = function(filterType) {
    switch (filterType) {
        case VmStandardFilters.VMSF_DELTA:
            var dataSize = this.R_[4];
            var channels = this.R_[0];
            var srcPos = 0;
            var border = dataSize * 2;

            //SET_VALUE(false,&Mem[VM_GLOBALMEMADDR+0x20],DataSize);
            var dataView = new DataView(this.mem_.buffer, VM_GLOBALMEMADDR);
            dataView.setUint32(0x20, dataSize, true /* little endian */ );

            if (dataSize >= VM_GLOBALMEMADDR / 2) {
                break;
            }

            // Bytes from same channels are grouped to continual data blocks,
            // so we need to place them back to their interleaving positions.
            for (var curChannel = 0; curChannel < channels; ++curChannel) {
                var prevByte = 0;
                for (var destPos = dataSize + curChannel; destPos < border; destPos += channels) {
                    prevByte = (prevByte - this.mem_[srcPos++]) & 0xff;
                    this.mem_[destPos] = prevByte;
                }
            }

            break;

        default:
            console.error("RarVM Standard Filter not supported: " + getDebugString(VmStandardFilters, filterType));
            break;
    }
};

/**
 * @param {Uint8Array} code
 * @param {VmPreparedProgram} prg
 */
RarVM.prototype.prepare = function(code, prg) {
    var codeSize = code.length;
    var i;
    var curCmd;

    //InitBitInput();
    //memcpy(InBuf,Code,Min(CodeSize,BitInput::MAX_SIZE));
    var bstream = new bitjs.io.BitStream(code.buffer, true /* rtl */ );

    // Calculate the single byte XOR checksum to check validity of VM code.
    var xorSum = 0;
    for (i = 1; i < codeSize; ++i) {
        xorSum ^= code[i];
    }

    bstream.readBits(8);

    prg.Cmd = []; // TODO: Is this right?  I don't see it being done in rarvm.cpp.

    // VM code is valid if equal.
    if (xorSum === code[0]) {
        var filterType = this.isStandardFilter(code);
        if (filterType !== VmStandardFilters.VMSF_NONE) {
            // VM code is found among standard filters.
            curCmd = new VmPreparedCommand();
            prg.Cmd.push(curCmd);

            curCmd.OpCode = VmCommands.VM_STANDARD;
            curCmd.Op1.Data = filterType;
            // TODO: Addr=&CurCmd->Op1.Data
            curCmd.Op1.Addr = [curCmd.Op1.Data];
            curCmd.Op2.Addr = [null]; // &CurCmd->Op2.Data;
            curCmd.Op1.Type = VmOpType.VM_OPNONE;
            curCmd.Op2.Type = VmOpType.VM_OPNONE;
            codeSize = 0;
        }

        var dataFlag = bstream.readBits(1);

        // Read static data contained in DB operators. This data cannot be
        // changed, it is a part of VM code, not a filter parameter.

        if (dataFlag & 0x8000) {
            var dataSize = RarVM.readData(bstream) + 1;
            // TODO: This accesses the byte pointer of the bstream directly.  Is that ok?
            for (i = 0; i < bstream.bytePtr < codeSize && i < dataSize; ++i) {
                // Append a byte to the program's static data.
                var newStaticData = new Uint8Array(prg.StaticData.length + 1);
                newStaticData.set(prg.StaticData);
                newStaticData[newStaticData.length - 1] = bstream.readBits(8);
                prg.StaticData = newStaticData;
            }
        }

        while (bstream.bytePtr < codeSize) {
            curCmd = new VmPreparedCommand();
            prg.Cmd.push(curCmd); // Prg->Cmd.Add(1)
            var flag = bstream.peekBits(1);
            if (!flag) { // (Data&0x8000)==0
                curCmd.OpCode = bstream.readBits(4);
            } else {
                curCmd.OpCode = (bstream.readBits(6) - 24);
            }

            if (VmCmdFlags[curCmd.OpCode] & VMCF_BYTEMODE) {
                curCmd.ByteMode = (bstream.readBits(1) !== 0);
            } else {
                curCmd.ByteMode = 0;
            }
            curCmd.Op1.Type = VmOpType.VM_OPNONE;
            curCmd.Op2.Type = VmOpType.VM_OPNONE;
            var opNum = (VmCmdFlags[curCmd.OpCode] & VMCF_OPMASK);
            curCmd.Op1.Addr = null;
            curCmd.Op2.Addr = null;
            if (opNum > 0) {
                this.decodeArg(curCmd.Op1, curCmd.ByteMode, bstream); // reading the first operand
                if (opNum === 2) {
                    this.decodeArg(curCmd.Op2, curCmd.ByteMode, bstream); // reading the second operand
                } else {
                    if (curCmd.Op1.Type === VmOpType.VM_OPINT && (VmCmdFlags[curCmd.OpCode] & (VMCF_JUMP | VMCF_PROC))) {
                        // Calculating jump distance.
                        var distance = curCmd.Op1.Data;
                        if (distance >= 256) {
                            distance -= 256;
                        } else {
                            if (distance >= 136) {
                                distance -= 264;
                            } else {
                                if (distance >= 16) {
                                    distance -= 8;
                                } else {
                                    if (distance >= 8) {
                                        distance -= 16;
                                    }
                                }
                            }
                            distance += prg.Cmd.length;
                        }
                        curCmd.Op1.Data = distance;
                    }
                }
            } // if (OpNum>0)
        } // while ((uint)InAddr<CodeSize)
    } // if (XorSum==Code[0])

    curCmd = new VmPreparedCommand();
    prg.Cmd.push(curCmd);
    curCmd.OpCode = VmCommands.VM_RET;
    // TODO: Addr=&CurCmd->Op1.Data
    curCmd.Op1.Addr = [curCmd.Op1.Data];
    curCmd.Op2.Addr = [curCmd.Op2.Data];
    curCmd.Op1.Type = VmOpType.VM_OPNONE;
    curCmd.Op2.Type = VmOpType.VM_OPNONE;

    // If operand 'Addr' field has not been set by DecodeArg calls above,
    // let's set it to point to operand 'Data' field. It is necessary for
    // VM_OPINT type operands (usual integers) or maybe if something was
    // not set properly for other operands. 'Addr' field is required
    // for quicker addressing of operand data.
    for (i = 0; i < prg.Cmd.length; ++i) {
        var cmd = prg.Cmd[i];
        if (cmd.Op1.Addr === null) {
            cmd.Op1.Addr = [cmd.Op1.Data];
        }
        if (cmd.Op2.Addr === null) {
            cmd.Op2.Addr = [cmd.Op2.Data];
        }
    }

    /*
    #ifdef VM_OPTIMIZE
      if (CodeSize!=0)
        Optimize(Prg);
    #endif
      */
};

/**
 * @param {Uint8Array} arr The byte array to set a value in.
 * @param {number} value The unsigned 32-bit value to set.
 * @param {number} offset Offset into arr to start setting the value, defaults to 0.
 */
RarVM.prototype.setLowEndianValue = function(arr, value, offset) {
    var i = offset || 0;
    arr[i] = value & 0xff;
    arr[i + 1] = (value >>> 8) & 0xff;
    arr[i + 2] = (value >>> 16) & 0xff;
    arr[i + 3] = (value >>> 24) & 0xff;
};

/**
 * Sets a number of bytes of the VM memory at the given position from a
 * source buffer of bytes.
 * @param {number} pos The position in the VM memory to start writing to.
 * @param {Uint8Array} buffer The source buffer of bytes.
 * @param {number} dataSize The number of bytes to set.
 */
RarVM.prototype.setMemory = function(pos, buffer, dataSize) {
    if (pos < VM_MEMSIZE) {
        var numBytes = Math.min(dataSize, VM_MEMSIZE - pos);
        for (var i = 0; i < numBytes; ++i) {
            this.mem_[pos + i] = buffer[i];
        }
    }
};

/**
 * Static function that reads in the next set of bits for the VM
 * (might return 4, 8, 16 or 32 bits).
 * @param {bitjs.io.BitStream} bstream A RTL bit stream.
 * @return {number} The value of the bits read.
 */
RarVM.readData = function(bstream) {
    // Read in the first 2 bits.
    var flags = bstream.readBits(2);
    switch (flags) { // Data&0xc000
        // Return the next 4 bits.
        case 0:
            return bstream.readBits(4); // (Data>>10)&0xf

        case 1: // 0x4000
            // 0x3c00 => 0011 1100 0000 0000
            if (bstream.peekBits(4) === 0) { // (Data&0x3c00)==0
                // Skip the 4 zero bits.
                bstream.readBits(4);
                // Read in the next 8 and pad with 1s to 32 bits.
                return (0xffffff00 | bstream.readBits(8)) >>> 0; // ((Data>>2)&0xff)
            }

            // Else, read in the next 8.
            return bstream.readBits(8);

            // Read in the next 16.
        case 2: // 0x8000
            var val = bstream.getBits();
            bstream.readBits(16);
            return val; //bstream.readBits(16);

            // case 3
        default:
            return (bstream.readBits(16) << 16) | bstream.readBits(16);
    }
};

// ============================================================================================== //
