import type { DayPickerBase, DayPickerRangeProps, DayPickerSingleProps } from "react-day-picker";
type ReactDayPickerOmittedProps = "captionLayout" | "disableNavigation" | "fromDate" | "fromMonth" | "fromYear" | "locale" | "mode" | "month" | "numberOfMonths" | "required" | "selected" | "toDate" | "toMonth" | "toYear";
/**
 * react-day-picker v8.x options which may be customized / overriden on
 * `DatePicker`, `DateInput`, `DateRangePicker`, and `DateRangeInput` via the `dayPickerProps` prop.
 */
export type DayPickerProps = Omit<DayPickerBase, ReactDayPickerOmittedProps>;
export interface ReactDayPickerRangeProps {
    /**
     * Props to pass to react-day-picker's day range picker. See API documentation
     * [here](https://daypicker.dev/v8/api/interfaces/DayPickerRangeProps).
     *
     * Some properties are unavailable since they are set by the component design and cannot be changed:
     *  - "captionLayout"
     *  - "disableNavigation"
     *  - "mode"
     *
     * Other properties have alternative names as top-level props:
     *  - "fromDate", "fromMonth", "fromYear", "toDate", "toMonth", "toYear": use "minDate" and "maxDate" instead (legacy names from @blueprintjs/datetime v4)
     *  - "locale"
     *  - "month": navigation is controlled by the component; use "defaultMonth" to set the initially displayed month
     *  - "numberOfMonths": use "singleMonthOnly" prop instead
     *  - "required": use "canClearSelection" instead (legacy name from @blueprintjs/datetime v4)
     *  - "selected": use "value" instead
     */
    dayPickerProps?: Omit<DayPickerRangeProps, ReactDayPickerOmittedProps>;
}
export interface ReactDayPickerSingleProps {
    /**
     * Props to pass to react-day-picker's single day picker. See API documentation
     * [here](https://daypicker.dev/v8/api/interfaces/DayPickerSingleProps).
     *
     * Some properties are unavailable since they are set by the component design and cannot be changed:
     *  - "captionLayout"
     *  - "disableNavigation"
     *  - "mode"
     *  - "numberOfMonths": fixed to 1 month
     *
     * Other properties have alternative names as top-level props:
     *  - "fromDate", "fromMonth", "fromYear", "toDate", "toMonth", "toYear": use "minDate" and "maxDate" instead (legacy names from @blueprintjs/datetime v4)
     *  - "locale"
     *  - "month": navigation is controlled by the component; use "defaultMonth" to set the initially displayed month
     *  - "required": use "canClearSelection" instead (legacy name from @blueprintjs/datetime v4)
     *  - "selected": use "value" instead
     */
    dayPickerProps?: Omit<DayPickerSingleProps, ReactDayPickerOmittedProps>;
}
export {};
