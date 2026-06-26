import { type Locale } from "date-fns";
import type { DatePickerBaseProps } from "./datePickerBaseProps";
export declare const DefaultDateFnsFormats: {
    DATE_ONLY: string;
    DATE_TIME_MILLISECONDS: string;
    DATE_TIME_MINUTES: string;
    DATE_TIME_SECONDS: string;
};
export declare function getDefaultDateFnsFormat(props: Pick<DatePickerBaseProps, "timePickerProps" | "timePrecision">): string;
export declare function getDateFnsFormatter(formatStr: string, locale: Locale | undefined): (date: Date) => string;
export declare function getDateFnsParser(formatStr: string, locale: Locale | undefined): (str: string) => Date;
