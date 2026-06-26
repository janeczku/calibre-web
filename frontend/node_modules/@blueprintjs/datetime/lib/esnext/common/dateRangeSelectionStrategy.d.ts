import { Boundary } from "@blueprintjs/core";
import type { DateRange } from "./dateRange";
export interface DateRangeSelectionState {
    /**
     * The boundary that would be modified by clicking the provided `day`.
     */
    boundary: Boundary;
    /**
     * The date range that would be selected after clicking the provided `day`.
     */
    dateRange: DateRange;
}
export declare class DateRangeSelectionStrategy {
    /**
     * Returns the new date-range and the boundary that would be affected if `day` were clicked. The
     * affected boundary may be different from the provided `boundary` in some cases. For example,
     * clicking a particular boundary's selected date will always deselect it regardless of which
     * `boundary` you provide to this function (because it's simply a more intuitive interaction).
     */
    static getNextState(currentRange: DateRange, day: Date, allowSingleDayRange: boolean, boundary?: Boundary): DateRangeSelectionState;
    private static getNextStateForBoundary;
    private static getDefaultNextState;
    private static getOtherBoundary;
    private static getBoundaryDate;
    private static isOverlappingOtherBoundary;
    private static createRangeForBoundary;
    private static createRange;
}
