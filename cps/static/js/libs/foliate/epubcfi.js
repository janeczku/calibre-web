const findIndices = (arr, f) => arr
    .map((x, i, a) => f(x, i, a) ? i : null).filter(x => x != null)
const splitAt = (arr, is) => [-1, ...is, arr.length].reduce(({ xs, a }, b) =>
    ({ xs: xs?.concat([arr.slice(a + 1, b)]) ?? [], a: b }), {}).xs
const concatArrays = (a, b) =>
    a.slice(0, -1).concat([a[a.length - 1].concat(b[0])]).concat(b.slice(1))

const isNumber = /\d/
export const isCFI = /^epubcfi\((.*)\)$/
const escapeCFI = str => str.replace(/[\^[\](),;=]/g, '^$&')

const wrap = x => isCFI.test(x) ? x : `epubcfi(${x})`
const unwrap = x => x.match(isCFI)?.[1] ?? x
const lift = f => (...xs) =>
    `epubcfi(${f(...xs.map(x => x.match(isCFI)?.[1] ?? x))})`
export const joinIndir = lift((...xs) => xs.join('!'))

const tokenizer = str => {
    const tokens = []
    let state, escape, value = ''
    const push = x => (tokens.push(x), state = null, value = '')
    const cat = x => (value += x, escape = false)
    for (const char of Array.from(str.trim()).concat('')) {
        if (char === '^' && !escape) {
            escape = true
            continue
        }
        if (state === '!') push(['!'])
        else if (state === ',') push([','])
        else if (state === '/' || state === ':') {
            if (isNumber.test(char)) {
                cat(char)
                continue
            } else push([state, parseInt(value)])
        } else if (state === '~') {
            if (isNumber.test(char) || char === '.') {
                cat(char)
                continue
            } else push(['~', parseFloat(value)])
        } else if (state === '@') {
            if (char === ':') {
                push(['@', parseFloat(value)])
                state = '@'
                continue
            }
            if (isNumber.test(char) || char === '.') {
                cat(char)
                continue
            } else push(['@', parseFloat(value)])
        } else if (state === '[') {
            if (char === ';' && !escape) {
                push(['[', value])
                state = ';'
            } else if (char === ',' && !escape) {
                push(['[', value])
                state = '['
            } else if (char === ']' && !escape) push(['[', value])
            else cat(char)
            continue
        } else if (state?.startsWith(';')) {
            if (char === '=' && !escape) {
                state = `;${value}`
                value = ''
            } else if (char === ';' && !escape) {
                push([state, value])
                state = ';'
            } else if (char === ']' && !escape) push([state, value])
            else cat(char)
            continue
        }
        if (char === '/' || char === ':' || char === '~' || char === '@'
        || char === '[' || char === '!' || char === ',') state = char
    }
    return tokens
}

const findTokens = (tokens, x) => findIndices(tokens, ([t]) => t === x)

const parser = tokens => {
    const parts = []
    let state
    for (const [type, val] of tokens) {
        if (type === '/') parts.push({ index: val })
        else {
            const last = parts[parts.length - 1]
            if (type === ':') last.offset = val
            else if (type === '~') last.temporal = val
            else if (type === '@') last.spatial = (last.spatial ?? []).concat(val)
            else if (type === ';s') last.side = val
            else if (type === '[') {
                if (state === '/' && val) last.id = val
                else {
                    last.text = (last.text ?? []).concat(val)
                    continue
                }
            }
        }
        state = type
    }
    return parts
}

// split at step indirections, then parse each part
const parserIndir = tokens =>
    splitAt(tokens, findTokens(tokens, '!')).map(parser)

export const parse = cfi => {
    const tokens = tokenizer(unwrap(cfi))
    const commas = findTokens(tokens, ',')
    if (!commas.length) return parserIndir(tokens)
    const [parent, start, end] = splitAt(tokens, commas).map(parserIndir)
    return { parent, start, end }
}

const partToString = ({ index, id, offset, temporal, spatial, text, side }) => {
    const param = side ? `;s=${side}` : ''
    return `/${index}`
        + (id ? `[${escapeCFI(id)}${param}]` : '')
        // "CFI expressions [..] SHOULD include an explicit character offset"
        + (offset != null && index % 2 ? `:${offset}` : '')
        + (temporal ? `~${temporal}` : '')
        + (spatial ? `@${spatial.join(':')}` : '')
        + (text || (!id && side) ? '['
            + (text?.map(escapeCFI)?.join(',') ?? '')
            + param + ']' : '')
}

const toInnerString = parsed => parsed.parent
    ? [parsed.parent, parsed.start, parsed.end].map(toInnerString).join(',')
    : parsed.map(parts => parts.map(partToString).join('')).join('!')

const toString = parsed => wrap(toInnerString(parsed))

export const collapse = (x, toEnd) => typeof x === 'string'
    ? toString(collapse(parse(x), toEnd))
    : x.parent ? concatArrays(x.parent, x[toEnd ? 'end' : 'start']) : x

// create range CFI from two CFIs
const buildRange = (from, to) => {
    if (typeof from === 'string') from = parse(from)
    if (typeof to === 'string') to = parse(to)
    from = collapse(from)
    to = collapse(to, true)
    // ranges across multiple documents are not allowed; handle local paths only
    const localFrom = from[from.length - 1], localTo = to[to.length - 1]
    const localParent = [], localStart = [], localEnd = []
    let pushToParent = true
    const len = Math.max(localFrom.length, localTo.length)
    for (let i = 0; i < len; i++) {
        const a = localFrom[i], b = localTo[i]
        pushToParent &&= a?.index === b?.index && !a?.offset && !b?.offset
        if (pushToParent) localParent.push(a)
        else {
            if (a) localStart.push(a)
            if (b) localEnd.push(b)
        }
    }
    // copy non-local paths from `from`
    const parent = from.slice(0, -1).concat([localParent])
    return toString({ parent, start: [localStart], end: [localEnd] })
}

export const compare = (a, b) => {
    if (typeof a === 'string') a = parse(a)
    if (typeof b === 'string') b = parse(b)
    if (a.start || b.start) return compare(collapse(a), collapse(b))
        || compare(collapse(a, true), collapse(b, true))

    for (let i = 0; i < Math.max(a.length, b.length); i++) {
        const p = a[i] ?? [], q = b[i] ?? []
        const maxIndex = Math.max(p.length, q.length) - 1
        for (let i = 0; i <= maxIndex; i++) {
            const x = p[i], y = q[i]
            if (!x) return -1
            if (!y) return 1
            if (x.index > y.index) return 1
            if (x.index < y.index) return -1
            if (i === maxIndex) {
                // TODO: compare temporal & spatial offsets
                if (x.offset > y.offset) return 1
                if (x.offset < y.offset) return -1
            }
        }
    }
    return 0
}

const isTextNode = ({ nodeType }) => nodeType === 3 || nodeType === 4
const isElementNode = ({ nodeType }) => nodeType === 1

const getChildNodes = (node, filter) => {
    const nodes = Array.from(node.childNodes)
        // "content other than element and character data is ignored"
        .filter(node => isTextNode(node) || isElementNode(node))
    return filter ? nodes.map(node => {
        const accept = filter(node)
        if (accept === NodeFilter.FILTER_REJECT) return null
        else if (accept === NodeFilter.FILTER_SKIP) return getChildNodes(node, filter)
        else return node
    }).flat().filter(x => x) : nodes
}

// child nodes are organized such that the result is always
//     [element, text, element, text, ..., element],
// regardless of the actual structure in the document;
// so multiple text nodes need to be combined, and nonexistent ones counted;
// see "Step Reference to Child Element or Character Data (/)" in EPUB CFI spec
const indexChildNodes = (node, filter) => {
    const nodes = getChildNodes(node, filter)
        .reduce((arr, node) => {
            let last = arr[arr.length - 1]
            if (!last) arr.push(node)
            // "there is one chunk between each pair of child elements"
            else if (isTextNode(node)) {
                if (Array.isArray(last)) last.push(node)
                else if (isTextNode(last)) arr[arr.length - 1] = [last, node]
                else arr.push(node)
            } else {
                if (isElementNode(last)) arr.push(null, node)
                else arr.push(node)
            }
            return arr
        }, [])
    // "the first chunk is located before the first child element"
    if (isElementNode(nodes[0])) nodes.unshift('first')
    // "the last chunk is located after the last child element"
    if (isElementNode(nodes[nodes.length - 1])) nodes.push('last')
    // "'virtual' elements"
    nodes.unshift('before') // "0 is a valid index"
    nodes.push('after') // "n+2 is a valid index"
    return nodes
}

const partsToNode = (node, parts, filter) => {
    const { id } = parts[parts.length - 1]
    if (id) {
        const el = node.ownerDocument.getElementById(id)
        if (el) return { node: el, offset: 0 }
    }
    for (const { index } of parts) {
        const newNode = node ? indexChildNodes(node, filter)[index] : null
        // handle non-existent nodes
        if (newNode === 'first') return { node: node.firstChild ?? node }
        if (newNode === 'last') return { node: node.lastChild ?? node }
        if (newNode === 'before') return { node, before: true }
        if (newNode === 'after') return { node, after: true }
        node = newNode
    }
    const { offset } = parts[parts.length - 1]
    if (!Array.isArray(node)) return { node, offset }
    // get underlying text node and offset from the chunk
    let sum = 0
    for (const n of node) {
        const { length } = n.nodeValue
        if (sum + length >= offset) return { node: n, offset: offset - sum }
        sum += length
    }
}

const nodeToParts = (node, offset, filter) => {
    let { id, parentNode } = node
    while (filter && parentNode
        && parentNode !== node.ownerDocument.documentElement
        && filter(parentNode) === NodeFilter.FILTER_SKIP)
        parentNode = parentNode.parentNode
    const indexed = indexChildNodes(parentNode, filter)
    const index = indexed.findIndex(x =>
        Array.isArray(x) ? x.some(x => x === node) : x === node)
    // adjust offset as if merging the text nodes in the chunk
    const chunk = indexed[index]
    if (Array.isArray(chunk)) {
        let sum = 0
        for (const x of chunk) {
            if (x === node) {
                sum += offset
                break
            } else sum += x.nodeValue.length
        }
        offset = sum
    }
    const part = { id, index, offset }
    return (parentNode !== node.ownerDocument.documentElement
        ? nodeToParts(parentNode, null, filter).concat(part) : [part])
        // remove ignored nodes
        .filter(x => x.index !== -1)
}

export const fromRange = (range, filter) => {
    const { startContainer, startOffset, endContainer, endOffset } = range
    const start = nodeToParts(startContainer, startOffset, filter)
    if (range.collapsed) return toString([start])
    const end = nodeToParts(endContainer, endOffset, filter)
    return buildRange([start], [end])
}

export const toRange = (doc, parts, filter) => {
    const startParts = collapse(parts)
    const endParts = collapse(parts, true)

    const root = doc.documentElement
    const start = partsToNode(root, startParts[0], filter)
    const end = partsToNode(root, endParts[0], filter)

    const range = doc.createRange()

    if (start.before) range.setStartBefore(start.node)
    else if (start.after) range.setStartAfter(start.node)
    else range.setStart(start.node, start.offset)

    if (end.before) range.setEndBefore(end.node)
    else if (end.after) range.setEndAfter(end.node)
    else range.setEnd(end.node, end.offset)
    return range
}

// faster way of getting CFIs for sorted elements in a single parent
export const fromElements = elements => {
    const results = []
    const { parentNode } = elements[0]
    const parts = nodeToParts(parentNode)
    for (const [index, node] of indexChildNodes(parentNode).entries()) {
        const el = elements[results.length]
        if (node === el)
            results.push(toString([parts.concat({ id: el.id, index })]))
    }
    return results
}

export const toElement = (doc, parts) =>
    partsToNode(doc.documentElement, collapse(parts)).node

// turn indices into standard CFIs when you don't have an actual package document
export const fake = {
    fromIndex: index => wrap(`/6/${(index + 1) * 2}`),
    toIndex: parts => parts?.at(-1).index / 2 - 1,
}

// get CFI from Calibre bookmarks
// see https://github.com/johnfactotum/foliate/issues/849
export const fromCalibrePos = pos => {
    const [parts] = parse(pos)
    const item = parts.shift()
    parts.shift()
    return toString([[{ index: 6 }, item], parts])
}
export const fromCalibreHighlight = ({ spine_index, start_cfi, end_cfi }) => {
    const pre = fake.fromIndex(spine_index) + '!'
    return buildRange(pre + start_cfi.slice(2), pre + end_cfi.slice(2))
}
