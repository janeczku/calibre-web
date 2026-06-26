import { AbstractPureComponent, Intent, type IntentProps, type Props } from "../../common";
import { type HandleProps } from "./handleProps";
/**
 * Multi slider handle component, used as a child of MultiSlider. This component is not rendered directly.
 *
 * @see https://blueprintjs.com/docs/#core/components/sliders.handle
 */
export declare const MultiSliderHandle: React.FC<HandleProps>;
export interface SliderBaseProps extends Props, IntentProps {
    children?: React.ReactNode;
    /**
     * Whether the slider is non-interactive.
     *
     * @default false
     */
    disabled?: boolean;
    /**
     * Increment between successive labels. Must be greater than zero.
     *
     * @default inferred (if labelStepSize is undefined)
     */
    labelStepSize?: number;
    /**
     * Array of specific values for the label placement. This prop is mutually exclusive with
     * `labelStepSize`.
     */
    labelValues?: readonly number[];
    /**
     * Number of decimal places to use when rendering label value. Default value is the number of
     * decimals used in the `stepSize` prop. This prop has _no effect_ if you supply a custom
     * `labelRenderer` callback.
     *
     * @default inferred from stepSize
     */
    labelPrecision?: number;
    /**
     * Maximum value of the slider. Value must be a finite number.
     *
     * @default 10
     */
    max?: number;
    /**
     * Minimum value of the slider. Value must be a finite number.
     *
     * @default 0
     */
    min?: number;
    /**
     * Whether a solid bar should be rendered on the track between current and initial values,
     * or between handles for `RangeSlider`.
     *
     * @default true
     */
    showTrackFill?: boolean;
    /**
     * Increment between successive values; amount by which the handle moves. Must be greater than zero.
     *
     * @default 1
     */
    stepSize?: number;
    /**
     * Callback to render a single label. Useful for formatting numbers as currency or percentages.
     * If `true`, labels will use number value formatted to `labelPrecision` decimal places.
     * If `false`, labels will not be shown.
     *
     * The callback is provided a numeric value and optional rendering options, which include:
     * - isHandleTooltip: whether this label is being rendered within a handle tooltip
     *
     * @default true
     */
    labelRenderer?: boolean | ((value: number, opts?: {
        isHandleTooltip: boolean;
    }) => string | React.JSX.Element);
    /**
     * Whether to show the slider in a vertical orientation.
     *
     * @default false
     */
    vertical?: boolean;
}
export interface MultiSliderProps extends SliderBaseProps {
    /** Default intent of a track segment, used only if no handle specifies `intentBefore/After`. */
    defaultTrackIntent?: Intent;
    /** Callback invoked when a handle value changes. Receives handle values in sorted order. */
    onChange?(values: number[]): void;
    /** Callback invoked when a handle is released. Receives handle values in sorted order. */
    onRelease?(values: number[]): void;
}
export interface SliderState {
    labelPrecision: number;
    /** the client size, in pixels, of one tick */
    tickSize: number;
    /** the size of one tick as a ratio of the component's client size */
    tickSizeRatio: number;
}
/**
 * Multi slider component.
 *
 * @see https://blueprintjs.com/docs/#core/components/sliders.multi-slider
 */
export declare class MultiSlider extends AbstractPureComponent<MultiSliderProps, SliderState> {
    static defaultSliderProps: SliderBaseProps;
    static defaultProps: MultiSliderProps;
    static displayName: string;
    /** @deprecated Use `MultiSliderHandle` instead */
    static Handle: import("react").FC<HandleProps>;
    static getDerivedStateFromProps(props: MultiSliderProps): {
        labelPrecision: number;
    };
    private static getLabelPrecision;
    state: SliderState;
    private handleElements;
    private trackElement;
    getSnapshotBeforeUpdate(prevProps: MultiSliderProps): null;
    render(): import("react/jsx-runtime").JSX.Element;
    componentDidMount(): void;
    componentDidUpdate(prevProps: MultiSliderProps, prevState: SliderState): void;
    protected validateProps(props: React.PropsWithChildren<MultiSliderProps>): void;
    private formatLabel;
    private renderLabels;
    private renderTracks;
    private renderTrackFill;
    private renderHandles;
    private addHandleRef;
    private maybeHandleTrackClick;
    private maybeHandleTrackTouch;
    private canHandleTrackEvent;
    private nearestHandleForValue;
    private getHandlerForIndex;
    private getNewHandleValues;
    private findFirstLockedHandleIndex;
    private handleChange;
    private handleRelease;
    private getLabelValues;
    private getOffsetRatio;
    private getTrackIntent;
    private updateTickSize;
}
