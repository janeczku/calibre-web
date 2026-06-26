import type { Locale } from "date-fns";
import type { DateRange } from "../../common";
export interface DateRangePickerState {
    hoverValue?: DateRange;
    locale: Locale | undefined;
    value: DateRange;
    time: DateRange;
    selectedShortcutIndex?: number;
}
