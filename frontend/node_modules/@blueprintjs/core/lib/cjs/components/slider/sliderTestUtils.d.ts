import type { ReactWrapper } from "enzyme";
import { type InternalHandleProps } from "./handle";
interface MoveOptions {
    /** Size in pixels of one drag event. Direction of drag is determined by `vertical` option. */
    dragSize?: number;
    /** Number of drag events of length `dragSize` to perform. */
    dragTimes: number;
    /** Initial pixel of drag operation: where the mouse is initially pressed. */
    from?: number;
    /** Index of `Handle` to move. */
    handleIndex?: number;
    /** Whether to use touch events. */
    touch?: boolean;
    /** Whether to use vertical events. */
    vertical?: boolean;
    /** Height of slider when vertical. */
    verticalHeight?: number;
}
export declare const DRAG_SIZE = 20;
/**
 * Simulates a full move of a slider handle: engage, move, release.
 * Supports touch and vertical events. Use options to configure exact movement.
 */
export declare function simulateMovement(wrapper: ReactWrapper<InternalHandleProps>, options: MoveOptions): ReactWrapper<InternalHandleProps, {}, import("react").Component<{}, {}, any>>;
/** Release the mouse at the given clientX pixel. Useful for ending a drag interaction. */
export declare const mouseUpHorizontal: (clientX: number) => void;
export {};
