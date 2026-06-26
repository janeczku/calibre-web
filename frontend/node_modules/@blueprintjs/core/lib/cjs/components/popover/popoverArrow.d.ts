import type { Placement } from "@popperjs/core";
import type { PopperArrowProps } from "react-popper";
export declare const POPOVER_ARROW_SVG_SIZE = 30;
export declare const TOOLTIP_ARROW_SVG_SIZE = 22;
export interface PopoverArrowProps {
    arrowProps: PopperArrowProps;
    placement: Placement;
}
export declare const PopoverArrow: React.FC<PopoverArrowProps>;
