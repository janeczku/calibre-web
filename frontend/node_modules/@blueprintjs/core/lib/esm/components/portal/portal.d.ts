import { type Props } from "../../common";
export interface PortalProps extends Props {
    /** Contents to send through the portal. */
    children: React.ReactNode;
    /**
     * Callback invoked when the children of this `Portal` have been added to the DOM.
     */
    onChildrenMount?: () => void;
    /**
     * The HTML element that children will be mounted to.
     *
     * @default PortalProvider#portalContainer ?? document.body
     */
    container?: HTMLElement;
    /**
     * A list of DOM events which should be stopped from propagating through this portal element.
     *
     * @deprecated this prop's implementation no longer works in React v17+
     * @see https://legacy.reactjs.org/docs/portals.html#event-bubbling-through-portals
     * @see https://github.com/palantir/blueprint/issues/6124
     * @see https://github.com/palantir/blueprint/issues/6580
     */
    stopPropagationEvents?: Array<keyof HTMLElementEventMap>;
}
/**
 * Portal component.
 *
 * This component detaches its contents and re-attaches them to document.body.
 * Use it when you need to circumvent DOM z-stacking (for dialogs, popovers, etc.).
 * Any class names passed to this element will be propagated to the new container element on document.body.
 *
 * @see https://blueprintjs.com/docs/#core/components/portal
 */
export declare function Portal({ className, stopPropagationEvents, container, onChildrenMount, children }: PortalProps): import("react").ReactPortal | null;
export declare namespace Portal {
    var displayName: string;
}
