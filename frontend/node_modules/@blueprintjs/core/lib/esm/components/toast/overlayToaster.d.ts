import { AbstractPureComponent } from "../../common";
import type { OverlayToasterProps } from "./overlayToasterProps";
import type { Toaster, ToastOptions } from "./toaster";
import type { ToastProps } from "./toastProps";
export interface OverlayToasterState {
    toasts: ToastOptions[];
    toastRefs: Record<string, React.RefObject<HTMLElement>>;
}
export interface OverlayToasterCreateOptions {
    /**
     * A new DOM element will be created and appended to this container.
     *
     * @default document.body
     */
    container?: HTMLElement;
    /**
     * A function to render the React component onto a newly created DOM element. By default, this creates a
     * ReactDOM client root at the passed container and renders the element into that React tree.
     */
    domRenderer?: OverlayToasterDOMRenderer;
}
export type OverlayToasterDOMRenderer = (element: React.ReactElement<unknown>, container: Element | DocumentFragment) => void;
export declare const OVERLAY_TOASTER_DELAY_MS = 50;
/**
 * OverlayToaster component.
 *
 * @see https://blueprintjs.com/docs/#core/components/toast
 */
export declare class OverlayToaster extends AbstractPureComponent<OverlayToasterProps, OverlayToasterState> implements Toaster {
    static displayName: string;
    static defaultProps: OverlayToasterProps;
    /**
     * Create a new `Toaster` instance that can be shared around your application.
     * The `Toaster` will be rendered into a new element appended to the given container.
     */
    static create(props?: OverlayToasterProps, options?: OverlayToasterCreateOptions): Promise<Toaster>;
    /**
     * This is an alias for `OverlayToaster.create`, exposed for backwards compatibility with the 5.x API.
     *
     * @deprecated Use `OverlayToaster.create` instead.
     */
    static createAsync(props?: OverlayToasterProps, options?: OverlayToasterCreateOptions): Promise<Toaster>;
    state: OverlayToasterState;
    private queue;
    private toastId;
    private toastRefs;
    /** Compute a new collection of toast refs (usually after updating toasts) */
    private getToastRefs;
    show(props: ToastProps, key?: string): string;
    private maybeUpdateExistingToast;
    private immediatelyShowToast;
    private startQueueTimeout;
    private handleQueueTimeout;
    private updateToastsInState;
    dismiss(key: string, timeoutExpired?: boolean): void;
    clear(): void;
    getToasts(): ToastOptions[];
    render(): import("react/jsx-runtime").JSX.Element;
    protected validateProps({ maxToasts }: OverlayToasterProps): void;
    private dismissIfAtLimit;
    private renderToast;
    private createToastOptions;
    private getPositionClasses;
    private getDismissHandler;
    private handleClose;
}
