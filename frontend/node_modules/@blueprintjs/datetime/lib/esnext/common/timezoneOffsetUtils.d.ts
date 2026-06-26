import type { Timezone, TimezoneWithoutOffset } from "./timezoneTypes";
/**
 * Augment hard-coded timezone information stored in this package with its current offset relative to UTC,
 * adjusted for daylight saving using the current date.
 *
 * @see https://github.com/marnusw/date-fns-tz#gettimezoneoffset
 */
export declare function lookupTimezoneOffset(tz: TimezoneWithoutOffset, date?: Date): Timezone;
