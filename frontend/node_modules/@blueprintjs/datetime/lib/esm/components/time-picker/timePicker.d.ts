import { Component } from "react";
import { type TimePickerProps } from "../../common";
export interface TimePickerState {
    hourText?: string;
    minuteText?: string;
    secondText?: string;
    millisecondText?: string;
    value?: Date;
    isPm?: boolean;
}
/**
 * Time picker component.
 *
 * @see https://blueprintjs.com/docs/#datetime/timepicker
 */
export declare class TimePicker extends Component<TimePickerProps, TimePickerState> {
    static defaultProps: TimePickerProps;
    static displayName: string;
    constructor(props: TimePickerProps);
    private timeInputIds;
    render(): import("react/jsx-runtime").JSX.Element;
    componentDidUpdate(prevProps: TimePickerProps): void;
    private maybeRenderArrowButton;
    private renderDivider;
    private renderInput;
    private maybeRenderAmPm;
    private getInputChangeHandler;
    private getInputBlurHandler;
    private getInputFocusHandler;
    private getInputKeyDownHandler;
    private getInputKeyUpHandler;
    private handleAmPmChange;
    /**
     * Generates a full TimePickerState object with all text fields set to formatted strings based on value
     */
    private getFullStateFromValue;
    private incrementTime;
    private decrementTime;
    private shiftTime;
    private updateTime;
    private updateState;
    private getInitialValue;
}
