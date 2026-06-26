import type { Locale } from "date-fns";
import type { Boundary } from "@blueprintjs/core";
export interface DateRangeInputState {
    isOpen?: boolean;
    boundaryToModify?: Boundary;
    lastFocusedField?: Boundary;
    locale?: Locale | undefined;
    formattedMinDateString?: string;
    formattedMaxDateString?: string;
    isStartInputFocused: boolean;
    isEndInputFocused: boolean;
    startInputString?: string;
    endInputString?: string;
    startHoverString?: string | null;
    endHoverString?: string | null;
    selectedEnd: Date | null;
    selectedStart: Date | null;
    shouldSelectAfterUpdate?: boolean;
    wasLastFocusChangeDueToHover?: boolean;
    selectedShortcutIndex?: number;
}
