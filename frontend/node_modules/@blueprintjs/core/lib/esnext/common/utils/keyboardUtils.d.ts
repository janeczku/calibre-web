/**
 * Returns whether the keyboard event was triggered by Enter or Space, the two keys that are expected to trigger
 * interactive elements like buttons.
 */
export declare function isKeyboardClick(event: React.KeyboardEvent<HTMLElement>): boolean;
declare const ARROW_KEYS: readonly ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"];
type ArrowKey = (typeof ARROW_KEYS)[number];
export declare function isArrowKey(event: React.KeyboardEvent<HTMLElement>): boolean;
/** Direction multiplier */
export declare function getArrowKeyDirection(event: React.KeyboardEvent<HTMLElement>, 
/** Keys that result in a return of -1 */
negativeKeys: ArrowKey[], 
/** Keys that result in a return of 1 */
positiveKeys: ArrowKey[]): 1 | -1 | undefined;
export {};
