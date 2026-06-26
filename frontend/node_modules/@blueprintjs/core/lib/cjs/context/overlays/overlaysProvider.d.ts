import type { OverlayInstance } from "../../components/overlay2/overlayInstance";
export interface OverlaysContextState {
    /**
     * Whether the context instance is being used within a tree which has an `<OverlaysProvider>`.
     * `useOverlayStack()` will work if this is `false` in Blueprint v5, but this will be unsupported
     * in Blueprint v6; all applications with overlays will be required to configure a provider to
     * manage global overlay state.
     *
     * @see https://github.com/palantir/blueprint/wiki/Overlay2-migration
     */
    hasProvider: boolean;
    /**
     * The application-wide global overlay stack.
     */
    stack: React.MutableRefObject<OverlayInstance[]>;
}
/**
 * A React context used to interact with the overlay stack in an application.
 * Users should take care to make sure that only _one_ of these is instantiated and used within an
 * application.
 *
 * You will likely not be using this OverlaysContext directly, it's mostly used internally by the
 * Overlay2 component.
 *
 * For more information, see the [OverlaysProvider documentation](https://blueprintjs.com/docs/#core/context/overlays-provider).
 */
export declare const OverlaysContext: import("react").Context<OverlaysContextState>;
export interface OverlaysProviderProps {
    /** The component subtree which will have access to this overlay stack context. */
    children: React.ReactNode;
}
/**
 * Overlays context provider, necessary for the `useOverlayStack` hook.
 *
 * @see https://blueprintjs.com/docs/#core/context/overlays-provider
 */
export declare const OverlaysProvider: ({ children }: OverlaysProviderProps) => import("react/jsx-runtime").JSX.Element;
