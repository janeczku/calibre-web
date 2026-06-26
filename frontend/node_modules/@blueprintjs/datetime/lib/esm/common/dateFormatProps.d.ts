import type { DatePickerBaseProps } from "./datePickerBaseProps";
export interface DateFormatProps {
    /**
     * The error message to display when the date selected is invalid.
     *
     * @default "Invalid date"
     */
    invalidDateMessage?: string;
    /**
     * The locale name, which is passed to `formatDate`, `parseDate`
     */
    locale?: string;
    /**
     * The error message to display when the date selected is out of range.
     *
     * @default "Out of range"
     */
    outOfRangeMessage?: string;
    /**
     * Placeholder text to display in empty input fields.
     * Recommended practice is to indicate the expected date format.
     */
    placeholder?: string;
    /**
     * Function to render a JavaScript `Date` to a string.
     * Optional `localeCode` argument comes directly from the prop on this component:
     * if the prop is defined, then the argument will be too.
     */
    formatDate(date: Date, localeCode?: string): string;
    /**
     * Function to deserialize user input text to a JavaScript `Date` object.
     * Return `false` if the string is an invalid date.
     * Return `null` to represent the absence of a date.
     * Optional `localeCode` argument comes directly from the prop on this component.
     */
    parseDate(str: string, localeCode?: string): Date | false | null;
}
export declare function getFormattedDateString(date: Date | false | null | undefined, props: Omit<DateFormatProps, "parseDate"> & Pick<DatePickerBaseProps, "maxDate" | "minDate">, ignoreRange?: boolean): string | undefined;
