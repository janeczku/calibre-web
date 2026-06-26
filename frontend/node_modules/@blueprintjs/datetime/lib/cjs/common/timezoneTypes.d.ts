export interface Timezone {
    /** Current offset from UTC time, adjusted for daylight saving using the current date. */
    offset: string;
    /** Common human-readable name of the timezone, usually the name of a big city in that zone. */
    label: string;
    /** IANA identifier code, see https://www.iana.org/time-zones. */
    ianaCode: string;
}
export type TimezoneWithoutOffset = Omit<Timezone, "offset">;
export interface TimezoneWithNames extends Timezone {
    longName: string;
    shortName: string;
}
