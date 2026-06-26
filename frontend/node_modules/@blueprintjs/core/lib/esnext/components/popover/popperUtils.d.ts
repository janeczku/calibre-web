import type { BasePlacement, Placement } from "@popperjs/core";
export { placements as PopperPlacements } from "@popperjs/core";
/** Converts a full placement to one of the four positions by stripping text after the `-`. */
export declare function getBasePlacement(placement: Placement): BasePlacement;
/** Returns true if position is left or right. */
export declare function isVerticalPlacement(side: BasePlacement): boolean;
/** Returns the opposite position. */
export declare function getOppositePlacement(side: BasePlacement): "left" | "right" | "bottom" | "top";
/** Returns the CSS alignment keyword corresponding to given placement. */
export declare function getAlignment(placement: Placement): "center" | "left" | "right";
/** Modifier helper function to compute popper transform-origin based on arrow position */
export declare function getTransformOrigin(placement: Placement, arrowStyles: {
    left: string;
    top: string;
} | undefined): string;
