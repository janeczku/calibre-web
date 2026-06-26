export interface KeyAllowlist<T> {
    include: Array<keyof T>;
}
export interface KeyDenylist<T> {
    exclude: Array<keyof T>;
}
/**
 * Returns true if the arrays are equal. Elements will be shallowly compared by
 * default, or they will be compared using the custom `compare` function if one
 * is provided.
 */
export declare function arraysEqual(arrA: any[], arrB: any[], compare?: (a: any, b: any) => boolean): boolean;
/**
 * Shallow comparison between objects. If `keys` is provided, just that subset
 * of keys will be compared; otherwise, all keys will be compared.
 *
 * @returns true if items are equal.
 */
export declare function shallowCompareKeys<T extends {}>(objA: T | null | undefined, objB: T | null | undefined, keys?: KeyDenylist<T> | KeyAllowlist<T>): boolean;
/**
 * Deep comparison between objects. If `keys` is provided, just that subset of
 * keys will be compared; otherwise, all keys will be compared.
 *
 * @returns true if items are equal.
 */
export declare function deepCompareKeys(objA: any, objB: any, keys?: Array<string | number | symbol>): boolean;
/**
 * Returns a descriptive object for each key whose values are deeply unequal
 * between two provided objects. Useful for debugging shouldComponentUpdate.
 */
export declare function getDeepUnequalKeyValues<T extends {}>(objA?: T, objB?: T, keys?: Array<keyof T>): {
    key: keyof T;
    valueA: T[keyof T];
    valueB: T[keyof T];
}[];
