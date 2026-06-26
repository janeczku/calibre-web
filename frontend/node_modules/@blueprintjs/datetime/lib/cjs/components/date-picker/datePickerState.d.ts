import type { Locale } from "date-fns";
export interface DatePickerState {
    displayMonth: number;
    displayYear: number;
    locale: Locale | undefined;
    selectedDay: number | null;
    value: Date | null;
    selectedShortcutIndex?: number;
}
