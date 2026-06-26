/** describes a component of time. `H:MM:SS.MS` */
export declare enum TimeUnit {
    HOUR_24 = "hour24",
    HOUR_12 = "hour12",
    MINUTE = "minute",
    SECOND = "second",
    MS = "ms"
}
/** Gets a descriptive label representing the plural of the given time unit. */
export declare function getTimeUnitPrintStr(unit: TimeUnit): string;
/** Returns the given time unit component of the date. */
export declare function getTimeUnit(unit: TimeUnit, date: Date): number;
/** Sets the given time unit to the given time in date object. Modifies given `date` object and returns it. */
export declare function setTimeUnit(unit: TimeUnit, time: number, date: Date, isPm?: boolean): Date;
/** Returns true if `time` is a valid value */
export declare function isTimeUnitValid(unit: TimeUnit, time?: number): boolean;
/** If unit of time is greater than max, returns min. If less than min, returns max. Otherwise, returns time. */
export declare function wrapTimeAtUnit(unit: TimeUnit, time: number): number;
export declare function getTimeUnitClassName(unit: TimeUnit): string;
export declare function getTimeUnitMax(unit: TimeUnit): number;
export declare function getTimeUnitMin(unit: TimeUnit): number;
export declare function getDefaultMinTime(): Date;
export declare function getDefaultMaxTime(): Date;
