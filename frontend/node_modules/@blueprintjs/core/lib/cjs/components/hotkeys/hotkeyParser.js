"use strict";
/*
 * Copyright 2016 Palantir Technologies, Inc. All rights reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.normalizeKeyCombo = exports.getKeyCombo = exports.getKeyComboString = exports.parseKeyCombo = exports.SHIFT_KEYS = exports.CONFIG_ALIASES = exports.MODIFIER_BIT_MASKS = void 0;
exports.comboMatches = comboMatches;
exports.isMac = isMac;
/**
 * Named modifier keys
 *
 * @see https://www.w3.org/TR/uievents-key/#keys-modifier
 */
const MODIFIER_KEYS = new Set(["Shift", "Control", "Alt", "Meta"]);
exports.MODIFIER_BIT_MASKS = {
    alt: 1,
    ctrl: 2,
    meta: 4,
    shift: 8,
};
exports.CONFIG_ALIASES = {
    cmd: "meta",
    command: "meta",
    del: "delete",
    esc: "escape",
    escape: "escape",
    minus: "-",
    mod: isMac(undefined) ? "meta" : "ctrl",
    option: "alt",
    plus: "+",
    return: "enter",
    win: "meta",
    // need these aliases for backwards-compatibility (but they're also convenient)
    up: "ArrowUp",
    left: "ArrowLeft",
    down: "ArrowDown",
    right: "ArrowRight",
};
/**
 * Key mapping used in getKeyCombo() implementation for physical keys which are not alphabet characters or digits.
 *
 * N.B. at some point, we should stop using this mapping, since we can implement the desired functionality in a more
 * straightforward way by using the `event.code` property, which will always tell us the identifiers represented by the
 * _values_ in this object (the default physical keys, unaltered by modifier keys or keyboard layout).
 */
exports.SHIFT_KEYS = {
    "~": "`",
    _: "-",
    "+": "=",
    "{": "[",
    "}": "]",
    "|": "\\",
    ":": ";",
    '"': "'",
    "<": ",",
    ">": ".",
    "?": "/",
};
function comboMatches(a, b) {
    return a.modifiers === b.modifiers && a.key === b.key;
}
/**
 * Converts a key combo string into a key combo object. Key combos include
 * zero or more modifier keys, such as `shift` or `alt`, and exactly one
 * action key, such as `A`, `enter`, or `left`.
 *
 * For action keys that require a shift, e.g. `@` or `|`, we inlude the
 * necessary `shift` modifier and automatically convert the action key to the
 * unshifted version. For example, `@` is equivalent to `shift+2`.
 */
const parseKeyCombo = (combo) => {
    const pieces = combo.replace(/\s/g, "").toLowerCase().split("+");
    let modifiers = 0;
    let key;
    for (let piece of pieces) {
        if (piece === "") {
            throw new Error(`Failed to parse key combo "${combo}".
                Valid key combos look like "cmd + plus", "shift+p", or "!"`);
        }
        if (exports.CONFIG_ALIASES[piece] !== undefined) {
            piece = exports.CONFIG_ALIASES[piece];
        }
        if (exports.MODIFIER_BIT_MASKS[piece] !== undefined) {
            modifiers += exports.MODIFIER_BIT_MASKS[piece];
        }
        else if (exports.SHIFT_KEYS[piece] !== undefined) {
            modifiers += exports.MODIFIER_BIT_MASKS.shift;
            key = exports.SHIFT_KEYS[piece];
        }
        else {
            key = piece.toLowerCase();
        }
    }
    return { modifiers, key };
};
exports.parseKeyCombo = parseKeyCombo;
/**
 * Interprets a keyboard event as a valid KeyComboTag `combo` prop string value.
 *
 * Note that this function is only used in the docs example and tests; it is not used by `useHotkeys()` or any
 * Blueprint consumers that we are currently aware of.
 */
const getKeyComboString = (e) => {
    const comboParts = [];
    // modifiers first
    if (e.ctrlKey) {
        comboParts.push("ctrl");
    }
    if (e.altKey) {
        comboParts.push("alt");
    }
    if (e.shiftKey) {
        comboParts.push("shift");
    }
    if (e.metaKey) {
        comboParts.push("meta");
    }
    const key = maybeGetKeyFromEventCode(e);
    if (key !== undefined) {
        comboParts.push(key);
    }
    else {
        if (e.code === "Space") {
            comboParts.push("space");
        }
        else if (MODIFIER_KEYS.has(e.key)) {
            // do nothing
        }
        else if (e.shiftKey && exports.SHIFT_KEYS[e.key] !== undefined) {
            comboParts.push(exports.SHIFT_KEYS[e.key]);
        }
        else if (e.key !== undefined) {
            comboParts.push(e.key.toLowerCase());
        }
    }
    return comboParts.join(" + ");
};
exports.getKeyComboString = getKeyComboString;
const KEY_CODE_PREFIX = "Key";
const DIGIT_CODE_PREFIX = "Digit";
function maybeGetKeyFromEventCode(e) {
    if (e.code == null) {
        return undefined;
    }
    if (e.code.startsWith(KEY_CODE_PREFIX)) {
        // Code looks like "KeyA", etc.
        return e.code.substring(KEY_CODE_PREFIX.length).toLowerCase();
    }
    else if (e.code.startsWith(DIGIT_CODE_PREFIX)) {
        // Code looks like "Digit1", etc.
        return e.code.substring(DIGIT_CODE_PREFIX.length).toLowerCase();
    }
    else if (e.code === "Space" || e.code === "Delete") {
        return e.code.toLowerCase();
    }
    return undefined;
}
/**
 * Determines the key combo object from the given keyboard event. A key combo includes zero or more modifiers
 * (represented by a bitmask) and one key. We use a nuanced approach:
 * - For digits (0-9): use `code` to get the base digit (Shift+1 → "1", not "!")
 * - For letters (a-z): use `key` to respect keyboard layout
 * - For symbols: use `key`, with SHIFT_KEYS mapping applied when Shift is pressed
 * - For Alt-modified characters: use `code` to avoid transformed characters (Alt+c → ç on macOS)
 *
 * @see https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key
 * @see https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/code
 */
const getKeyCombo = (e) => {
    let key;
    if (MODIFIER_KEYS.has(e.key)) {
        // Leave local variable `key` undefined
    }
    else {
        const codeKey = maybeGetKeyFromEventCode(e);
        // Special cases where we must use code instead of key
        if (e.code === "Space" || e.code === "Delete") {
            // Space: event.key is " " but we need "space" to match parseKeyCombo
            // Delete: need lowercase code name
            key = codeKey;
        }
        else if (e.altKey && isAltModifiedCharacter(e.key) && codeKey !== undefined) {
            // Alt on macOS produces special characters (e.g., Alt+c → ç), use code for those cases
            key = codeKey;
        }
        else if (e.code?.startsWith(DIGIT_CODE_PREFIX) && codeKey !== undefined) {
            // For digit keys, always use code to get the base digit (Shift+1 → "1", not "!")
            key = codeKey;
        }
        else {
            // For letters and other keys, prefer event.key to respect keyboard layout
            key = e.key?.toLowerCase() ?? codeKey;
        }
    }
    let modifiers = 0;
    if (e.altKey) {
        modifiers += exports.MODIFIER_BIT_MASKS.alt;
    }
    if (e.ctrlKey) {
        modifiers += exports.MODIFIER_BIT_MASKS.ctrl;
    }
    if (e.metaKey) {
        modifiers += exports.MODIFIER_BIT_MASKS.meta;
    }
    if (e.shiftKey) {
        modifiers += exports.MODIFIER_BIT_MASKS.shift;
        if (exports.SHIFT_KEYS[e.key] !== undefined) {
            key = exports.SHIFT_KEYS[e.key];
        }
    }
    return { modifiers, key };
};
exports.getKeyCombo = getKeyCombo;
/**
 * Checks if a character is likely the result of Alt modification on macOS.
 * Alt produces characters like: ç, ñ, ø, ∫, etc. which are outside normal ASCII printable range.
 */
function isAltModifiedCharacter(key) {
    if (key == null || key.length !== 1) {
        return false;
    }
    const code = key.charCodeAt(0);
    // Check if it's outside the normal ASCII printable range (32-127), excluding space and delete (32 & 127)
    return code > 127 || code < 32;
}
/**
 * Splits a key combo string into its constituent key values and looks up
 * aliases, such as `return` -> `enter`.
 *
 * Unlike the parseKeyCombo method, this method does NOT convert shifted
 * action keys. So `"@"` will NOT be converted to `["shift", "2"]`).
 */
const normalizeKeyCombo = (combo, platformOverride) => {
    const keys = combo.replace(/\s/g, "").split("+");
    return keys.map(key => {
        const keyName = exports.CONFIG_ALIASES[key] != null ? exports.CONFIG_ALIASES[key] : key;
        return keyName === "meta" ? (isMac(platformOverride) ? "cmd" : "ctrl") : keyName;
    });
};
exports.normalizeKeyCombo = normalizeKeyCombo;
function isMac(platformOverride) {
    // HACKHACK: see https://github.com/palantir/blueprint/issues/5174
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    const platform = platformOverride ?? (typeof navigator !== "undefined" ? navigator.platform : undefined);
    return platform === undefined ? false : /Mac|iPod|iPhone|iPad/.test(platform);
}
//# sourceMappingURL=hotkeyParser.js.map