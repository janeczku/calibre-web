/** @returns true if React is running in a client environment, and false if it's in a server */
export declare function hasDOMEnvironment(): boolean;
export declare function elementIsOrContains(element: HTMLElement, testElement: HTMLElement): boolean;
/**
 * Checks whether the given element is inside something that looks like a text input.
 * This is particularly useful to determine if a keyboard event inside this element should take priority over hotkey
 * bindings / keyboard shortcut handlers.
 *
 * @returns true if the element is inside a text input
 */
export declare function elementIsTextInput(elem: HTMLElement): boolean;
/**
 * Gets the active element in the document or shadow root (if an element is provided, and it's in the shadow DOM).
 */
export declare function getActiveElement(element?: HTMLElement | null, options?: GetRootNodeOptions): HTMLElement | null;
/**
 * Throttle an event on an EventTarget by wrapping it in a
 * `requestAnimationFrame` call. Returns the event handler that was bound to
 * given eventName so you can clean up after yourself.
 *
 * @see https://developer.mozilla.org/en-US/docs/Web/Events/scroll
 */
export declare function throttleEvent(target: EventTarget, eventName: string, newEventName: string): (event: Event) => void;
export interface ThrottledReactEventOptions {
    preventDefault?: boolean;
}
/**
 * Throttle a callback by wrapping it in a `requestAnimationFrame` call. Returns
 * the throttled function.
 *
 * @see https://www.html5rocks.com/en/tutorials/speed/animations/
 */
export declare function throttleReactEventCallback<E extends React.SyntheticEvent = React.SyntheticEvent>(callback: (event: E, ...otherArgs: any[]) => any, options?: ThrottledReactEventOptions): (event: E, ...otherArgs: any[]) => any;
/**
 * Throttle a method by wrapping it in a `requestAnimationFrame` call. Returns
 * the throttled function.
 */
export declare function throttle<T extends Function>(method: T): T;
export declare function clickElementOnKeyPress(keys: string[]): (e: React.KeyboardEvent) => void;
/**
 * Gets all focusable elements within the given element.
 *
 * Selector derived from this SO question: {@link https://stackoverflow.com/questions/1599660/which-html-elements-can-receive-focus}
 *
 * Note: Order may not be correct if children elements use tabindex values > 0.
 *
 * @param {HTMLElement} element - The element to search within.
 * @returns {HTMLElement[]} An array of focusable elements.
 */
export declare function getFocusableElements(element: HTMLElement): HTMLElement[];
