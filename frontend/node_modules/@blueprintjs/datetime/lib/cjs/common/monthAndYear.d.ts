export declare class MonthAndYear {
    static fromDate(date: Date | null): MonthAndYear | undefined;
    private date;
    constructor(month?: number, year?: number);
    clone(): MonthAndYear;
    getFullDate(): Date;
    getMonth(): number;
    getYear(): number;
    getPreviousMonth(): MonthAndYear;
    getNextMonth(): MonthAndYear;
    isBefore(monthAndYear: MonthAndYear): boolean;
    isAfter(monthAndYear: MonthAndYear): boolean;
    isSame(monthAndYear: MonthAndYear): boolean;
    isSameMonth(monthAndYear: MonthAndYear): boolean;
}
