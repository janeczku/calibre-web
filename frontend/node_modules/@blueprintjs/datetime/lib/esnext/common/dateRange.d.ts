export type DateRange = [Date | null, Date | null];
export type NonNullDateRange = [Date, Date];
export declare function isNonNullRange(range: DateRange): range is NonNullDateRange;
