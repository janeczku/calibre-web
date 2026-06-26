export declare function getTodayAtMidnight(): Date;
export declare function shiftDateByDays(date: Date, days: number): Date;
export declare function shiftDateByWeeks(date: Date, weeks: number): Date;
export declare function shiftDateByArrowKey(date: Date, key: string): Date;
export declare function clampDate(date: Date, minDate: Date | null | undefined, maxDate: Date | null | undefined): Date;
export declare function isEntireInputSelected(element: HTMLInputElement | null): boolean;
