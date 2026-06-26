import { AbstractPureComponent } from "../../common";
import type { HandleHtmlProps } from "./handleProps";
import { type SliderBaseProps } from "./multiSlider";
export type NumberRange = [number, number];
export interface RangeSliderProps extends SliderBaseProps {
    /**
     * Range value of slider. Handles will be rendered at each position in the range.
     *
     * @default [0, 10]
     */
    value?: NumberRange;
    /** Callback invoked when the range value changes. */
    onChange?(value: NumberRange): void;
    /** Callback invoked when a handle is released. */
    onRelease?(value: NumberRange): void;
    /** HTML props to apply to the slider Handles */
    handleHtmlProps?: {
        start?: HandleHtmlProps;
        end?: HandleHtmlProps;
    };
}
/**
 * Range slider component.
 *
 * @see https://blueprintjs.com/docs/#core/components/sliders.range-slider
 */
export declare class RangeSlider extends AbstractPureComponent<RangeSliderProps> {
    static defaultProps: RangeSliderProps;
    static displayName: string;
    render(): import("react/jsx-runtime").JSX.Element;
    protected validateProps(props: RangeSliderProps): void;
}
