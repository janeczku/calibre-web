import { AbstractPureComponent } from "../../common";
import type { OverlayProps } from "./overlayProps";
export interface OverlayState {
    hasEverOpened?: boolean;
}
/**
 * Overlay component.
 *
 * @deprecated use `Overlay2` instead
 * @see https://blueprintjs.com/docs/#core/components/overlay
 */
export declare class Overlay extends AbstractPureComponent<OverlayProps, OverlayState> {
    static displayName: string;
    static defaultProps: OverlayProps;
    static getDerivedStateFromProps({ isOpen: hasEverOpened }: OverlayProps): {
        hasEverOpened: true;
    } | null;
    private static openStack;
    private static getLastOpened;
    private isAutoFocusing;
    private lastActiveElementBeforeOpened;
    state: OverlayState;
    /** Ref for container element, containing all children and the backdrop */
    containerElement: import("react").RefObject<HTMLDivElement>;
    private startFocusTrapElement;
    private endFocusTrapElement;
    render(): import("react/jsx-runtime").JSX.Element | null;
    componentDidMount(): void;
    componentDidUpdate(prevProps: OverlayProps): void;
    componentWillUnmount(): void;
    private maybeRenderChild;
    private maybeRenderBackdrop;
    private renderDummyElement;
    /**
     * Ensures repeatedly pressing shift+tab keeps focus inside the Overlay. Moves focus to
     * the `endFocusTrapElement` or the first keyboard-focusable element in the Overlay (excluding
     * the `startFocusTrapElement`), depending on whether the element losing focus is inside the
     * Overlay.
     */
    private handleStartFocusTrapElementFocus;
    /**
     * Wrap around to the end of the dialog if `enforceFocus` is enabled.
     */
    private handleStartFocusTrapElementKeyDown;
    /**
     * Ensures repeatedly pressing tab keeps focus inside the Overlay. Moves focus to the
     * `startFocusTrapElement` or the last keyboard-focusable element in the Overlay (excluding the
     * `startFocusTrapElement`), depending on whether the element losing focus is inside the
     * Overlay.
     */
    private handleEndFocusTrapElementFocus;
    private overlayWillClose;
    private overlayWillOpen;
    private handleTransitionExited;
    private handleBackdropMouseDown;
    private handleDocumentClick;
    /**
     * When multiple Overlays are open, this event handler is only active for the most recently
     * opened one to avoid Overlays competing with each other for focus.
     */
    private handleDocumentFocus;
    private handleKeyDown;
    private handleTransitionAddEnd;
}
