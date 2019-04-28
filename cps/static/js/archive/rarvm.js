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
const CRCTab = new Array(256).fill(0);

// Helper functions between signed and unsigned integers.

/**
 * -1 becomes 0xffffffff
 */
function fromSigned32ToUnsigned32(val) {
  return (val < 0) ? (val += 0x100000000) : val;
}

/**
 * 0xffffffff becomes -1
 */
function fromUnsigned32ToSigned32(val) {
  return (val >= 0x80000000) ? (val -= 0x100000000) : val;
}

/**
 * -1 becomes 0xff
 */
function fromSigned8ToUnsigned8(val) {
  return (val < 0) ? (val += 0x100) : val;
}

/**
 * 0xff becomes -1
 */
function fromUnsigned8ToSigned8(val) {
  return (val >= 0x80) ? (val -= 0x100) : val;
}

function InitCRC() {
  for (let i = 0; i < 256; ++i) {
    let c = i;
    for (let j = 0; j < 8; ++j) {
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
  if (CRCTab[1] == 0) {
    InitCRC();
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

  for (let i = 0; i < arr.length; ++i) {
    const byte = ((startCRC ^ arr[i]) >>> 0) & 0xff;
    startCRC = (CRCTab[byte] ^ (startCRC >>> 8)) >>> 0;
  }

  return startCRC;
}

// ============================================================================================== //


/**
 * RarVM Implementation.
 */
const VM_MEMSIZE = 0x40000;
const VM_MEMMASK = (VM_MEMSIZE - 1);
const VM_GLOBALMEMADDR = 0x3C000;
const VM_GLOBALMEMSIZE = 0x2000;
const VM_FIXEDGLOBALSIZE = 64;
const MAXWINSIZE = 0x400000;
const MAXWINMASK = (MAXWINSIZE - 1);

/**
 */
const VM_Commands = {
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
const VM_StandardFilters = {
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
const VM_Flags = {
  VM_FC: 1,
  VM_FZ: 2,
  VM_FS: 0x80000000,
};

/**
 */
const VM_OpType = {
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
  for (let key in obj) {
    if (obj[key] === val) {
      return key;
    }
  }
  return null;
}

function getDebugString(obj, val) {
  let s = 'Unknown.';
  if (obj === VM_Commands) {
    s = 'VM_Commands.';
  } else if (obj === VM_StandardFilters) {
    s = 'VM_StandardFilters.';
  } else if (obj === VM_Flags) {
    s = 'VM_OpType.';
  } else if (obj === VM_OpType) {
    s = 'VM_OpType.';
  }

  return s + findKeyForValue(obj, val);
}

/**
 */
class VM_PreparedOperand {
  constructor() {
    /** @type {VM_OpType} */
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
  toString() {
    if (this.Type === null) {
      return 'Error: Type was null in VM_PreparedOperand';
    }
    return '{ '
        + 'Type: ' + getDebugString(VM_OpType, this.Type)
        + ', Data: ' + this.Data
        + ', Base: ' + this.Base
        + ' }';
  }
}

/**
 */
class VM_PreparedCommand {
  constructor() {
    /** @type {VM_Commands} */
    this.OpCode;

    /** @type {boolean} */
    this.ByteMode = false;

    /** @type {VM_PreparedOperand} */
    this.Op1 = new VM_PreparedOperand();

    /** @type {VM_PreparedOperand} */
    this.Op2 = new VM_PreparedOperand();
  }

  /** @return {string} */
  toString(indent) {
    if (this.OpCode === null) {
      return 'Error: OpCode was null in VM_PreparedCommand';
    }
    indent = indent || '';
    return indent + '{\n'
        + indent + '  OpCode: ' + getDebugString(VM_Commands, this.OpCode) + ',\n'
        + indent + '  ByteMode: ' + this.ByteMode + ',\n'
        + indent + '  Op1: ' + this.Op1.toString() + ',\n'
        + indent + '  Op2: ' + this.Op2.toString() + ',\n'
        + indent + '}';
  }
}

/**
 */
class VM_PreparedProgram {
  constructor() {
    /** @type {Array<VM_PreparedCommand>} */
    this.Cmd = [];

    /** @type {Array<VM_PreparedCommand>} */
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
  }

  /** @return {string} */
  toString() {
    let s = '{\n  Cmd: [\n';
    for (let i = 0; i < this.Cmd.length; ++i) {
      s += this.Cmd[i].toString('  ') + ',\n';
    }
    s += '],\n';
    // TODO: Dump GlobalData, StaticData, InitR?
    s += ' }\n';
    return s;
  }
}

/**
 */
class UnpackFilter {
  constructor() {
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

    /** @type {VM_PreparedProgram} */
    this.Prg = new VM_PreparedProgram();
  }
}

const VMCF_OP0       =  0;
const VMCF_OP1       =  1;
const VMCF_OP2       =  2;
const VMCF_OPMASK    =  3;
const VMCF_BYTEMODE  =  4;
const VMCF_JUMP      =  8;
const VMCF_PROC      = 16;
const VMCF_USEFLAGS  = 32;
const VMCF_CHFLAGS   = 64;

const VM_CmdFlags = [
  /* VM_MOV   */ VMCF_OP2 | VMCF_BYTEMODE                                ,
  /* VM_CMP   */ VMCF_OP2 | VMCF_BYTEMODE | VMCF_CHFLAGS                 ,
  /* VM_ADD   */ VMCF_OP2 | VMCF_BYTEMODE | VMCF_CHFLAGS                 ,
  /* VM_SUB   */ VMCF_OP2 | VMCF_BYTEMODE | VMCF_CHFLAGS                 ,
  /* VM_JZ    */ VMCF_OP1 | VMCF_JUMP | VMCF_USEFLAGS                    ,
  /* VM_JNZ   */ VMCF_OP1 | VMCF_JUMP | VMCF_USEFLAGS                    ,
  /* VM_INC   */ VMCF_OP1 | VMCF_BYTEMODE | VMCF_CHFLAGS                 ,
  /* VM_DEC   */ VMCF_OP1 | VMCF_BYTEMODE | VMCF_CHFLAGS                 ,
  /* VM_JMP   */ VMCF_OP1 | VMCF_JUMP                                    ,
  /* VM_XOR   */ VMCF_OP2 | VMCF_BYTEMODE | VMCF_CHFLAGS                 ,
  /* VM_AND   */ VMCF_OP2 | VMCF_BYTEMODE | VMCF_CHFLAGS                 ,
  /* VM_OR    */ VMCF_OP2 | VMCF_BYTEMODE | VMCF_CHFLAGS                 ,
  /* VM_TEST  */ VMCF_OP2 | VMCF_BYTEMODE | VMCF_CHFLAGS                 ,
  /* VM_JS    */ VMCF_OP1 | VMCF_JUMP | VMCF_USEFLAGS                    ,
  /* VM_JNS   */ VMCF_OP1 | VMCF_JUMP | VMCF_USEFLAGS                    ,
  /* VM_JB    */ VMCF_OP1 | VMCF_JUMP | VMCF_USEFLAGS                    ,
  /* VM_JBE   */ VMCF_OP1 | VMCF_JUMP | VMCF_USEFLAGS                    ,
  /* VM_JA    */ VMCF_OP1 | VMCF_JUMP | VMCF_USEFLAGS                    ,
  /* VM_JAE   */ VMCF_OP1 | VMCF_JUMP | VMCF_USEFLAGS                    ,
  /* VM_PUSH  */ VMCF_OP1                                                ,
  /* VM_POP   */ VMCF_OP1                                                ,
  /* VM_CALL  */ VMCF_OP1 | VMCF_PROC                                    ,
  /* VM_RET   */ VMCF_OP0 | VMCF_PROC                                    ,
  /* VM_NOT   */ VMCF_OP1 | VMCF_BYTEMODE                                ,
  /* VM_SHL   */ VMCF_OP2 | VMCF_BYTEMODE | VMCF_CHFLAGS                 ,
  /* VM_SHR   */ VMCF_OP2 | VMCF_BYTEMODE | VMCF_CHFLAGS                 ,
  /* VM_SAR   */ VMCF_OP2 | VMCF_BYTEMODE | VMCF_CHFLAGS                 ,
  /* VM_NEG   */ VMCF_OP1 | VMCF_BYTEMODE | VMCF_CHFLAGS                 ,
  /* VM_PUSHA */ VMCF_OP0                                                ,
  /* VM_POPA  */ VMCF_OP0                                                ,
  /* VM_PUSHF */ VMCF_OP0 | VMCF_USEFLAGS                                ,
  /* VM_POPF  */ VMCF_OP0 | VMCF_CHFLAGS                                 ,
  /* VM_MOVZX */ VMCF_OP2                                                ,
  /* VM_MOVSX */ VMCF_OP2                                                ,
  /* VM_XCHG  */ VMCF_OP2 | VMCF_BYTEMODE                                ,
  /* VM_MUL   */ VMCF_OP2 | VMCF_BYTEMODE                                ,
  /* VM_DIV   */ VMCF_OP2 | VMCF_BYTEMODE                                ,
  /* VM_ADC   */ VMCF_OP2 | VMCF_BYTEMODE | VMCF_USEFLAGS | VMCF_CHFLAGS ,
  /* VM_SBB   */ VMCF_OP2 | VMCF_BYTEMODE | VMCF_USEFLAGS | VMCF_CHFLAGS ,
  /* VM_PRINT */ VMCF_OP0                                                ,
];


/**
 */
class StandardFilterSignature {
  /**
   * @param {number} length
   * @param {number} crc
   * @param {VM_StandardFilters} type
   */
  constructor(length, crc, type) {
    /** @type {number} */
    this.Length = length;

    /** @type {number} */
    this.CRC = crc;

    /** @type {VM_StandardFilters} */
    this.Type = type;
  }
}

/**
 * @type {Array<StandardFilterSignature>}
 */
const StdList = [
  new StandardFilterSignature(53, 0xad576887, VM_StandardFilters.VMSF_E8),
  new StandardFilterSignature(57, 0x3cd7e57e, VM_StandardFilters.VMSF_E8E9),
  new StandardFilterSignature(120, 0x3769893f, VM_StandardFilters.VMSF_ITANIUM),
  new StandardFilterSignature(29, 0x0e06077d, VM_StandardFilters.VMSF_DELTA),
  new StandardFilterSignature(149, 0x1c2c5dc8, VM_StandardFilters.VMSF_RGB),
  new StandardFilterSignature(216, 0xbc85e701, VM_StandardFilters.VMSF_AUDIO),
  new StandardFilterSignature(40, 0x46b9c560, VM_StandardFilters.VMSF_UPCASE),
];

/**
 * @constructor
 */
class RarVM {
  constructor() {
    /** @private {Uint8Array} */
    this.mem_ = null;

    /** @private {Uint32Array<number>} */
    this.R_ = new Uint32Array(8);

    /** @private {number} */
    this.flags_ = 0;
  }

  /**
   * Initializes the memory of the VM.
   */
  init() {
    if (!this.mem_) {
      this.mem_ = new Uint8Array(VM_MEMSIZE);
    }
  }

  /**
   * @param {Uint8Array} code
   * @return {VM_StandardFilters}
   */
  isStandardFilter(code) {
    const codeCRC = (CRC(0xffffffff, code, code.length) ^ 0xffffffff) >>> 0;
    for (let i = 0; i < StdList.length; ++i) {
      if (StdList[i].CRC == codeCRC && StdList[i].Length == code.length)
        return StdList[i].Type;
    }

    return VM_StandardFilters.VMSF_NONE;
  }

  /**
   * @param {VM_PreparedOperand} op
   * @param {boolean} byteMode
   * @param {bitjs.io.BitStream} bstream A rtl bit stream.
   */
  decodeArg(op, byteMode, bstream) {
    const data = bstream.peekBits(16);
    if (data & 0x8000) {
      op.Type = VM_OpType.VM_OPREG;        // Operand is register (R[0]..R[7])
      bstream.readBits(1);                 // 1 flag bit and...
      op.Data = bstream.readBits(3);       // ... 3 register number bits
      op.Addr = [this.R_[op.Data]] // TODO &R[Op.Data] // Register address
    } else {
      if ((data & 0xc000) == 0) {
        op.Type = VM_OpType.VM_OPINT; // Operand is integer
        bstream.readBits(2); // 2 flag bits
        if (byteMode) {
          op.Data = bstream.readBits(8);         // Byte integer.
        } else {
          op.Data = RarVM.readData(bstream);     // 32 bit integer.
        }
      } else {
        // Operand is data addressed by register data, base address or both.
        op.Type = VM_OpType.VM_OPREGMEM;
        if ((data & 0x2000) == 0) {
          bstream.readBits(3); // 3 flag bits
          // Base address is zero, just use the address from register.
          op.Data = bstream.readBits(3); // (Data>>10)&7
          op.Addr = [this.R_[op.Data]]; // TODO &R[op.Data]
          op.Base = 0;
        } else {
          bstream.readBits(4); // 4 flag bits
          if ((data & 0x1000) == 0) {
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
  }

  /**
   * @param {VM_PreparedProgram} prg
   */
  execute(prg) {
    this.R_.set(prg.InitR);

    const globalSize = Math.min(prg.GlobalData.length, VM_GLOBALMEMSIZE);
    if (globalSize) {
      this.mem_.set(prg.GlobalData.subarray(0, globalSize), VM_GLOBALMEMADDR);
    }

    const staticSize = Math.min(prg.StaticData.length, VM_GLOBALMEMSIZE - globalSize);
    if (staticSize) {
      this.mem_.set(prg.StaticData.subarray(0, staticSize), VM_GLOBALMEMADDR + globalSize);
    }

    this.R_[7] = VM_MEMSIZE;
    this.flags_ = 0;

    const preparedCodes = prg.AltCmd ? prg.AltCmd : prg.Cmd;
    if (prg.Cmd.length > 0 && !this.executeCode(preparedCodes)) {
      // Invalid VM program. Let's replace it with 'return' command.
      preparedCode.OpCode = VM_Commands.VM_RET;
    }

    const dataView = new DataView(this.mem_.buffer, VM_GLOBALMEMADDR);
    let newBlockPos = dataView.getUint32(0x20, true /* little endian */) & VM_MEMMASK;
    const newBlockSize = dataView.getUint32(0x1c, true /* little endian */) & VM_MEMMASK;
    if (newBlockPos + newBlockSize >= VM_MEMSIZE) {
      newBlockPos = newBlockSize = 0;
    }
    prg.FilteredData = this.mem_.subarray(newBlockPos, newBlockPos + newBlockSize);

    prg.GlobalData = new Uint8Array(0);

    const dataSize = Math.min(dataView.getUint32(0x30), (VM_GLOBALMEMSIZE - VM_FIXEDGLOBALSIZE));
    if (dataSize != 0) {
      const len = dataSize + VM_FIXEDGLOBALSIZE;
      prg.GlobalData = new Uint8Array(len);
      prg.GlobalData.set(mem.subarray(VM_GLOBALMEMADDR, VM_GLOBALMEMADDR + len));
    }
  }

  /**
   * @param {Array<VM_PreparedCommand>} preparedCodes
   * @return {boolean}
   */
  executeCode(preparedCodes) {
    let codeIndex = 0;
    let cmd = preparedCodes[codeIndex];
    // TODO: Why is this an infinite loop instead of just returning
    // when a VM_RET is hit?
    while (1) {
      switch (cmd.OpCode) {
        case VM_Commands.VM_RET:
          if (this.R_[7] >= VM_MEMSIZE) {
            return true;
          }
          //SET_IP(GET_VALUE(false,(uint *)&Mem[R[7] & VM_MEMMASK]));
          this.R_[7] += 4;
          continue;

        case VM_Commands.VM_STANDARD:
          this.executeStandardFilter(cmd.Op1.Data);
          break;

        default:
          console.error('RarVM OpCode not supported: ' + getDebugString(VM_Commands, cmd.OpCode));
          break;
      } // switch (cmd.OpCode)
      codeIndex++;
      cmd = preparedCodes[codeIndex];
    }
  }

  /**
   * @param {number} filterType
   */
  executeStandardFilter(filterType) {
    switch (filterType) {
      case VM_StandardFilters.VMSF_RGB: {
        const dataSize = this.R_[4];
        const width = this.R_[0] - 3;
        const posR = this.R_[1];
        const Channels = 3;
        let srcOffset = 0;
        let destOffset = dataSize;

        // byte *SrcData=Mem,*DestData=SrcData+DataSize;
        // SET_VALUE(false,&Mem[VM_GLOBALMEMADDR+0x20],DataSize);
        const dataView = new DataView(this.mem_.buffer, VM_GLOBALMEMADDR /* offset */);
        dataView.setUint32(0x20 /* byte offset */,
            dataSize /* value */,
            true /* little endian */);

        if (dataSize >= (VM_GLOBALMEMADDR / 2) || posR < 0) {
          break;
        }

        for (let curChannel = 0; curChannel < Channels; ++curChannel) {
          let prevByte=0;

          for (let i = curChannel; i < dataSize; i += Channels) {
            let predicted;
            const upperPos = i - width;
            if (upperPos >= 3) {
              const upperByte = this.mem_[destOffset + upperPos];
              const upperLeftByte = this.mem_[destOffset + upperPos - 3];
              predicted = prevByte + upperByte - upperLeftByte;

              const pa = Math.abs(predicted - prevByte);
              const pb = Math.abs(predicted - upperByte);
              const pc = Math.abs(predicted - upperLeftByte);
              if (pa <= pb && pa <= pc) {
                predicted = prevByte;
              } else if (pb <= pc) {
                predicted = upperByte;
              } else {
                predicted = upperLeftByte;
              }
            } else {
              predicted = prevByte;
            }
            //DestData[I]=PrevByte=(byte)(Predicted-*(SrcData++));
            prevByte = (predicted - this.mem_[srcOffset++]) & 0xff;
            this.mem_[destOffset + i] = prevByte;
          }
        }
        for (let i = posR, border = dataSize - 2; i < border; i += 3) {
          const g = this.mem_[destOffset + i + 1];
          this.mem_[destOffset + i] += g;
          this.mem_[destOffset + i + 2] += g;
        }

        break;
      }

      // The C++ version of this standard filter uses an odd mixture of
      // signed and unsigned integers, bytes and various casts.  Careful!
      case VM_StandardFilters.VMSF_AUDIO: {
        const dataSize = this.R_[4];
        const channels = this.R_[0];
        let srcOffset = 0;
        let destOffset = dataSize;

        //SET_VALUE(false,&Mem[VM_GLOBALMEMADDR+0x20],DataSize);
        const dataView = new DataView(this.mem_.buffer, VM_GLOBALMEMADDR);
        dataView.setUint32(0x20 /* byte offset */,
            dataSize /* value */,
            true /* little endian */);

        if (dataSize >= VM_GLOBALMEMADDR / 2) {
          break;
        }

        for (let curChannel = 0; curChannel < channels; ++curChannel) {
          let prevByte = 0; // uint
          let prevDelta = 0; // uint
          let dif = [0, 0, 0, 0, 0, 0, 0];
          let d1 = 0, d2 = 0, d3; // ints
          let k1 = 0, k2 = 0, k3 = 0; // ints

          for (var i = curChannel, byteCount = 0;
              i < dataSize;
              i += channels, ++byteCount) {
            d3 = d2;
            d2 = fromUnsigned32ToSigned32(prevDelta - d1);
            d1 = fromUnsigned32ToSigned32(prevDelta);

            let predicted = fromSigned32ToUnsigned32(8*prevByte + k1*d1 + k2*d2 + k3*d3); // uint
            predicted = (predicted >>> 3) & 0xff;

            let curByte = this.mem_[srcOffset++]; // uint

            // Predicted-=CurByte;
            predicted = fromSigned32ToUnsigned32(predicted - curByte);
            this.mem_[destOffset + i] = (predicted & 0xff);

            // PrevDelta=(signed char)(Predicted-PrevByte);
            // where Predicted, PrevByte, PrevDelta are all unsigned int (32)
            // casting this subtraction to a (signed char) is kind of invalid
            // but it does the following:
            // - do the subtraction
            // - get the bottom 8 bits of the result
            // - if it was >= 0x80, then the value is negative (subtract 0x100)
            // - if the value is now negative, add 0x100000000 to make unsigned
            //
            // Example:
            //   predicted = 101
            //   prevByte = 4294967158
            //   (predicted - prevByte) = -4294967057
            //   take lower 8 bits:  1110 1111 = 239
            //   since > 127, subtract 256 = -17
            //   since < 0, add 0x100000000 = 4294967279
            prevDelta = fromSigned32ToUnsigned32(
                            fromUnsigned8ToSigned8((predicted - prevByte) & 0xff));
            prevByte = predicted;

            // int D=((signed char)CurByte)<<3;
            let curByteAsSignedChar = fromUnsigned8ToSigned8(curByte); // signed char
            let d = (curByteAsSignedChar << 3);

            dif[0] += Math.abs(d);
            dif[1] += Math.abs(d-d1);
            dif[2] += Math.abs(d+d1);
            dif[3] += Math.abs(d-d2);
            dif[4] += Math.abs(d+d2);
            dif[5] += Math.abs(d-d3);
            dif[6] += Math.abs(d+d3);

            if ((byteCount & 0x1f) == 0) {
              let minDif = dif[0], numMinDif = 0;
              dif[0] = 0;
              for (let j = 1; j < 7; ++j) {
                if (dif[j] < minDif) {
                  minDif = dif[j];
                  numMinDif = j;
                }
                dif[j] = 0;
              }
              switch (numMinDif) {
                case 1: if (k1>=-16) k1--; break;
                case 2: if (k1 < 16) k1++; break;
                case 3: if (k2>=-16) k2--; break;
                case 4: if (k2 < 16) k2++; break;
                case 5: if (k3>=-16) k3--; break;
                case 6: if (k3 < 16) k3++; break;
              }
            }
          }
        }

        break;
      }

      case VM_StandardFilters.VMSF_DELTA: {
        const dataSize = this.R_[4];
        const channels = this.R_[0];
        let srcPos = 0;
        const border = dataSize * 2;

        //SET_VALUE(false,&Mem[VM_GLOBALMEMADDR+0x20],DataSize);
        const dataView = new DataView(this.mem_.buffer, VM_GLOBALMEMADDR);
        dataView.setUint32(0x20 /* byte offset */,
            dataSize /* value */,
            true /* little endian */);

        if (dataSize >= VM_GLOBALMEMADDR / 2) {
          break;
        }

        // Bytes from same channels are grouped to continual data blocks,
        // so we need to place them back to their interleaving positions.
        for (let curChannel = 0; curChannel < channels; ++curChannel) {
          let prevByte = 0;
          for (let destPos = dataSize + curChannel; destPos < border; destPos += channels) {
            prevByte = (prevByte - this.mem_[srcPos++]) & 0xff;
            this.mem_[destPos] = prevByte;
          }
        }

        break;
      }

      default:
        console.error('RarVM Standard Filter not supported: ' + getDebugString(VM_StandardFilters, filterType));
        break;
    }
  }

  /**
   * @param {Uint8Array} code
   * @param {VM_PreparedProgram} prg
   */
  prepare(code, prg) {
    let codeSize = code.length;

    //InitBitInput();
    //memcpy(InBuf,Code,Min(CodeSize,BitInput::MAX_SIZE));
    const bstream = new bitjs.io.BitStream(code.buffer, true /* rtl */);

    // Calculate the single byte XOR checksum to check validity of VM code.
    let xorSum = 0;
    for (let i = 1; i < codeSize; ++i) {
      xorSum ^= code[i];
    }

    bstream.readBits(8);

    prg.Cmd = [];  // TODO: Is this right?  I don't see it being done in rarvm.cpp.

    // VM code is valid if equal.
    if (xorSum == code[0]) {
      const filterType = this.isStandardFilter(code);
      if (filterType != VM_StandardFilters.VMSF_NONE) {
        // VM code is found among standard filters.
        const curCmd = new VM_PreparedCommand();
        prg.Cmd.push(curCmd);

        curCmd.OpCode = VM_Commands.VM_STANDARD;
        curCmd.Op1.Data = filterType;
        // TODO: Addr=&CurCmd->Op1.Data
        curCmd.Op1.Addr = [curCmd.Op1.Data];
        curCmd.Op2.Addr = [null]; // &CurCmd->Op2.Data;
        curCmd.Op1.Type = VM_OpType.VM_OPNONE;
        curCmd.Op2.Type = VM_OpType.VM_OPNONE;
        codeSize = 0;
      }

      const dataFlag = bstream.readBits(1);

      // Read static data contained in DB operators. This data cannot be
      // changed, it is a part of VM code, not a filter parameter.

      if (dataFlag & 0x8000) {
        const dataSize = RarVM.readData(bstream) + 1;
        // TODO: This accesses the byte pointer of the bstream directly.  Is that ok?
        for (let i = 0; i < bstream.bytePtr < codeSize && i < dataSize; ++i) {
          // Append a byte to the program's static data.
          const newStaticData = new Uint8Array(prg.StaticData.length + 1);
          newStaticData.set(prg.StaticData);
          newStaticData[newStaticData.length - 1] = bstream.readBits(8);
          prg.StaticData = newStaticData;
        }
      }

      while (bstream.bytePtr < codeSize) {
        const curCmd = new VM_PreparedCommand();
        prg.Cmd.push(curCmd); // Prg->Cmd.Add(1)
        const flag = bstream.peekBits(1);
        if (!flag) { // (Data&0x8000)==0
          curCmd.OpCode = bstream.readBits(4);
        } else {
          curCmd.OpCode = (bstream.readBits(6) - 24);
        }

        if (VM_CmdFlags[curCmd.OpCode] & VMCF_BYTEMODE) {
          curCmd.ByteMode = (bstream.readBits(1) != 0);
        } else {
          curCmd.ByteMode = 0;
        }
        curCmd.Op1.Type = VM_OpType.VM_OPNONE;
        curCmd.Op2.Type = VM_OpType.VM_OPNONE;
        const opNum = (VM_CmdFlags[curCmd.OpCode] & VMCF_OPMASK);
        curCmd.Op1.Addr = null;
        curCmd.Op2.Addr = null;
        if (opNum > 0) {
          this.decodeArg(curCmd.Op1, curCmd.ByteMode, bstream); // reading the first operand
          if (opNum == 2) {
            this.decodeArg(curCmd.Op2, curCmd.ByteMode, bstream); // reading the second operand
          } else {
            if (curCmd.Op1.Type == VM_OpType.VM_OPINT && (VM_CmdFlags[curCmd.OpCode] & (VMCF_JUMP|VMCF_PROC))) {
              // Calculating jump distance.
              let distance = curCmd.Op1.Data;
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

    const curCmd = new VM_PreparedCommand();
    prg.Cmd.push(curCmd);
    curCmd.OpCode = VM_Commands.VM_RET;
    // TODO: Addr=&CurCmd->Op1.Data
    curCmd.Op1.Addr = [curCmd.Op1.Data];
    curCmd.Op2.Addr = [curCmd.Op2.Data];
    curCmd.Op1.Type = VM_OpType.VM_OPNONE;
    curCmd.Op2.Type = VM_OpType.VM_OPNONE;

    // If operand 'Addr' field has not been set by DecodeArg calls above,
    // let's set it to point to operand 'Data' field. It is necessary for
    // VM_OPINT type operands (usual integers) or maybe if something was
    // not set properly for other operands. 'Addr' field is required
    // for quicker addressing of operand data.
    for (let i = 0; i < prg.Cmd.length; ++i) {
      const cmd = prg.Cmd[i];
      if (cmd.Op1.Addr == null) {
        cmd.Op1.Addr = [cmd.Op1.Data];
      }
      if (cmd.Op2.Addr == null) {
        cmd.Op2.Addr = [cmd.Op2.Data];
      }
    }

  /*
  #ifdef VM_OPTIMIZE
    if (CodeSize!=0)
      Optimize(Prg);
  #endif
    */
  }

  /**
   * @param {Uint8Array} arr The byte array to set a value in.
   * @param {number} value The unsigned 32-bit value to set.
   * @param {number} offset Offset into arr to start setting the value, defaults to 0.
   */
  setLowEndianValue(arr, value, offset) {
    const i = offset || 0;
    arr[i]     = value & 0xff;
    arr[i + 1] = (value >>> 8) & 0xff;
    arr[i + 2] = (value >>> 16) & 0xff;
    arr[i + 3] = (value >>> 24) & 0xff;
  }

  /**
   * Sets a number of bytes of the VM memory at the given position from a
   * source buffer of bytes.
   * @param {number} pos The position in the VM memory to start writing to.
   * @param {Uint8Array} buffer The source buffer of bytes.
   * @param {number} dataSize The number of bytes to set.
   */
  setMemory(pos, buffer, dataSize) {
    if (pos < VM_MEMSIZE) {
      const numBytes = Math.min(dataSize, VM_MEMSIZE - pos);
      for (let i = 0; i < numBytes; ++i) {
        this.mem_[pos + i] = buffer[i];
      }
    }
  }

  /**
   * Static function that reads in the next set of bits for the VM
   * (might return 4, 8, 16 or 32 bits).
   * @param {bitjs.io.BitStream} bstream A RTL bit stream.
   * @return {number} The value of the bits read.
   */
  static readData(bstream) {
    // Read in the first 2 bits.
    const flags = bstream.readBits(2);
    switch (flags) { // Data&0xc000
      // Return the next 4 bits.
      case 0:
        return bstream.readBits(4); // (Data>>10)&0xf

      case 1: // 0x4000
        // 0x3c00 => 0011 1100 0000 0000
        if (bstream.peekBits(4) == 0) { // (Data&0x3c00)==0
          // Skip the 4 zero bits.
          bstream.readBits(4);
          // Read in the next 8 and pad with 1s to 32 bits.
          return (0xffffff00 | bstream.readBits(8)) >>> 0; // ((Data>>2)&0xff)
        }

        // Else, read in the next 8.
        return bstream.readBits(8);

      // Read in the next 16.
      case 2: // 0x8000
        const val = bstream.getBits();
        bstream.readBits(16);
        return val; //bstream.readBits(16);

      // case 3
      default:
        return (bstream.readBits(16) << 16) | bstream.readBits(16);
    }
  }
}

// ============================================================================================== //
