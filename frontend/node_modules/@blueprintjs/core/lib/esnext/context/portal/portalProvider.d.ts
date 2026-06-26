export interface PortalContextOptions {
    /** Additional CSS classes to add to all `Portal` elements in this React context. */
    portalClassName?: string;
    /** The HTML element that all `Portal` elements in this React context will be added as children to  */
    portalContainer?: HTMLElement;
}
/**
 * A React context to set options for all portals in a given subtree.
 * Do not use this PortalContext directly, instead use PortalProvider to set the options.
 */
export declare const PortalContext: import("react").Context<PortalContextOptions>;
/**
 * Portal context provider.
 *
 * @see https://blueprintjs.com/docs/#core/context/portal-provider
 */
export declare const PortalProvider: ({ children, portalClassName, portalContainer, }: React.PropsWithChildren<PortalContextOptions>) => import("react/jsx-runtime").JSX.Element;
