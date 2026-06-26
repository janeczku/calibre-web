import { DateFnsLocalizedComponent } from "../dateFnsLocalizedComponent";
import type { DateRangeInputDefaultProps, DateRangeInputProps } from "./dateRangeInputProps";
import type { DateRangeInputState } from "./dateRangeInputState";
export type { DateRangeInputProps };
/**
 * Date range input component.
 *
 * @see https://blueprintjs.com/docs/#datetime/date-range-input
 */
export declare class DateRangeInput extends DateFnsLocalizedComponent<DateRangeInputProps, DateRangeInputState> {
    static defaultProps: DateRangeInputDefaultProps;
    static displayName: string;
    startInputElement: HTMLInputElement | null;
    endInputElement: HTMLInputElement | null;
    private handleStartInputRef;
    private handleEndInputRef;
    constructor(props: DateRangeInputProps);
    componentDidMount(): Promise<void>;
    componentDidUpdate(prevProps: DateRangeInputProps): Promise<void>;
    render(): import("react/jsx-runtime").JSX.Element;
    protected validateProps(props: DateRangeInputProps): void;
    private renderTarget;
    private renderInputGroup;
    private handleDateRangePickerChange;
    private handleShortcutChange;
    private handleDateRangePickerHoverChange;
    private handleStartInputEvent;
    private handleEndInputEvent;
    private handleInputEvent;
    private handleInputKeyDown;
    private handleInputArrowKeyDown;
    private getNextDateForArrowKeyNavigation;
    private getDefaultDateForArrowKeyNavigation;
    private handleInputMouseDown;
    private handleInputClick;
    private handleInputFocus;
    private handleInputBlur;
    private handleInputChange;
    private handlePopoverClose;
    private shouldFocusInputRef;
    private getIsOpenValueWhenDateChanges;
    private getInitialRange;
    private getSelectedRange;
    private getInputDisplayString;
    private getInputPlaceholderString;
    private getInputProps;
    private getInputRef;
    private getStateKeysAndValuesForBoundary;
    private getDateRangeForCallback;
    private getOtherBoundary;
    private doBoundaryDatesOverlap;
    /**
     * Returns true if the provided boundary is an END boundary overlapping the
     * selected start date. (If the boundaries overlap, we consider the END
     * boundary to be erroneous.)
     */
    private doesEndBoundaryOverlapStartBoundary;
    private isControlled;
    private isInputEmpty;
    private isInputInErrorState;
    private isDateValidAndInRange;
    private isNextDateRangeValid;
    private formatMinMaxDateString;
    private parseDate;
    private formatDate;
}
