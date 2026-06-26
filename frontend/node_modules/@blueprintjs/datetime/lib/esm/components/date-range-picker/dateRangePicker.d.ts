import { DateFnsLocalizedComponent } from "../dateFnsLocalizedComponent";
import type { DateRangePickerDefaultProps, DateRangePickerProps } from "./dateRangePickerProps";
import type { DateRangePickerState } from "./dateRangePickerState";
export type { DateRangePickerProps };
/**
 * Date range picker component.
 *
 * @see https://blueprintjs.com/docs/#datetime/date-range-picker
 */
export declare class DateRangePicker extends DateFnsLocalizedComponent<DateRangePickerProps, DateRangePickerState> {
    static defaultProps: DateRangePickerDefaultProps;
    static displayName: string;
    private modifiers;
    private modifiersClassNames;
    private initialMonthAndYear;
    constructor(props: DateRangePickerProps);
    render(): import("react/jsx-runtime").JSX.Element;
    componentDidMount(): Promise<void>;
    componentDidUpdate(prevProps: DateRangePickerProps): Promise<void>;
    protected validateProps(props: DateRangePickerProps): void;
    private maybeRenderShortcuts;
    private maybeRenderTimePickers;
    private handleTimeChange;
    private getDefaultDate;
    private handleTimeChangeLeftCalendar;
    private handleTimeChangeRightCalendar;
    /**
     * Render a standard day range picker where props.contiguousCalendarMonths is expected to be `true`.
     */
    private renderContiguousDayRangePicker;
    /**
     * react-day-picker doesn't have built-in support for non-contiguous calendar months in its range picker,
     * so we have to implement this ourselves.
     */
    private renderNonContiguousDayRangePicker;
    private get resolvedDayPickerProps();
    /**
     * Custom formatter to render weekday names in the calendar header. The default formatter generally works fine,
     * but it was returning CAPITALIZED strings for some reason, while we prefer Title Case.
     */
    private formatWeekdayName;
    private handleDayMouseEnter;
    private handleDayMouseLeave;
    private handleDayRangeSelect;
    private handleShortcutClick;
    private updateSelectedRange;
}
