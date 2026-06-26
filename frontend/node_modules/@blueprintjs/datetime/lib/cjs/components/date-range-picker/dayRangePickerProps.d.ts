import type { DayPickerRangeProps } from "react-day-picker";
import type { Boundary } from "@blueprintjs/core";
import type { DateRange } from "../../common";
import type { MonthAndYear } from "../../common/monthAndYear";
import type { DateRangePickerProps } from "./dateRangePickerProps";
import type { DateRangePickerState } from "./dateRangePickerState";
/**
 * Props used to render an interactive single- or double-calendar day range picker.
 * This is the core UI of DateRangePicker (exclusive of time pickers, shortcuts, and the actions bar).
 */
export interface DayRangePickerProps extends Omit<DateRangePickerProps, "initialMonth" | "locale" | "value">, Pick<DateRangePickerState, "locale" | "value"> {
    /**
     * react-day-picker event handlers. These are used to update hover state in DateRangePicker.
     */
    dayPickerEventHandlers: Required<Pick<DayPickerRangeProps, "onDayMouseEnter" | "onDayMouseLeave">>;
    /**
     * Initial month and year to display. If there are multiple calendars, this applies to the left calendar.
     */
    initialMonthAndYear: MonthAndYear;
    /**
     * Date range selection handler triggered when clicking a day in one of the calendars.
     *
     * @param selectedRange the new selected date range
     * @param selectedDay the date that was clicked to trigger this selection
     * @param boundary the boundary (start or end) which has just been modified by this click
     */
    onRangeSelect: (selectedRange: DateRange, selectedDay: Date, boundary: Boundary) => void;
}
