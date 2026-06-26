import { getCurrentTimezone } from "./getTimezone";
import { TimePrecision } from "./timePrecision";
import { UTC_TIME } from "./timezoneItems";
export { getCurrentTimezone, UTC_TIME };
export declare function getIsoEquivalentWithUpdatedTimezone(date: Date, timezone: string, timePrecision: TimePrecision | undefined): string;
/**
 * HACKHACK: this method relies on parsing strings with the `Date()` constructor, which is discouraged
 * by the MDN documentation and the Moment.js status page. If we continue to use this approach, we need
 * to validate that input strings conform to the ISO 8601 format.
 *
 * @see https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date/Date#parameters
 * @see https://momentjs.com/docs/#/-project-status/
 *
 * @param value ISO string representation of a date
 * @param timezone target timezone IANA code
 */
export declare function getDateObjectFromIsoString(value: string | undefined, timezone: string): Date | undefined;
export declare function getDateObjectFromIsoString(value: string | null | undefined, timezone: string): Date | null | undefined;
/**
 * Converts a date in local timezone to represent better the passed through timezone
 * representation for the user, meaning if 8 AM local time is currently the date, and local time is Oslo
 * and the user has a default of UTC in selection, the new date should represent 7 AM.
 *
 * @param date the current existing date object
 * @param newTimezone the new timezone that we need to update the date to represent
 * @returns The date converted to match the new timezone
 */
export declare function convertLocalDateToTimezoneTime(date: Date, newTimezone: string): Date;
/**
 * Converts a date to match a new timezone selection. The date is the internal local time
 * representation for the user, meaning if 8 AM local time is currently selected, and local time is Oslo
 * and the user switches timezone to UTC, the new date should represent 9 AM in Oslo time.
 *
 * @param date the current existing date object
 * @param newTimezone the new timezone that the date should be converted to represent
 * @returns The date converted to match the new timezone
 */
export declare function convertDateToLocalEquivalentOfTimezoneTime(date: Date, newTimezone: string): Date;
