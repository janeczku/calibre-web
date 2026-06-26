import { DateFnsLocalizedComponent } from "../dateFnsLocalizedComponent";
import type { DatePickerProps } from "./datePickerProps";
import type { DatePickerState } from "./datePickerState";
export type { DatePickerProps };
/**
 * Date picker component.
 *
 * @see https://blueprintjs.com/docs/#datetime/date-picker
 */
export declare class DatePicker extends DateFnsLocalizedComponent<DatePickerProps, DatePickerState> {
    static defaultProps: DatePickerProps;
    static displayName: string;
    private ignoreNextMonthChange;
    constructor(props: DatePickerProps);
    render(): import("react/jsx-runtime").JSX.Element;
    componentDidMount(): Promise<void>;
    componentDidUpdate(prevProps: DatePickerProps): Promise<void>;
    protected validateProps(props: DatePickerProps): void;
    /**
     * Custom formatter to render weekday names in the calendar header. The default formatter generally works fine,
     * but it was returning CAPITALIZED strings for some reason, while we prefer Title Case.
     */
    private renderWeekdayName;
    private renderOptionsBar;
    private maybeRenderTimePicker;
    private maybeRenderShortcuts;
    private handleDaySelect;
    private handleShortcutClick;
    private updateDay;
    private computeValidDateInSpecifiedMonthYear;
    private handleClearClick;
    private handleMonthChange;
    private handleTodayClick;
    private handleTimeChange;
    /**
     * Update `value` by invoking `onChange` (always) and setting state (if uncontrolled).
     */
    private updateValue;
}
