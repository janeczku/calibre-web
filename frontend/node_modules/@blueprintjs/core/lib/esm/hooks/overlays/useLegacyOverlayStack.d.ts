import type { OverlayInstance } from "../../components";
import type { UseOverlayStackReturnValue } from "./useOverlayStack";
/**
 * Modify the global stack in-place and notify all listeners of the updated value.
 *
 * @public for testing
 */
export declare const modifyGlobalStack: (fn: (stack: OverlayInstance[]) => void) => void;
/**
 * Legacy implementation of a global overlay stack which maintains state in a global variable.
 * This is used for backwards-compatibility with overlay-based components in Blueprint v5.
 * It will be removed in Blueprint v6 once `<OverlaysProvider>` is required.
 *
 * @see https://github.com/palantir/blueprint/wiki/Overlay2-migration
 */
export declare function useLegacyOverlayStack(): UseOverlayStackReturnValue;
