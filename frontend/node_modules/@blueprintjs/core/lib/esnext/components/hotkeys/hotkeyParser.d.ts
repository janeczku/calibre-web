export interface KeyCodeTable {
    [code: number]: string;
}
export interface KeyCodeReverseTable {
    [key: string]: number;
}
export interface KeyMap {
    [key: string]: string;
}
export declare const MODIFIER_BIT_MASKS: KeyCodeReverseTable;
export declare const CONFIG_ALIASES: KeyMap;
/**
 * Key mapping used in getKeyCombo() implementation for physical keys which are not alphabet characters or digits.
 *
 * N.B. at some point, we should stop using this mapping, since we can implement the desired functionality in a more
 * straightforward way by using the `event.code` property, which will always tell us the identifiers represented by the
 * _values_ in this object (the default physical keys, unaltered by modifier keys or keyboard layout).
 */
export declare const SHIFT_KEYS: KeyMap;
export interface KeyCombo {
    key?: string;
    modifiers: number;
}
export declare function comboMatches(a: KeyCombo, b: KeyCombo): boolean;
/**
 * Converts a key combo string into a key combo object. Key combos include
 * zero or more modifier keys, such as `shift` or `alt`, and exactly one
 * action key, such as `A`, `enter`, or `left`.
 *
 * For action keys that require a shift, e.g. `@` or `|`, we inlude the
 * necessary `shift` modifier and automatically convert the action key to the
 * unshifted version. For example, `@` is equivalent to `shift+2`.
 */
export declare const parseKeyCombo: (combo: string) => KeyCombo;
/**
 * Interprets a keyboard event as a valid KeyComboTag `combo` prop string value.
 *
 * Note that this function is only used in the docs example and tests; it is not used by `useHotkeys()` or any
 * Blueprint consumers that we are currently aware of.
 */
export declare const getKeyComboString: (e: KeyboardEvent) => string;
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
export declare const getKeyCombo: (e: KeyboardEvent) => KeyCombo;
/**
 * Splits a key combo string into its constituent key values and looks up
 * aliases, such as `return` -> `enter`.
 *
 * Unlike the parseKeyCombo method, this method does NOT convert shifted
 * action keys. So `"@"` will NOT be converted to `["shift", "2"]`).
 */
export declare const normalizeKeyCombo: (combo: string, platformOverride: string | undefined) => string[];
export declare function isMac(platformOverride: string | undefined): boolean;
