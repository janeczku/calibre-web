import type { TimezoneWithNames } from "./timezoneTypes";
export declare const TimezoneDisplayFormat: {
    /**
     * Short name format: "HST", "EDT", etc.
     * Falls back to "GMT+/-offset" if there is no commonly used abbreviation.
     */
    ABBREVIATION: "abbreviation";
    /**
     * IANA timezone code: "Pacific/Honolulu", "America/New_York", etc.
     */
    CODE: "code";
    /**
     * Composite format: "Hawaii Time (HST) -10:00", "New York (EDT) -5:00", etc.
     * Omits abbreviation if there is no short name (it is redundant with offset).
     */
    COMPOSITE: "composite";
    /**
     * Long name format: "Hawaii-Aleutian Standard Time", "Eastern Daylight Time", "Coordinated Universal Time", etc.
     */
    LONG_NAME: "long-name";
    /**
     * Offset format: "-10:00", "-5:00", etc.
     */
    OFFSET: "offset";
};
export type TimezoneDisplayFormat = (typeof TimezoneDisplayFormat)[keyof typeof TimezoneDisplayFormat];
/**
 * Formats a timezone according to the specified display format to show in the default `<Button>` rendered as the
 * `<TimezoneSelect>` target element.
 */
export declare function formatTimezone(timezone: TimezoneWithNames | undefined, displayFormat: TimezoneDisplayFormat): string | undefined;
