import type { TimezoneWithNames } from "./timezoneTypes";
/**
 * Given a timezone IANA code and an optional date object, retrieve additional metadata like its common name, offset,
 * and abbreviation.
 */
export declare function getTimezoneMetadata(timezoneIanaCode: string, date?: Date): TimezoneWithNames | undefined;
