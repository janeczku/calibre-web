import type { OverlayProps } from "../overlay/overlayProps";
/**
 * Public instance properties & methods for an overlay in the current overlay stack.
 */
export interface OverlayInstance {
    /**
     * Bring document focus inside this overlay element.
     * This should be defined if `props.enforceFocus={true}` or `props.autoFocus={true}`.
     */
    bringFocusInsideOverlay?: () => void;
    /** Reference to the overlay container element which may or may not be in a Portal. */
    containerElement: React.RefObject<HTMLDivElement>;
    /**
     * Document "focus" event handler which needs to be attached & detached appropriately.
     * This should be defined if `props.enforceFocus={true}`.
     */
    handleDocumentFocus?: (e: FocusEvent) => void;
    /**
     * Document "mousedown" event handler which needs to be attached & detached appropriately.
     * This should be defined if `props.canOutsideClickClose={true}` and `props.hasBackdrop={false}`.
     */
    handleDocumentMousedown?: (e: MouseEvent) => void;
    /** Unique ID for this overlay which helps to identify it across prop changes. */
    id: string;
    /** Subset of props necessary for some overlay stack focus management logic. */
    props: Pick<OverlayProps, "autoFocus" | "enforceFocus" | "usePortal" | "hasBackdrop">;
}
