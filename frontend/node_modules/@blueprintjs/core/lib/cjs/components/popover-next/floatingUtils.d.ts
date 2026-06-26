import { type Middleware } from "@floating-ui/react";
import type { MiddlewareConfig } from "./middlewareTypes";
/**
 * Converts a middleware configuration object to a properly ordered array of Floating UI middleware.
 *
 * @param overrides - Configuration object containing middleware options
 * @returns Array of Floating UI middleware instances in the correct order
 *
 * @see https://floating-ui.com/docs/middleware#ordering
 */
export declare function convertMiddlewareConfigToArray(overrides: MiddlewareConfig): Middleware[];
