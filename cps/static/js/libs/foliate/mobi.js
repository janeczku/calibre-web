const unescapeHTML = str => {
    if (!str) return ''
    const textarea = document.createElement('textarea')
    textarea.innerHTML = str
    return textarea.value
}

const MIME = {
    XML: 'application/xml',
    XHTML: 'application/xhtml+xml',
    HTML: 'text/html',
    CSS: 'text/css',
    SVG: 'image/svg+xml',
}

const PDB_HEADER = {
    name: [0, 32, 'string'],
    type: [60, 4, 'string'],
    creator: [64, 4, 'string'],
    numRecords: [76, 2, 'uint'],
}

const PALMDOC_HEADER = {
    compression: [0, 2, 'uint'],
    numTextRecords: [8, 2, 'uint'],
    recordSize: [10, 2, 'uint'],
    encryption: [12, 2, 'uint'],
}

const MOBI_HEADER = {
    magic: [16, 4, 'string'],
    length: [20, 4, 'uint'],
    type: [24, 4, 'uint'],
    encoding: [28, 4, 'uint'],
    uid: [32, 4, 'uint'],
    version: [36, 4, 'uint'],
    titleOffset: [84, 4, 'uint'],
    titleLength: [88, 4, 'uint'],
    localeRegion: [94, 1, 'uint'],
    localeLanguage: [95, 1, 'uint'],
    resourceStart: [108, 4, 'uint'],
    huffcdic: [112, 4, 'uint'],
    numHuffcdic: [116, 4, 'uint'],
    exthFlag: [128, 4, 'uint'],
    trailingFlags: [240, 4, 'uint'],
    indx: [244, 4, 'uint'],
}

const KF8_HEADER = {
    resourceStart: [108, 4, 'uint'],
    fdst: [192, 4, 'uint'],
    numFdst: [196, 4, 'uint'],
    frag: [248, 4, 'uint'],
    skel: [252, 4, 'uint'],
    guide: [260, 4, 'uint'],
}

const EXTH_HEADER = {
    magic: [0, 4, 'string'],
    length: [4, 4, 'uint'],
    count: [8, 4, 'uint'],
}

const INDX_HEADER = {
    magic: [0, 4, 'string'],
    length: [4, 4, 'uint'],
    type: [8, 4, 'uint'],
    idxt: [20, 4, 'uint'],
    numRecords: [24, 4, 'uint'],
    encoding: [28, 4, 'uint'],
    language: [32, 4, 'uint'],
    total: [36, 4, 'uint'],
    ordt: [40, 4, 'uint'],
    ligt: [44, 4, 'uint'],
    numLigt: [48, 4, 'uint'],
    numCncx: [52, 4, 'uint'],
}

const TAGX_HEADER = {
    magic: [0, 4, 'string'],
    length: [4, 4, 'uint'],
    numControlBytes: [8, 4, 'uint'],
}

const HUFF_HEADER = {
    magic: [0, 4, 'string'],
    offset1: [8, 4, 'uint'],
    offset2: [12, 4, 'uint'],
}

const CDIC_HEADER = {
    magic: [0, 4, 'string'],
    length: [4, 4, 'uint'],
    numEntries: [8, 4, 'uint'],
    codeLength: [12, 4, 'uint'],
}

const FDST_HEADER = {
    magic: [0, 4, 'string'],
    numEntries: [8, 4, 'uint'],
}

const FONT_HEADER = {
    flags: [8, 4, 'uint'],
    dataStart: [12, 4, 'uint'],
    keyLength: [16, 4, 'uint'],
    keyStart: [20, 4, 'uint'],
}

const MOBI_ENCODING = {
    1252: 'windows-1252',
    65001: 'utf-8',
}

const EXTH_RECORD_TYPE = {
    100: ['creator', 'string', true],
    101: ['publisher'],
    103: ['description'],
    104: ['isbn'],
    105: ['subject', 'string', true],
    106: ['date'],
    108: ['contributor', 'string', true],
    109: ['rights'],
    110: ['subjectCode', 'string', true],
    112: ['source', 'string', true],
    113: ['asin'],
    121: ['boundary', 'uint'],
    122: ['fixedLayout'],
    125: ['numResources', 'uint'],
    126: ['originalResolution'],
    127: ['zeroGutter'],
    128: ['zeroMargin'],
    129: ['coverURI'],
    132: ['regionMagnification'],
    201: ['coverOffset', 'uint'],
    202: ['thumbnailOffset', 'uint'],
    503: ['title'],
    524: ['language', 'string', true],
    527: ['pageProgressionDirection'],
}

const MOBI_LANG = {
    1: ['ar', 'ar-SA', 'ar-IQ', 'ar-EG', 'ar-LY', 'ar-DZ', 'ar-MA', 'ar-TN', 'ar-OM',
        'ar-YE', 'ar-SY', 'ar-JO', 'ar-LB', 'ar-KW', 'ar-AE', 'ar-BH', 'ar-QA'],
    2: ['bg'], 3: ['ca'], 4: ['zh', 'zh-TW', 'zh-CN', 'zh-HK', 'zh-SG'], 5: ['cs'],
    6: ['da'], 7: ['de', 'de-DE', 'de-CH', 'de-AT', 'de-LU', 'de-LI'], 8: ['el'],
    9: ['en', 'en-US', 'en-GB', 'en-AU', 'en-CA', 'en-NZ', 'en-IE', 'en-ZA',
        'en-JM', null, 'en-BZ', 'en-TT', 'en-ZW', 'en-PH'],
    10: ['es', 'es-ES', 'es-MX', null, 'es-GT', 'es-CR', 'es-PA', 'es-DO',
        'es-VE', 'es-CO', 'es-PE', 'es-AR', 'es-EC', 'es-CL', 'es-UY', 'es-PY',
        'es-BO', 'es-SV', 'es-HN', 'es-NI', 'es-PR'],
    11: ['fi'], 12: ['fr', 'fr-FR', 'fr-BE', 'fr-CA', 'fr-CH', 'fr-LU', 'fr-MC'],
    13: ['he'], 14: ['hu'], 15: ['is'], 16: ['it', 'it-IT', 'it-CH'],
    17: ['ja'], 18: ['ko'], 19: ['nl', 'nl-NL', 'nl-BE'], 20: ['no', 'nb', 'nn'],
    21: ['pl'], 22: ['pt', 'pt-BR', 'pt-PT'], 23: ['rm'], 24: ['ro'], 25: ['ru'],
    26: ['hr', null, 'sr'], 27: ['sk'], 28: ['sq'], 29: ['sv', 'sv-SE', 'sv-FI'],
    30: ['th'], 31: ['tr'], 32: ['ur'], 33: ['id'], 34: ['uk'], 35: ['be'],
    36: ['sl'], 37: ['et'], 38: ['lv'], 39: ['lt'], 41: ['fa'], 42: ['vi'],
    43: ['hy'], 44: ['az'], 45: ['eu'], 46: ['hsb'], 47: ['mk'], 48: ['st'],
    49: ['ts'], 50: ['tn'], 52: ['xh'], 53: ['zu'], 54: ['af'], 55: ['ka'],
    56: ['fo'], 57: ['hi'], 58: ['mt'], 59: ['se'], 62: ['ms'], 63: ['kk'],
    65: ['sw'], 67: ['uz', null, 'uz-UZ'], 68: ['tt'], 69: ['bn'], 70: ['pa'],
    71: ['gu'], 72: ['or'], 73: ['ta'], 74: ['te'], 75: ['kn'], 76: ['ml'],
    77: ['as'], 78: ['mr'], 79: ['sa'], 82: ['cy', 'cy-GB'], 83: ['gl', 'gl-ES'],
    87: ['kok'], 97: ['ne'], 98: ['fy'],
}

const concatTypedArray = (a, b) => {
    const result = new a.constructor(a.length + b.length)
    result.set(a)
    result.set(b, a.length)
    return result
}
const concatTypedArray3 = (a, b, c) => {
    const result = new a.constructor(a.length + b.length + c.length)
    result.set(a)
    result.set(b, a.length)
    result.set(c, a.length + b.length)
    return result
}

const decoder = new TextDecoder()
const getString = buffer => decoder.decode(buffer)
const getUint = buffer => {
    if (!buffer) return
    const l = buffer.byteLength
    const func = l === 4 ? 'getUint32' : l === 2 ? 'getUint16' : 'getUint8'
    return new DataView(buffer)[func](0)
}
const getStruct = (def, buffer) => Object.fromEntries(Array.from(Object.entries(def))
    .map(([key, [start, len, type]]) => [key,
        (type === 'string' ? getString : getUint)(buffer.slice(start, start + len))]))

const getDecoder = x => new TextDecoder(MOBI_ENCODING[x])

const getVarLen = (byteArray, i = 0) => {
    let value = 0, length = 0
    for (const byte of byteArray.subarray(i, i + 4)) {
        value = (value << 7) | (byte & 0b111_1111) >>> 0
        length++
        if (byte & 0b1000_0000) break
    }
    return { value, length }
}

// variable-length quantity, but read from the end of data
const getVarLenFromEnd = byteArray => {
    let value = 0
    for (const byte of byteArray.subarray(-4)) {
        // `byte & 0b1000_0000` indicates the start of value
        if (byte & 0b1000_0000) value = 0
        value = (value << 7) | (byte & 0b111_1111)
    }
    return value
}

const countBitsSet = x => {
    let count = 0
    for (; x > 0; x = x >> 1) if ((x & 1) === 1) count++
    return count
}

const countUnsetEnd = x => {
    let count = 0
    while ((x & 1) === 0) x = x >> 1, count++
    return count
}

const decompressPalmDOC = array => {
    let output = []
    for (let i = 0; i < array.length; i++) {
        const byte = array[i]
        if (byte === 0) output.push(0) // uncompressed literal, just copy it
        else if (byte <= 8) // copy next 1-8 bytes
            for (const x of array.subarray(i + 1, (i += byte) + 1))
                output.push(x)
        else if (byte <= 0b0111_1111) output.push(byte) // uncompressed literal
        else if (byte <= 0b1011_1111) {
            // 1st and 2nd bits are 10, meaning this is a length-distance pair
            // read next byte and combine it with current byte
            const bytes = (byte << 8) | array[i++ + 1]
            // the 3rd to 13th bits encode distance
            const distance = (bytes & 0b0011_1111_1111_1111) >>> 3
            // the last 3 bits, plus 3, is the length to copy
            const length = (bytes & 0b111) + 3
            for (let j = 0; j < length; j++)
                output.push(output[output.length - distance])
        }
        // compressed from space plus char
        else output.push(32, byte ^ 0b1000_0000)
    }
    return Uint8Array.from(output)
}

const read32Bits = (byteArray, from) => {
    const startByte = from >> 3
    const end = from + 32
    const endByte = end >> 3
    let bits = 0n
    for (let i = startByte; i <= endByte; i++)
        bits = bits << 8n | BigInt(byteArray[i] ?? 0)
    return (bits >> (8n - BigInt(end & 7))) & 0xffffffffn
}

const huffcdic = async (mobi, loadRecord) => {
    const huffRecord = await loadRecord(mobi.huffcdic)
    const { magic, offset1, offset2 } = getStruct(HUFF_HEADER, huffRecord)
    if (magic !== 'HUFF') throw new Error('Invalid HUFF record')

    // table1 is indexed by byte value
    const table1 = Array.from({ length: 256 }, (_, i) => offset1 + i * 4)
        .map(offset => getUint(huffRecord.slice(offset, offset + 4)))
        .map(x => [x & 0b1000_0000, x & 0b1_1111, x >>> 8])

    // table2 is indexed by code length
    const table2 = [null].concat(Array.from({ length: 32 }, (_, i) => offset2 + i * 8)
        .map(offset => [
            getUint(huffRecord.slice(offset, offset + 4)),
            getUint(huffRecord.slice(offset + 4, offset + 8))]))

    const dictionary = []
    for (let i = 1; i < mobi.numHuffcdic; i++) {
        const record = await loadRecord(mobi.huffcdic + i)
        const cdic = getStruct(CDIC_HEADER, record)
        if (cdic.magic !== 'CDIC') throw new Error('Invalid CDIC record')
        // `numEntries` is the total number of dictionary data across CDIC records
        // so `n` here is the number of entries in *this* record
        const n = Math.min(1 << cdic.codeLength, cdic.numEntries - dictionary.length)
        const buffer = record.slice(cdic.length)
        for (let i = 0; i < n; i++) {
            const offset = getUint(buffer.slice(i * 2, i * 2 + 2))
            const x = getUint(buffer.slice(offset, offset + 2))
            const length = x & 0x7fff
            const decompressed = x & 0x8000
            const value = new Uint8Array(
                buffer.slice(offset + 2, offset + 2 + length))
            dictionary.push([value, decompressed])
        }
    }

    const decompress = byteArray => {
        let output = new Uint8Array()
        const bitLength = byteArray.byteLength * 8
        for (let i = 0; i < bitLength;) {
            const bits = Number(read32Bits(byteArray, i))
            let [found, codeLength, value] = table1[bits >>> 24]
            if (!found) {
                while (bits >>> (32 - codeLength) < table2[codeLength][0])
                    codeLength += 1
                value = table2[codeLength][1]
            }
            if ((i += codeLength) > bitLength) break

            const code = value - (bits >>> (32 - codeLength))
            let [result, decompressed] = dictionary[code]
            if (!decompressed) {
                // the result is itself compressed
                result = decompress(result)
                // cache the result for next time
                dictionary[code] = [result, true]
            }
            output = concatTypedArray(output, result)
        }
        return output
    }
    return decompress
}

const getIndexData = async (indxIndex, loadRecord) => {
    const indxRecord = await loadRecord(indxIndex)
    const indx = getStruct(INDX_HEADER, indxRecord)
    if (indx.magic !== 'INDX') throw new Error('Invalid INDX record')
    const decoder = getDecoder(indx.encoding)

    const tagxBuffer = indxRecord.slice(indx.length)
    const tagx = getStruct(TAGX_HEADER, tagxBuffer)
    if (tagx.magic !== 'TAGX') throw new Error('Invalid TAGX section')
    const numTags = (tagx.length - 12) / 4
    const tagTable = Array.from({ length: numTags }, (_, i) =>
        new Uint8Array(tagxBuffer.slice(12 + i * 4, 12 + i * 4 + 4)))

    const cncx = {}
    let cncxRecordOffset = 0
    for (let i = 0; i < indx.numCncx; i++) {
        const record = await loadRecord(indxIndex + indx.numRecords + i + 1)
        const array = new Uint8Array(record)
        for (let pos = 0; pos < array.byteLength;) {
            const index = pos
            const { value, length } = getVarLen(array, pos)
            pos += length
            const result = record.slice(pos, pos + value)
            pos += value
            cncx[cncxRecordOffset + index] = decoder.decode(result)
        }
        cncxRecordOffset += 0x10000
    }

    const table = []
    for (let i = 0; i < indx.numRecords; i++) {
        const record = await loadRecord(indxIndex + 1 + i)
        const array = new Uint8Array(record)
        const indx = getStruct(INDX_HEADER, record)
        if (indx.magic !== 'INDX') throw new Error('Invalid INDX record')
        for (let j = 0; j < indx.numRecords; j++) {
            const offsetOffset = indx.idxt + 4 + 2 * j
            const offset = getUint(record.slice(offsetOffset, offsetOffset + 2))

            const length = getUint(record.slice(offset, offset + 1))
            const name = getString(record.slice(offset + 1, offset + 1 + length))

            const tags = []
            const startPos = offset + 1 + length
            let controlByteIndex = 0
            let pos = startPos + tagx.numControlBytes
            for (const [tag, numValues, mask, end] of tagTable) {
                if (end & 1) {
                    controlByteIndex++
                    continue
                }
                const offset = startPos + controlByteIndex
                const value = getUint(record.slice(offset, offset + 1)) & mask
                if (value === mask) {
                    if (countBitsSet(mask) > 1) {
                        const { value, length } = getVarLen(array, pos)
                        tags.push([tag, null, value, numValues])
                        pos += length
                    } else tags.push([tag, 1, null, numValues])
                } else tags.push([tag, value >> countUnsetEnd(mask), null, numValues])
            }

            const tagMap = {}
            for (const [tag, valueCount, valueBytes, numValues] of tags) {
                const values = []
                if (valueCount != null) {
                    for (let i = 0; i < valueCount * numValues; i++) {
                        const { value, length } = getVarLen(array, pos)
                        values.push(value)
                        pos += length
                    }
                } else {
                    let count = 0
                    while (count < valueBytes) {
                        const { value, length } = getVarLen(array, pos)
                        values.push(value)
                        pos += length
                        count += length
                    }
                }
                tagMap[tag] = values
            }
            table.push({ name, tagMap })
        }
    }
    return { table, cncx }
}

const getNCX = async (indxIndex, loadRecord) => {
    const { table, cncx } = await getIndexData(indxIndex, loadRecord)
    const items = table.map(({ tagMap }, index) => ({
        index,
        offset: tagMap[1]?.[0],
        size: tagMap[2]?.[0],
        label: cncx[tagMap[3]] ?? '',
        headingLevel: tagMap[4]?.[0],
        pos: tagMap[6],
        parent: tagMap[21]?.[0],
        firstChild: tagMap[22]?.[0],
        lastChild: tagMap[23]?.[0],
    }))
    const getChildren = item => {
        if (item.firstChild == null) return item
        item.children = items.filter(x => x.parent === item.index).map(getChildren)
        return item
    }
    return items.filter(item => item.headingLevel === 0).map(getChildren)
}

const getEXTH = (buf, encoding) => {
    const { magic, count } = getStruct(EXTH_HEADER, buf)
    if (magic !== 'EXTH') throw new Error('Invalid EXTH header')
    const decoder = getDecoder(encoding)
    const results = {}
    let offset = 12
    for (let i = 0; i < count; i++) {
        const type = getUint(buf.slice(offset, offset + 4))
        const length = getUint(buf.slice(offset + 4, offset + 8))
        if (type in EXTH_RECORD_TYPE) {
            const [name, typ, many] = EXTH_RECORD_TYPE[type]
            const data = buf.slice(offset + 8, offset + length)
            const value = typ === 'uint' ? getUint(data) : decoder.decode(data)
            if (many) {
                results[name] ??= []
                results[name].push(value)
            } else results[name] = value
        }
        offset += length
    }
    return results
}

const getFont = async (buf, unzlib) => {
    const { flags, dataStart, keyLength, keyStart } = getStruct(FONT_HEADER, buf)
    const array = new Uint8Array(buf.slice(dataStart))
    // deobfuscate font
    if (flags & 0b10) {
        const bytes = keyLength === 16 ? 1024 : 1040
        const key = new Uint8Array(buf.slice(keyStart, keyStart + keyLength))
        const length = Math.min(bytes, array.length)
        for (var i = 0; i < length; i++) array[i] = array[i] ^ key[i % key.length]
    }
    // decompress font
    if (flags & 1) try {
        return await unzlib(array)
    } catch (e) {
        console.warn(e)
        console.warn('Failed to decompress font')
    }
    return array
}

export const isMOBI = async file => {
    const magic = getString(await file.slice(60, 68).arrayBuffer())
    return magic === 'BOOKMOBI'// || magic === 'TEXtREAd'
}

class PDB {
    #file
    #offsets
    pdb
    async open(file) {
        this.#file = file
        const pdb = getStruct(PDB_HEADER, await file.slice(0, 78).arrayBuffer())
        this.pdb = pdb
        const buffer = await file.slice(78, 78 + pdb.numRecords * 8).arrayBuffer()
        // get start and end offsets for each record
        this.#offsets = Array.from({ length: pdb.numRecords },
            (_, i) => getUint(buffer.slice(i * 8, i * 8 + 4)))
            .map((x, i, a) => [x, a[i + 1]])
    }
    loadRecord(index) {
        const offsets = this.#offsets[index]
        if (!offsets) throw new RangeError('Record index out of bounds')
        return this.#file.slice(...offsets).arrayBuffer()
    }
    async loadMagic(index) {
        const start = this.#offsets[index][0]
        return getString(await this.#file.slice(start, start + 4).arrayBuffer())
    }
}

export class MOBI extends PDB {
    #start = 0
    #resourceStart
    #decoder
    #encoder
    #decompress
    #removeTrailingEntries
    constructor({ unzlib }) {
        super()
        this.unzlib = unzlib
    }
    async open(file) {
        await super.open(file)
        // TODO: if (this.pdb.type === 'TEXt')
        this.headers = this.#getHeaders(await super.loadRecord(0))
        this.#resourceStart = this.headers.mobi.resourceStart
        let isKF8 = this.headers.mobi.version >= 8
        if (!isKF8) {
            const boundary = this.headers.exth?.boundary
            if (boundary < 0xffffffff) try {
                // it's a "combo" MOBI/KF8 file; try to open the KF8 part
                this.headers = this.#getHeaders(await super.loadRecord(boundary))
                this.#start = boundary
                isKF8 = true
            } catch (e) {
                console.warn(e)
                console.warn('Failed to open KF8; falling back to MOBI')
            }
        }
        await this.#setup()
        return isKF8 ? new KF8(this).init() : new MOBI6(this).init()
    }
    #getHeaders(buf) {
        const palmdoc = getStruct(PALMDOC_HEADER, buf)
        const mobi = getStruct(MOBI_HEADER, buf)
        if (mobi.magic !== 'MOBI') throw new Error('Missing MOBI header')

        const { titleOffset, titleLength, localeLanguage, localeRegion } = mobi
        mobi.title = buf.slice(titleOffset, titleOffset + titleLength)
        const lang = MOBI_LANG[localeLanguage]
        mobi.language = lang?.[localeRegion >> 2] ?? lang?.[0]

        const exth = mobi.exthFlag & 0b100_0000
            ? getEXTH(buf.slice(mobi.length + 16), mobi.encoding) : null
        const kf8 = mobi.version >= 8 ? getStruct(KF8_HEADER, buf) : null
        return { palmdoc, mobi, exth, kf8 }
    }
    async #setup() {
        const { palmdoc, mobi } = this.headers
        this.#decoder = getDecoder(mobi.encoding)
        // `TextEncoder` only supports UTF-8
        // we are only encoding ASCII anyway, so I think it's fine
        this.#encoder = new TextEncoder()

        // set up decompressor
        const { compression } = palmdoc
        this.#decompress = compression === 1 ? f => f
            : compression === 2 ? decompressPalmDOC
            : compression === 17480 ? await huffcdic(mobi, this.loadRecord.bind(this))
            : null
        if (!this.#decompress) throw new Error('Unknown compression type')

        // set up function for removing trailing bytes
        const { trailingFlags } = mobi
        const multibyte = trailingFlags & 1
        const numTrailingEntries = countBitsSet(trailingFlags >>> 1)
        this.#removeTrailingEntries = array => {
            for (let i = 0; i < numTrailingEntries; i++) {
                const length = getVarLenFromEnd(array)
                array = array.subarray(0, -length)
            }
            if (multibyte) {
                const length = (array[array.length - 1] & 0b11) + 1
                array = array.subarray(0, -length)
            }
            return array
        }
    }
    decode(...args) {
        return this.#decoder.decode(...args)
    }
    encode(...args) {
        return this.#encoder.encode(...args)
    }
    loadRecord(index) {
        return super.loadRecord(this.#start + index)
    }
    loadMagic(index) {
        return super.loadMagic(this.#start + index)
    }
    loadText(index) {
        return this.loadRecord(index + 1)
            .then(buf => new Uint8Array(buf))
            .then(this.#removeTrailingEntries)
            .then(this.#decompress)
    }
    async loadResource(index) {
        const buf = await super.loadRecord(this.#resourceStart + index)
        const magic = getString(buf.slice(0, 4))
        if (magic === 'FONT') return getFont(buf, this.unzlib)
        if (magic === 'VIDE' || magic === 'AUDI') return buf.slice(12)
        return buf
    }
    getNCX() {
        const index = this.headers.mobi.indx
        if (index < 0xffffffff) return getNCX(index, this.loadRecord.bind(this))
    }
    getMetadata() {
        const { mobi, exth } = this.headers
        return {
            identifier: mobi.uid.toString(),
            title: unescapeHTML(exth?.title || this.decode(mobi.title)),
            author: exth?.creator?.map(unescapeHTML),
            publisher: unescapeHTML(exth?.publisher),
            language: exth?.language ?? mobi.language,
            published: exth?.date,
            description: unescapeHTML(exth?.description),
            subject: exth?.subject?.map(unescapeHTML),
            rights: unescapeHTML(exth?.rights),
            contributor: exth?.contributor,
        }
    }
    async getCover() {
        const { exth } = this.headers
        const offset = exth?.coverOffset < 0xffffffff ? exth?.coverOffset
            : exth?.thumbnailOffset < 0xffffffff ? exth?.thumbnailOffset : null
        if (offset != null) {
            const buf = await this.loadResource(offset)
            return new Blob([buf])
        }
    }
}

const mbpPagebreakRegex = /<\s*(?:mbp:)?pagebreak[^>]*>/gi
const fileposRegex = /<[^<>]+filepos=['"]{0,1}(\d+)[^<>]*>/gi

const getIndent = el => {
    let x = 0
    while (el) {
        const parent = el.parentElement
        if (parent) {
            const tag = parent.tagName.toLowerCase()
            if (tag === 'p') x += 1.5
            else if (tag === 'blockquote') x += 2
        }
        el = parent
    }
    return x
}

function rawBytesToString(uint8Array) {
    const chunkSize = 0x8000
    let result = ''
    for (let i = 0; i < uint8Array.length; i += chunkSize) {
        result += String.fromCharCode.apply(null, uint8Array.subarray(i, i + chunkSize))
    }
    return result
}

class MOBI6 {
    parser = new DOMParser()
    serializer = new XMLSerializer()
    #resourceCache = new Map()
    #textCache = new Map()
    #cache = new Map()
    #sections
    #fileposList = []
    #type = MIME.HTML
    constructor(mobi) {
        this.mobi = mobi
    }
    async init() {
        const recordBuffers = []
        for (let i = 0; i < this.mobi.headers.palmdoc.numTextRecords; i++) {
            const buf = await this.mobi.loadText(i)
            recordBuffers.push(buf)
        }
        const totalLength = recordBuffers.reduce((sum, buf) => sum + buf.byteLength, 0)
        // load all text records in an array
        const array = new Uint8Array(totalLength)
        recordBuffers.reduce((offset, buf) => {
            array.set(new Uint8Array(buf), offset)
            return offset + buf.byteLength
        }, 0)
        // convert to string so we can use regex
        // note that `filepos` are byte offsets
        // so it needs to preserve each byte as a separate character
        // (see https://stackoverflow.com/q/50198017)
        const str = rawBytesToString(array)

        // split content into sections at each `<mbp:pagebreak>`
        this.#sections = [0]
            .concat(Array.from(str.matchAll(mbpPagebreakRegex), m => m.index))
            .map((start, i, a) => {
                const end = a[i + 1] ?? array.length
                return { book: this, raw: array.subarray(start, end) }
            })
            // get start and end filepos for each section
            .map((section, i, arr) => {
                section.start = arr[i - 1]?.end ?? 0
                section.end = section.start + section.raw.byteLength
                return section
            })

        this.sections = this.#sections.map((section, index) => ({
            id: index,
            load: () => this.loadSection(section),
            createDocument: () => this.createDocument(section),
            size: section.end - section.start,
        }))

        // get list of all `filepos` references in the book,
        // which will be used to insert anchor elements
        // because only then can they be referenced in the DOM
        // NOTE: must be built BEFORE getGuide()/createDocument() so that sections
        // cached during init() already have anchor elements inserted.
        this.#fileposList = [...new Set(
            Array.from(str.matchAll(fileposRegex), m => m[1]))]
            .map(filepos => ({ filepos, number: Number(filepos) }))
            .sort((a, b) => a.number - b.number)

        try {
            this.landmarks = await this.getGuide()
            const tocHref = this.landmarks
                .find(({ type }) => type?.includes('toc'))?.href
            if (tocHref) {
                const { index } = this.resolveHref(tocHref)
                const doc = await this.sections[index].createDocument()
                let lastItem
                let lastLevel = 0
                let lastIndent = 0
                const lastLevelOfIndent = new Map()
                const lastParentOfLevel = new Map()
                this.toc = Array.from(doc.querySelectorAll('a[filepos]'))
                    .reduce((arr, a) => {
                        const indent = getIndent(a)
                        const item = {
                            label: a.innerText?.trim() ?? '',
                            href: `filepos:${a.getAttribute('filepos')}`,
                        }
                        const level = indent > lastIndent ? lastLevel + 1
                            : indent === lastIndent ? lastLevel
                            : lastLevelOfIndent.get(indent) ?? Math.max(0, lastLevel - 1)
                        if (level > lastLevel) {
                            if (lastItem) {
                                lastItem.subitems ??= []
                                lastItem.subitems.push(item)
                                lastParentOfLevel.set(level, lastItem)
                            }
                            else arr.push(item)
                        }
                        else {
                            const parent = lastParentOfLevel.get(level)
                            if (parent) parent.subitems.push(item)
                            else arr.push(item)
                        }
                        lastItem = item
                        lastLevel = level
                        lastIndent = indent
                        lastLevelOfIndent.set(indent, level)
                        return arr
                    }, [])
            }
        } catch(e) {
            console.warn(e)
        }

        this.metadata = this.mobi.getMetadata()
        this.getCover = this.mobi.getCover.bind(this.mobi)
        return this
    }
    async getGuide() {
        const doc = await this.createDocument(this.#sections[0])
        return Array.from(doc.getElementsByTagName('reference'), ref => ({
            label: ref.getAttribute('title'),
            type: ref.getAttribute('type')?.split(/\s/),
            href: `filepos:${ref.getAttribute('filepos')}`,
        }))
    }
    async loadResource(index) {
        if (this.#resourceCache.has(index)) return this.#resourceCache.get(index)
        const raw = await this.mobi.loadResource(index)
        const url = URL.createObjectURL(new Blob([raw]))
        this.#resourceCache.set(index, url)
        return url
    }
    async loadRecindex(recindex) {
        return this.loadResource(Number(recindex) - 1)
    }
    async replaceResources(doc) {
        for (const img of doc.querySelectorAll('img[recindex]')) {
            const recindex = img.getAttribute('recindex')
            try {
                img.src = await this.loadRecindex(recindex)
            } catch {
                console.warn(`Failed to load image ${recindex}`)
            }
        }
        for (const media of doc.querySelectorAll('[mediarecindex]')) {
            const mediarecindex = media.getAttribute('mediarecindex')
            const recindex = media.getAttribute('recindex')
            try {
                media.src = await this.loadRecindex(mediarecindex)
                if (recindex) media.poster = await this.loadRecindex(recindex)
            } catch {
                console.warn(`Failed to load media ${mediarecindex}`)
            }
        }
        for (const a of doc.querySelectorAll('[filepos]')) {
            const filepos = a.getAttribute('filepos')
            a.href = `filepos:${filepos}`
        }
    }
    async loadText(section) {
        if (this.#textCache.has(section)) return this.#textCache.get(section)
        const { raw } = section

        // insert anchor elements for each `filepos`
        const fileposList = this.#fileposList
            .filter(({ number }) => number >= section.start && number < section.end)
            .map(obj => ({ ...obj, offset: obj.number - section.start }))
        let arr = raw
        if (fileposList.length) {
            arr = raw.subarray(0, fileposList[0].offset)
            fileposList.forEach(({ filepos, offset }, i) => {
                const next = fileposList[i + 1]
                const a = this.mobi.encode(`<a id="filepos${filepos}"></a>`)
                arr = concatTypedArray3(arr, a, raw.subarray(offset, next?.offset))
            })
        }
        const str = this.mobi.decode(arr).replaceAll(mbpPagebreakRegex, '')
        this.#textCache.set(section, str)
        return str
    }
    async createDocument(section) {
        const str = await this.loadText(section)
        return this.parser.parseFromString(str, this.#type)
    }
    async loadSection(section) {
        if (this.#cache.has(section)) return this.#cache.get(section)
        const doc = await this.createDocument(section)

        // inject default stylesheet
        const style = doc.createElement('style')
        doc.head.append(style)
        // blockquotes in MOBI seem to have only a small left margin by default
        // many books seem to rely on this, as it's the only way to set margin
        // (since there's no CSS)
        style.append(doc.createTextNode(`blockquote {
            margin-block-start: 0;
            margin-block-end: 0;
            margin-inline-start: 1em;
            margin-inline-end: 0;
        }`))

        await this.replaceResources(doc)
        const result = this.serializer.serializeToString(doc)
        const url = URL.createObjectURL(new Blob([result], { type: this.#type }))
        this.#cache.set(section, url)
        return url
    }
    resolveHref(href) {
        const filepos = href.match(/filepos:(.*)/)[1]
        const number = Number(filepos)
        const index = this.#sections.findIndex(section => section.end > number)
        const anchor = doc => doc.getElementById(`filepos${filepos}`)
        return { index, anchor }
    }
    splitTOCHref(href) {
        const filepos = href.match(/filepos:(.*)/)[1]
        const number = Number(filepos)
        const index = this.#sections.findIndex(section => section.end > number)
        return [index, `filepos${filepos}`]
    }
    getTOCFragment(doc, id) {
        return doc.getElementById(id)
    }
    isExternal(uri) {
        return /^(?!blob|filepos)\w+:/i.test(uri)
    }
    destroy() {
        for (const url of this.#resourceCache.values()) URL.revokeObjectURL(url)
        for (const url of this.#cache.values()) URL.revokeObjectURL(url)
    }
}

// handlers for `kindle:` uris
const kindleResourceRegex = /kindle:(flow|embed):(\w+)(?:\?mime=(\w+\/[-+.\w]+))?/
const kindlePosRegex = /kindle:pos:fid:(\w+):off:(\w+)/
const parseResourceURI = str => {
    const [resourceType, id, type] = str.match(kindleResourceRegex).slice(1)
    return { resourceType, id: parseInt(id, 32), type }
}
const parsePosURI = str => {
    const [fid, off] = str.match(kindlePosRegex).slice(1)
    return { fid: parseInt(fid, 32), off: parseInt(off, 32) }
}
const makePosURI = (fid = 0, off = 0) =>
    `kindle:pos:fid:${fid.toString(32).toUpperCase().padStart(4, '0')
    }:off:${off.toString(32).toUpperCase().padStart(10, '0')}`

// `kindle:pos:` links are originally links that contain fragments identifiers
// so there should exist an element with `id` or `name`
// otherwise try to find one with an `aid` attribute
const getFragmentSelector = str => {
    const match = str.match(/\s(id|name|aid)\s*=\s*['"]([^'"]*)['"]/i)
    if (!match) return
    const [, attr, value] = match
    return `[${attr}="${CSS.escape(value)}"]`
}

// replace asynchronously and sequentially
const replaceSeries = async (str, regex, f) => {
    const matches = []
    str.replace(regex, (...args) => (matches.push(args), null))
    const results = []
    for (const args of matches) results.push(await f(...args))
    return str.replace(regex, () => results.shift())
}

const getPageSpread = properties => {
    for (const p of properties) {
        if (p === 'page-spread-left' || p === 'rendition:page-spread-left')
            return 'left'
        if (p === 'page-spread-right' || p === 'rendition:page-spread-right')
            return 'right'
        if (p === 'rendition:page-spread-center') return 'center'
    }
}

class KF8 {
    parser = new DOMParser()
    serializer = new XMLSerializer()
    transformTarget = new EventTarget()
    #cache = new Map()
    #fragmentOffsets = new Map()
    #fragmentSelectors = new Map()
    #tables = {}
    #sections
    #fullRawLength
    #rawHead = new Uint8Array()
    #rawTail = new Uint8Array()
    #lastLoadedHead = -1
    #lastLoadedTail = -1
    #type = MIME.XHTML
    #inlineMap = new Map()
    constructor(mobi) {
        this.mobi = mobi
    }
    async init() {
        const loadRecord = this.mobi.loadRecord.bind(this.mobi)
        const { kf8 } = this.mobi.headers

        try {
            const fdstBuffer = await loadRecord(kf8.fdst)
            const fdst = getStruct(FDST_HEADER, fdstBuffer)
            if (fdst.magic !== 'FDST') throw new Error('Missing FDST record')
            const fdstTable = Array.from({ length: fdst.numEntries },
                (_, i) => 12 + i * 8)
                .map(offset => [
                    getUint(fdstBuffer.slice(offset, offset + 4)),
                    getUint(fdstBuffer.slice(offset + 4, offset + 8))])
            this.#tables.fdstTable = fdstTable
            this.#fullRawLength = fdstTable[fdstTable.length - 1][1]
        } catch {}

        const skelTable = (await getIndexData(kf8.skel, loadRecord)).table
            .map(({ name, tagMap }, index) => ({
                index, name,
                numFrag: tagMap[1][0],
                offset: tagMap[6][0],
                length: tagMap[6][1],
            }))
        const fragData = await getIndexData(kf8.frag, loadRecord)
        const fragTable = fragData.table.map(({ name, tagMap }) => ({
            insertOffset: parseInt(name),
            selector: fragData.cncx[tagMap[2][0]],
            index: tagMap[4][0],
            offset: tagMap[6][0],
            length: tagMap[6][1],
        }))
        this.#tables.skelTable = skelTable
        this.#tables.fragTable = fragTable

        this.#sections = skelTable.reduce((arr, skel) => {
            const last = arr[arr.length - 1]
            const fragStart = last?.fragEnd ?? 0, fragEnd = fragStart + skel.numFrag
            const frags = fragTable.slice(fragStart, fragEnd)
            const length = skel.length + frags.map(f => f.length).reduce((a, b) => a + b, 0)
            const totalLength = (last?.totalLength ?? 0) + length
            return arr.concat({ skel, frags, fragEnd, length, totalLength })
        }, [])

        const resources = await this.getResourcesByMagic(['RESC', 'PAGE'])
        const pageSpreads = new Map()
        if (resources.RESC) {
            const buf = await this.mobi.loadRecord(resources.RESC)
            const str = this.mobi.decode(buf.slice(16)).replace(/\0/g, '')
            // the RESC record lacks the root `<package>` element
            // but seem to be otherwise valid XML
            const index = str.search(/\?>/)
            const xmlStr = `<package>${str.slice(index)}</package>`
            const opf = this.parser.parseFromString(xmlStr, MIME.XML)
            for (const $itemref of opf.querySelectorAll('spine > itemref')) {
                const i = parseInt($itemref.getAttribute('skelid'))
                pageSpreads.set(i, getPageSpread(
                    $itemref.getAttribute('properties')?.split(' ') ?? []))
            }
        }

        this.sections = this.#sections.map((section, index) =>
            section.frags.length ? ({
                id: index,
                load: () => this.loadSection(section),
                createDocument: () => this.createDocument(section),
                size: section.length,
                pageSpread: pageSpreads.get(index),
            }) : ({ linear: 'no' }))

        try {
            const ncx = await this.mobi.getNCX()
            const map = ({ label, pos, children }) => {
                const [fid, off] = pos
                const href = makePosURI(fid, off)
                const arr = this.#fragmentOffsets.get(fid)
                if (arr) arr.push(off)
                else this.#fragmentOffsets.set(fid, [off])
                return { label: unescapeHTML(label), href, subitems: children?.map(map) }
            }
            this.toc = ncx?.map(map)
            this.landmarks = await this.getGuide()
        } catch(e) {
            console.warn(e)
        }

        const { exth } = this.mobi.headers
        this.dir = exth.pageProgressionDirection
        this.rendition = {
            layout: exth.fixedLayout === 'true' ? 'pre-paginated' : 'reflowable',
            viewport: Object.fromEntries(exth.originalResolution
                ?.split('x')?.slice(0, 2)
                ?.map((x, i) => [i ? 'height' : 'width', x]) ?? []),
        }

        this.metadata = this.mobi.getMetadata()
        this.getCover = this.mobi.getCover.bind(this.mobi)
        return this
    }
    // is this really the only way of getting to RESC, PAGE, etc.?
    async getResourcesByMagic(keys) {
        const results = {}
        const start = this.mobi.headers.kf8.resourceStart
        const end = this.mobi.pdb.numRecords
        for (let i = start; i < end; i++) {
            try {
                const magic = await this.mobi.loadMagic(i)
                const match = keys.find(key => key === magic)
                if (match) results[match] = i
            } catch {}
        }
        return results
    }
    async getGuide() {
        const index = this.mobi.headers.kf8.guide
        if (index < 0xffffffff) {
            const loadRecord = this.mobi.loadRecord.bind(this.mobi)
            const { table, cncx } = await getIndexData(index, loadRecord)
            return table.map(({ name, tagMap }) => ({
                label: cncx[tagMap[1][0]] ?? '',
                type: name?.split(/\s/),
                href: makePosURI(tagMap[6]?.[0] ?? tagMap[3]?.[0]),
            }))
        }
    }
    async loadResourceBlob(str) {
        const { resourceType, id, type } = parseResourceURI(str)
        const raw = resourceType === 'flow' ? await this.loadFlow(id)
            : await this.mobi.loadResource(id - 1)
        const result = [MIME.XHTML, MIME.HTML, MIME.CSS, MIME.SVG].includes(type)
            ? await this.replaceResources(this.mobi.decode(raw)) : raw
        const detail = { data: result, type }
        const event = new CustomEvent('data', { detail })
        this.transformTarget.dispatchEvent(event)
        const newData = await event.detail.data
        const newType = await event.detail.type
        const doc = newType === MIME.SVG ? this.parser.parseFromString(newData, newType) : null
        return [new Blob([newData], { newType }),
            // SVG wrappers need to be inlined
            // as browsers don't allow external resources when loading SVG as an image
            doc?.getElementsByTagNameNS('http://www.w3.org/2000/svg', 'image')?.length
                ? doc.documentElement : null]
    }
    async loadResource(str) {
        if (this.#cache.has(str)) return this.#cache.get(str)
        const [blob, inline] = await this.loadResourceBlob(str)
        const url = inline ? str : URL.createObjectURL(blob)
        if (inline) this.#inlineMap.set(url, inline)
        this.#cache.set(str, url)
        return url
    }
    replaceResources(str) {
        const regex = new RegExp(kindleResourceRegex, 'g')
        return replaceSeries(str, regex, this.loadResource.bind(this))
    }
    // NOTE: there doesn't seem to be a way to access text randomly?
    // how to know the decompressed size of the records without decompressing?
    // 4096 is just the maximum size
    async loadRaw(start, end) {
        // here we load either from the front or back until we have reached the
        // required offsets; at worst you'd have to load half the book at once
        const distanceHead = end - this.#rawHead.length
        const distanceEnd = this.#fullRawLength == null ? Infinity
            : (this.#fullRawLength - this.#rawTail.length) - start
        // load from the start
        if (distanceHead < 0 || distanceHead < distanceEnd) {
            while (this.#rawHead.length < end) {
                const index = ++this.#lastLoadedHead
                const data = await this.mobi.loadText(index)
                this.#rawHead = concatTypedArray(this.#rawHead, data)
            }
            return this.#rawHead.slice(start, end)
        }
        // load from the end
        while (this.#fullRawLength - this.#rawTail.length > start) {
            const index = this.mobi.headers.palmdoc.numTextRecords - 1
                - (++this.#lastLoadedTail)
            const data = await this.mobi.loadText(index)
            this.#rawTail = concatTypedArray(data, this.#rawTail)
        }
        const rawTailStart = this.#fullRawLength - this.#rawTail.length
        return this.#rawTail.slice(start - rawTailStart, end - rawTailStart)
    }
    loadFlow(index) {
        if (index < 0xffffffff)
            return this.loadRaw(...this.#tables.fdstTable[index])
    }
    async loadText(section) {
        const { skel, frags, length } = section
        const raw = await this.loadRaw(skel.offset, skel.offset + length)
        let skeleton = raw.slice(0, skel.length)
        for (const frag of frags) {
            const insertOffset = frag.insertOffset - skel.offset
            const offset = skel.length + frag.offset
            const fragRaw = raw.slice(offset, offset + frag.length)
            skeleton = concatTypedArray3(
                skeleton.slice(0, insertOffset), fragRaw,
                skeleton.slice(insertOffset))

            const offsets = this.#fragmentOffsets.get(frag.index)
            if (offsets) for (const offset of offsets) {
                const str = this.mobi.decode(fragRaw.slice(offset))
                const selector = getFragmentSelector(str)
                this.#setFragmentSelector(frag.index, offset, selector)
            }
        }
        return this.mobi.decode(skeleton)
    }
    async createDocument(section) {
        const str = await this.loadText(section)
        return this.parser.parseFromString(str, this.#type)
    }
    async loadSection(section) {
        if (this.#cache.has(section)) return this.#cache.get(section)
        const str = await this.loadText(section)
        const replaced = await this.replaceResources(str)

        // by default, type is XHTML; change to HTML if it's not valid XHTML
        let doc = this.parser.parseFromString(replaced, this.#type)
        if (doc.querySelector('parsererror') || !doc.documentElement?.namespaceURI) {
            this.#type = MIME.HTML
            doc = this.parser.parseFromString(replaced, this.#type)
        }
        for (const [url, node] of this.#inlineMap) {
            for (const el of doc.querySelectorAll(`img[src="${url}"]`))
                el.replaceWith(node)
        }
        const url = URL.createObjectURL(
            new Blob([this.serializer.serializeToString(doc)], { type: this.#type }))
        this.#cache.set(section, url)
        return url
    }
    getIndexByFID(fid) {
        return this.#sections.findIndex(section =>
            section.frags.some(frag => frag.index === fid))
    }
    #setFragmentSelector(id, offset, selector) {
        const map = this.#fragmentSelectors.get(id)
        if (map) map.set(offset, selector)
        else {
            const map = new Map()
            this.#fragmentSelectors.set(id, map)
            map.set(offset, selector)
        }
    }
    async resolveHref(href) {
        const { fid, off } = parsePosURI(href)
        const index = this.getIndexByFID(fid)
        if (index < 0) return

        const saved = this.#fragmentSelectors.get(fid)?.get(off)
        if (saved) return { index, anchor: doc => doc.querySelector(saved) }

        const { skel, frags } = this.#sections[index]
        const frag = frags.find(frag => frag.index === fid)
        const offset = skel.offset + skel.length + frag.offset
        const fragRaw = await this.loadRaw(offset, offset + frag.length)
        const str = this.mobi.decode(fragRaw.slice(off))
        const selector = getFragmentSelector(str)
        this.#setFragmentSelector(fid, off, selector)
        const anchor = doc => doc.querySelector(selector)
        return { index, anchor }
    }
    splitTOCHref(href) {
        const pos = parsePosURI(href)
        const index = this.getIndexByFID(pos.fid)
        return [index, pos]
    }
    getTOCFragment(doc, { fid, off }) {
        const selector = this.#fragmentSelectors.get(fid)?.get(off)
        return doc.querySelector(selector)
    }
    isExternal(uri) {
        return /^(?!blob|kindle)\w+:/i.test(uri)
    }
    destroy() {
        for (const url of this.#cache.values()) URL.revokeObjectURL(url)
    }
}
