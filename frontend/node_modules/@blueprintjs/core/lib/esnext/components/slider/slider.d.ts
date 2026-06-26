import { AbstractPureComponent } from "../../common";
import type { HandleHtmlProps } from "./handleProps";
import { type SliderBaseProps } from "./multiSlider";
export interface SliderProps extends SliderBaseProps {
    /**
     * Initial value of the slider. This determines the other end of the
     * track fill: from `initialValue` to `value`.
     *
     * @default 0
     */
    initialValue?: number;
    /**
     * Value of slider.
     *
     * @default 0
     */
    value?: number;
    /** Callback invoked when the value changes. */
    onChange?(value: number): void;
    /** Callback invoked when the handle is released. */
    onRelease?(value: number): void;
    /** A limited subset of HTML props to apply to the slider Handle */
    handleHtmlProps?: HandleHtmlProps;
}
/**
 * Slider component.
 *
 * @see https://blueprintjs.com/docs/#core/components/sliders.slider
 */
export declare class Slider extends AbstractPureComponent<SliderProps> {
    static defaultProps: SliderProps;
    static displayName: string;
    render(): import("react/jsx-runtime").JSX.Element;
}
