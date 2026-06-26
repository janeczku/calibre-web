/**
 * Measure width in pixels of a string displayed with styles provided by `className`.
 * Should only be used if measuring can't be done with existing DOM elements.
 */
export declare function measureTextWidth(text: string, className?: string, containerElement?: HTMLElement): number;
export declare function padWithZeroes(str: string, minLength: number): string;
