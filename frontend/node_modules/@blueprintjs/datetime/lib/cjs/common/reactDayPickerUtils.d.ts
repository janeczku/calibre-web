import type { DateRange as RDPRange } from "react-day-picker";
import type { DateRange } from "./dateRange";
/**
 * Converts a Blueprint `DateRange` to a react-day-picker `DateRange`.
 */
export declare function dateRangeToDayPickerRange(range: DateRange): RDPRange;
