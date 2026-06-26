import type { OverlayInstance } from "../../components";
export interface UseOverlayStackReturnValue {
    /**
     * Removes an existing overlay off the stack.
     *
     * N.B. This method accepts an id instead of an overlay instance because the latter may be
     * null when an overlay is unmounting, and we may stil have some cleanup to do at that time.
     * Also, this method is not idempotent: if the overlay is not found on the stack, nothing happens.
     *
     * @param id identifier of the overlay to be closed
     */
    closeOverlay: (id: string) => void;
    /**
     * @returns the last opened overlay on the stack
     */
    getLastOpened: () => OverlayInstance | undefined;
    /**
     * @param id current overlay identifier
     * @returns a list of the current overlay and all overlays which are descendants of it.
     */
    getThisOverlayAndDescendants: (id: string) => OverlayInstance[];
    /**
     * Pushes a new overlay onto the stack.
     */
    openOverlay: (overlay: OverlayInstance) => void;
    /**
     * Resets the overlay stack, to be called after all overlays are closed.
     * Warning: this should only be used in unit tests.
     */
    resetStack: () => void;
}
/**
 * React hook to interact with the global overlay stack.
 *
 * @see https://blueprintjs.com/docs/#core/hooks/use-overlay-stack
 */
export declare function useOverlayStack(): UseOverlayStackReturnValue;
