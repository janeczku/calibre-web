import type { ButtonSharedPropsAndAttributes } from "../button/buttonProps";
import { type TooltipProps } from "../tooltip/tooltip";
export type DialogStepButtonProps = Partial<ButtonSharedPropsAndAttributes> & {
    /** If defined, the button will be wrapped with a tooltip with the specified content. */
    tooltipContent?: TooltipProps["content"];
};
export declare function DialogStepButton({ tooltipContent, ...props }: DialogStepButtonProps): import("react/jsx-runtime").JSX.Element;
