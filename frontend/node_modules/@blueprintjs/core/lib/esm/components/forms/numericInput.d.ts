import { AbstractPureComponent, type HTMLInputProps, Position } from "../../common";
import type { Size } from "../../common/size";
import type { InputSharedProps } from "./inputSharedProps";
export interface NumericInputProps extends InputSharedProps {
    /**
     * Whether to allow only floating-point number characters in the field,
     * mimicking the native `input[type="number"]`.
     *
     * @default true
     */
    allowNumericCharactersOnly?: boolean;
    /**
     * Set this to `true` if you will be controlling the `value` of this input with asynchronous updates.
     * These may occur if you do not immediately call setState in a parent component with the value from
     * the `onChange` handler.
     */
    asyncControl?: boolean;
    /**
     * The position of the buttons with respect to the input field.
     *
     * @default Position.RIGHT
     */
    buttonPosition?: typeof Position.LEFT | typeof Position.RIGHT | "none";
    /**
     * Whether the value should be clamped to `[min, max]` on blur.
     * The value will be clamped to each bound only if the bound is defined.
     * Note that native `input[type="number"]` controls do *NOT* clamp on blur.
     *
     * @default false
     */
    clampValueOnBlur?: boolean;
    /**
     * In uncontrolled mode, this sets the default value of the input.
     * Note that this value is only used upon component instantiation and changes to this prop
     * during the component lifecycle will be ignored.
     *
     * @default ""
     */
    defaultValue?: number | string;
    /**
     * If set to `true`, the input will display with larger styling.
     * This is equivalent to setting `Classes.LARGE` via className on the
     * parent control group and on the child input group.
     *
     * @deprecated use size="large" instead
     * @default false
     */
    large?: boolean;
    /**
     * The locale name, which is passed to the component to format the number and allowing to type the number in the specific locale.
     * [See MDN documentation for more info about browser locale identification](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl#Locale_identification_and_negotiation).
     *
     * @default ""
     */
    locale?: string;
    /**
     * The increment between successive values when <kbd>shift</kbd> is held.
     * Pass explicit `null` value to disable this interaction.
     *
     * @default 10
     */
    majorStepSize?: number | null;
    /** The maximum value of the input. */
    max?: number;
    /** The minimum value of the input. */
    min?: number;
    /**
     * The increment between successive values when <kbd>alt</kbd> is held.
     * Pass explicit `null` value to disable this interaction.
     *
     * @default 0.1
     */
    minorStepSize?: number | null;
    /**
     * Whether the entire text field should be selected on focus.
     *
     * @default false
     */
    selectAllOnFocus?: boolean;
    /**
     * Whether the entire text field should be selected on increment.
     *
     * @default false
     */
    selectAllOnIncrement?: boolean;
    /**
     * If set to `true`, the input will display with smaller styling.
     * This is equivalent to setting `Classes.SMALL` via className on the
     * parent control group and on the child input group.
     *
     * @deprecated use size="small" instead
     * @default false
     */
    small?: boolean;
    /**
     * Size of the input.
     *
     * @default "medium"
     */
    size?: Size;
    /**
     * Alias for the native HTML input `size` attribute.
     * see: https://developer.mozilla.org/en-US/docs/Web/API/HTMLInputElement/size
     */
    inputSize?: HTMLInputProps["size"];
    /**
     * The increment between successive values when no modifier keys are held.
     *
     * @default 1
     */
    stepSize?: number;
    /**
     * The value to display in the input field.
     */
    value?: number | string;
    /** The callback invoked when the value changes due to a button click. */
    onButtonClick?(valueAsNumber: number, valueAsString: string): void;
    /** The callback invoked when the value changes due to typing, arrow keys, or button clicks. */
    onValueChange?(valueAsNumber: number, valueAsString: string, inputElement: HTMLInputElement | null): void;
}
export interface NumericInputState {
    currentImeInputInvalid: boolean;
    prevMinProp?: number;
    prevMaxProp?: number;
    shouldSelectAfterUpdate: boolean;
    stepMaxPrecision: number;
    value: string;
}
/**
 * Numeric input component.
 *
 * @see https://blueprintjs.com/docs/#core/components/numeric-input
 */
export declare class NumericInput extends AbstractPureComponent<Omit<HTMLInputProps, "size"> & NumericInputProps, NumericInputState> {
    static displayName: string;
    static VALUE_EMPTY: string;
    static VALUE_ZERO: string;
    private numericInputId;
    static defaultProps: NumericInputProps;
    static getDerivedStateFromProps(props: NumericInputProps, state: NumericInputState): {
        stepMaxPrecision: number;
        value: string;
        prevMaxProp: number | undefined;
        prevMinProp: number | undefined;
    };
    private static CONTINUOUS_CHANGE_DELAY;
    private static CONTINUOUS_CHANGE_INTERVAL;
    private static getStepMaxPrecision;
    private static roundAndClampValue;
    state: NumericInputState;
    private didPasteEventJustOccur;
    private delta;
    inputElement: HTMLInputElement | null;
    private inputRef;
    private intervalId?;
    private incrementButtonHandlers;
    private decrementButtonHandlers;
    private getCurrentValueAsNumber;
    render(): import("react/jsx-runtime").JSX.Element;
    componentDidUpdate(prevProps: NumericInputProps, prevState: NumericInputState): void;
    protected validateProps(nextProps: HTMLInputProps & NumericInputProps): void;
    private renderButtons;
    private renderInput;
    private getButtonEventHandlers;
    private handleButtonClick;
    private startContinuousChange;
    private stopContinuousChange;
    private handleContinuousChange;
    private handleInputFocus;
    private handleInputBlur;
    private handleInputKeyDown;
    private handleCompositionEnd;
    private handleCompositionUpdate;
    private handleInputKeyPress;
    private handleInputPaste;
    private handleInputChange;
    private handleNextValue;
    private incrementValue;
    private getIncrementDelta;
    private roundAndClampValue;
    private updateDelta;
}
