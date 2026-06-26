import type { OverlayProps } from "../overlay/overlayProps";
import type { OverlayInstance } from "./overlayInstance";
export interface Overlay2Props extends OverlayProps, React.RefAttributes<OverlayInstance> {
    /**
     * If you provide a single child element to Overlay2 and attach your own `ref` to the node, you must pass the
     * same value here (otherwise, Overlay2 won't be able to render CSSTransition correctly).
     *
     * Mutually exclusive with the `childRefs` prop. This prop is a shorthand for `childRefs={{ [key: string]: ref }}`.
     */
    childRef?: React.RefObject<HTMLElement>;
    /**
     * If you provide a _multiple child elements_ to Overlay2, you must enumerate and generate a
     * collection of DOM refs to those elements and provide it here. The object's keys must correspond to the child
     * React element `key` values.
     *
     * Mutually exclusive with the `childRef` prop. If you only provide a single child element, consider using
     * `childRef` instead.
     */
    childRefs?: Record<string, React.RefObject<HTMLElement>>;
}
/**
 * Overlay2 component.
 *
 * @see https://blueprintjs.com/docs/#core/components/overlay2
 */
export declare const Overlay2: import("react").ForwardRefExoticComponent<Omit<Overlay2Props, "ref"> & import("react").RefAttributes<OverlayInstance>>;
