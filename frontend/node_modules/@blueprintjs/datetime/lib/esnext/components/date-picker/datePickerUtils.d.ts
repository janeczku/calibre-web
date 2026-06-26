import { getFormattedDateString } from "../../common/dateFormatProps";
import { measureTextWidth } from "../../common/utils";
export declare function getDefaultMaxDate(): Date;
export declare function getDefaultMinDate(): Date;
/**
 * DatePicker-related utility functions which may be useful outside this package to
 * build date/time components.
 */
export declare const DatePickerUtils: {
    getDefaultMaxDate: typeof getDefaultMaxDate;
    getDefaultMinDate: typeof getDefaultMinDate;
    getFormattedDateString: typeof getFormattedDateString;
    measureTextWidth: typeof measureTextWidth;
};
