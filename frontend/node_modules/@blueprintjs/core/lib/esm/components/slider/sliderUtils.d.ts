/** Helper function for formatting ratios as CSS percentage values. */
export declare function formatPercentage(ratio: number): string;
/**
 * Mutates the values array by filling all the values between start and end index (inclusive) with the fill value.
 */
export declare function fillValues<T>(values: T[], startIndex: number, endIndex: number, fillValue: T): void;
/**
 * Returns the minimum element of an array as determined by comparing the results of calling the arg function on each
 * element of the array. The function will only be called once per element.
 */
export declare function argMin<T>(values: T[], argFn: (value: T) => any): T | undefined;
