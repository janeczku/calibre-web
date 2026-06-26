/**
 * A nifty little class that maintains event handlers to add a class to the container element
 * when entering "mouse mode" (on a `mousedown` event) and remove it when entering "keyboard mode"
 * (on a `tab` key `keydown` event).
 */
export declare class InteractionModeEngine {
    private container;
    private className;
    private isRunning;
    constructor(container: HTMLElement, className: string);
    /** Returns whether the engine is currently running. */
    isActive(): boolean;
    /** Enable behavior which applies the given className when in mouse mode. */
    start(): void;
    /** Disable interaction mode behavior and remove className from container. */
    stop(): void;
    private reset;
    private handleKeyDown;
    private handleMouseDown;
}
