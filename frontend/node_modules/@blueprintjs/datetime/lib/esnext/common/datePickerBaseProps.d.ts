import type { DayPickerProps } from "react-day-picker";
import type { TimePickerProps } from "./timePickerProps";
import type { TimePrecision } from "./timePrecision";
/**
 * Collection of functions that determine which modifier classes get applied to which days.
 * See the [**react-day-picker** documentation](https://daypicker.dev/v8/api/type-aliases/Modifiers)
 * to learn more.
 */
export interface DatePickerModifiers {
    [name: string]: (date: Date) => boolean;
}
export interface DatePickerBaseProps {
    /**
     * Props to pass to ReactDayPicker. See API documentation
     * [here](https://daypicker.dev/v8/api/type-aliases/DayPickerProps).
     *
     * The following props are managed by the component and cannot be configured:
     * `canChangeMonth`, `captionElement`, `fromMonth` (use `minDate`), `month` (use
     * `initialMonth`), `toMonth` (use `maxDate`).
     */
    dayPickerProps?: DayPickerProps;
    /**
     * An additional element to show below the date picker.
     */
    footerElement?: React.JSX.Element;
    /**
     * Whether the current day should be highlighted in the calendar.
     *
     * @default false
     */
    highlightCurrentDay?: boolean;
    /**
     * The initial month the calendar displays.
     */
    initialMonth?: Date;
    /**
     * The locale name, which is passed to `formatDate`, `parseDate`
     */
    locale?: string;
    /**
     * The latest date the user can select.
     *
     * @default 6 months from now.
     */
    maxDate?: Date;
    /**
     * The earliest date the user can select.
     *
     * @default Jan. 1st, 20 years in the past.
     */
    minDate?: Date;
    /**
     * Collection of functions that determine which modifier classes get applied to which days.
     * Each function should accept a `Date` and return a boolean.
     * See the [**react-day-picker** documentation](https://daypicker.dev/v8/api/type-aliases/Modifiers)
     * to learn more.
     */
    modifiers?: DatePickerModifiers;
    /**
     * If `true`, the month menu will appear to the left of the year menu.
     * Otherwise, the month menu will apear to the right of the year menu.
     *
     * @default false
     */
    reverseMonthAndYearMenus?: boolean;
    /**
     * The precision of time selection that accompanies the calendar. Passing a
     * `TimePrecision` value (or providing `timePickerProps`) shows a
     * `TimePicker` below the calendar. Time is preserved across date changes.
     *
     * This is shorthand for `timePickerProps.precision` and is a quick way to
     * enable time selection.
     */
    timePrecision?: TimePrecision;
    /**
     * Further configure the `TimePicker` that appears beneath the calendar.
     * `onChange` and `value` are ignored in favor of the corresponding
     * top-level props on this component.
     *
     * Passing any non-empty object to this prop will cause the `TimePicker` to appear.
     */
    timePickerProps?: TimePickerProps;
}
